#!/usr/bin/env python3
"""Compatibility entry point. Implementation: ante.nexus.routing (see ante/_compat.py).

nexus-routing.py — select execution targets by level, vector and factor.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from ante._compat import adopt  # noqa: E402

adopt(globals(), 'ante.nexus.routing')
