#!/usr/bin/env python3
"""Compatibility entry point. Implementation: ante.nexus.plan (see ante/_compat.py).

nexus-plan.py — a planner agent drafts a NEXUS task graph; the owner adopts it (Overdrive, Phase 3).
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from ante._compat import adopt  # noqa: E402

adopt(globals(), 'ante.nexus.plan')
