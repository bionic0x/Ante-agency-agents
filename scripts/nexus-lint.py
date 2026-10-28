#!/usr/bin/env python3
"""Compatibility entry point. Implementation: ante.nexus.lint (see ante/_compat.py).

nexus-lint.py — check a NEXUS instance's plan before the owner adopts it (Overdrive, Phase 2).
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from ante._compat import adopt  # noqa: E402

adopt(globals(), 'ante.nexus.lint')
