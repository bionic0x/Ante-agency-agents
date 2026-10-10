#!/usr/bin/env python3
"""NEXUS Relay entry point. See relay/DESIGN.md and relay/README.md."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "relay"))

from nexus_relay.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
