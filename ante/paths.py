"""Repository locations, resolved from the package rather than from a caller's file.

Code extracted from ``scripts/`` used ``Path(__file__).resolve().parents[1]``.
That expression means "the repository root" only for a file one level below it;
the package computes the same root once, here.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
STRATEGY = ROOT / 'strategy'
CONTRACTS = STRATEGY / 'contracts.json'
PROTECTED = STRATEGY / 'overdrive-protected.json'
