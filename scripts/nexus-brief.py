#!/usr/bin/env python3
"""Compatibility entry point. Implementation: ante.nexus.brief (see ante/_compat.py).

nexus-brief.py — the owner's decision brief for a NEXUS instance (Overdrive, Phase 3).
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from ante._compat import adopt  # noqa: E402

adopt(globals(), 'ante.nexus.brief')
