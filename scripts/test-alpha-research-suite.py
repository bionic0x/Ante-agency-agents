#!/usr/bin/env python3
"""Check the six synthetic Alpha Research Suite examples, not investment outcomes."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROFILES = (
    "finance-market-data-research-integrity",
    "finance-portfolio-risk-allocation-architect",
    "finance-onchain-capital-flows-market-structure",
    "finance-protocol-fundamentals-token-value-capture",
    "finance-catalyst-expectations-analyst",
    "finance-investment-thesis-challenger",
)

def main():
    contract = (ROOT / "strategy/alpha-research-suite/README.md").read_text(encoding="utf-8")
    assert "No profile may place orders" in contract
    assert "P8" in contract and "review_status" in contract
    fence = chr(96) * 3
    example_re = r"^" + re.escape(fence) + r"python\s*\n(.*?)^" + re.escape(fence) + r"[ \t]*$"
    for slug in PROFILES:
        text = (ROOT / "finance" / (slug + ".md")).read_text(encoding="utf-8")
        fm = text.split("\n---\n", 1)[0]
        assert text.startswith("---\n") and "mode: decision-support-only" in fm
        assert "status: proposed-agent-specification" in fm
        scripts = re.findall(example_re, text, flags=re.M | re.S)
        assert len(scripts) == 1, f"{slug}: expected one Python code example"
        p = subprocess.run([sys.executable, "-I", "-c", scripts[0]],
                           capture_output=True, text=True, timeout=15)
        assert p.returncode == 0, f"{slug}: {p.stdout}\n{p.stderr}"
        assert "passed" in p.stdout.lower(), f"{slug}: no success assertion"
    print("PASSED: six Alpha Research Suite synthetic examples")
    return 0

if __name__ == "__main__":
    sys.exit(main())
