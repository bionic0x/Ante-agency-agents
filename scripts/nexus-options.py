#!/usr/bin/env python3
"""Compatibility entry point. Implementation: ante.nexus.options (see ante/_compat.py).

Compare declared factors without weighted scores or compensating fatal defects.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from ante._compat import adopt  # noqa: E402

adopt(globals(), 'ante.nexus.options')
