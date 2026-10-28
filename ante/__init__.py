"""Ante Foundation: the shared package behind the ``ante`` command and the
compatibility scripts under ``scripts/``.

Layers:
    ante.core       strict JSON input, canonical hashing, schema checks, time
    ante.doctrine   canonical enums loaded from strategy/contracts.json
    ante.nexus      NEXUS engine programs extracted from scripts/
    ante.registry   catalog, divisions, tools and runbook resolution

Nothing in this package grants authority to act in the world. Decision outputs
are records for a human owner.
"""

__version__ = '0.1.0'
