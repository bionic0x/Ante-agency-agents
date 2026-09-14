#!/usr/bin/env python3
"""Measure conversion performance without turning timing into a CI gate.

The harness deliberately reports evidence rather than enforcing thresholds. It
covers the four cases useful for comparing converter changes:

* full-sequential: complete conversion with the default sequential path
* full-parallel: complete conversion using convert.sh --parallel
* representative-tool: one per-agent renderer (Codex by default)
* one-agent-change: an isolated checkout copy with one source agent perturbed,
  followed by a full sequential conversion. Today this measures the rebuild
  cost after a one-agent edit; future incremental work can use the same case.

Examples:
    python3 scripts/benchmark-conversion.py
    python3 scripts/benchmark-conversion.py --repeat 3 --json benchmark.json
    python3 scripts/benchmark-conversion.py --scenario representative-tool --tool codex
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AGENT = Path("engineering/engineering-frontend-developer.md")
SCENARIOS = (
    "full-sequential",
    "full-parallel",
    "representative-tool",
    "one-agent-change",
)


@dataclass
class Measurement:
    scenario: str
    iteration: int
    wall_seconds: float
    cpu_seconds: float
    returncode: int
    command: list[str]


def child_cpu_seconds() -> float:
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def run_command(
    scenario: str,
    iteration: int,
    command: list[str],
    cwd: Path,
    verbose: bool,
) -> Measurement:
    before_cpu = child_cpu_seconds()
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=cwd,
        stdout=None if verbose else subprocess.DEVNULL,
        stderr=None if verbose else subprocess.DEVNULL,
        check=False,
    )
    wall = time.perf_counter() - started
    cpu = child_cpu_seconds() - before_cpu
    return Measurement(
        scenario=scenario,
        iteration=iteration,
        wall_seconds=wall,
        cpu_seconds=cpu,
        returncode=completed.returncode,
        command=command,
    )


def conversion_command(root: Path, out: Path, scenario: str, tool: str, jobs: int) -> list[str]:
    command = ["bash", str(root / "scripts" / "convert.sh"), "--out", str(out)]
    if scenario == "full-parallel":
        command.append("--parallel")
        if jobs:
            command.extend(["--jobs", str(jobs)])
    elif scenario == "representative-tool":
        command.extend(["--tool", tool])
    return command


def isolated_source_copy(agent: Path) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    holder: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory(prefix="agency-benchmark-source-")
    destination = Path(holder.name) / "repo"

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = {".git", ".cache", "__pycache__"}.intersection(names)
        # Generated adapters are not inputs needed by convert.sh and copying them
        # would make this benchmark mostly measure filesystem duplication.
        if Path(directory).resolve() == ROOT.resolve() and "integrations" in names:
            ignored.add("integrations")
        return ignored

    shutil.copytree(ROOT, destination, ignore=ignore)
    target = destination / agent
    if not target.is_file():
        holder.cleanup()
        raise FileNotFoundError(f"benchmark agent does not exist: {agent}")
    with target.open("a", encoding="utf-8") as handle:
        handle.write("\n<!-- benchmark-only one-agent perturbation -->\n")
    return holder, destination


def run_scenario(
    scenario: str,
    iteration: int,
    tool: str,
    jobs: int,
    agent: Path,
    verbose: bool,
) -> Measurement:
    if scenario == "one-agent-change":
        holder, source_root = isolated_source_copy(agent)
        try:
            with tempfile.TemporaryDirectory(prefix="agency-benchmark-out-") as out_dir:
                command = conversion_command(source_root, Path(out_dir), "full-sequential", tool, jobs)
                return run_command(scenario, iteration, command, source_root, verbose)
        finally:
            holder.cleanup()

    with tempfile.TemporaryDirectory(prefix="agency-benchmark-out-") as out_dir:
        command = conversion_command(ROOT, Path(out_dir), scenario, tool, jobs)
        return run_command(scenario, iteration, command, ROOT, verbose)


def git_revision() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def bash_version() -> str | None:
    try:
        first = subprocess.check_output(["bash", "--version"], text=True).splitlines()[0]
        return first.strip()
    except (OSError, subprocess.CalledProcessError, IndexError):
        return None


def print_table(measurements: Iterable[Measurement]) -> None:
    rows = list(measurements)
    print(f"{'scenario':22} {'run':>3} {'wall(s)':>10} {'cpu(s)':>10} {'rc':>3}")
    print("-" * 54)
    for item in rows:
        print(
            f"{item.scenario:22} {item.iteration:>3} "
            f"{item.wall_seconds:>10.3f} {item.cpu_seconds:>10.3f} {item.returncode:>3}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        action="append",
        choices=SCENARIOS,
        help="scenario to run; repeat the flag to select several (default: all)",
    )
    parser.add_argument("--repeat", type=int, default=1, help="number of runs per scenario")
    parser.add_argument("--tool", default="codex", help="representative tool renderer")
    parser.add_argument("--jobs", type=int, default=0, help="parallel worker count; 0 uses convert.sh default")
    parser.add_argument(
        "--changed-agent",
        type=Path,
        default=DEFAULT_AGENT,
        help="source agent perturbed in the isolated one-agent-change scenario",
    )
    parser.add_argument("--json", type=Path, help="write machine-readable results to this path")
    parser.add_argument("--verbose", action="store_true", help="show converter output while benchmarking")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be >= 1")
    if args.jobs < 0:
        parser.error("--jobs must be >= 0")
    return args


def main() -> int:
    args = parse_args()
    scenarios = args.scenario or list(SCENARIOS)
    measurements: list[Measurement] = []

    for scenario in scenarios:
        for iteration in range(1, args.repeat + 1):
            result = run_scenario(
                scenario,
                iteration,
                args.tool,
                args.jobs,
                args.changed_agent,
                args.verbose,
            )
            measurements.append(result)
            if result.returncode != 0:
                print_table(measurements)
                print(f"benchmark failed: {scenario} returned {result.returncode}", file=sys.stderr)
                return result.returncode

    metadata = {
        "revision": git_revision(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "python": platform.python_version(),
        "bash": bash_version(),
        "representative_tool": args.tool,
        "changed_agent": args.changed_agent.as_posix(),
        "repeat": args.repeat,
    }
    payload = {
        "metadata": metadata,
        "measurements": [asdict(item) for item in measurements],
    }

    print_table(measurements)
    print("\nmetadata:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
