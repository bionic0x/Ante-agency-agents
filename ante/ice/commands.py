"""``ante ice``: seed and scan canaries, check layer independence.

    ante ice seed PACK_DIR --registry FILE     before nexus-casepack.py freeze
    ante ice scan PATH... [--registry FILE]    exit 1 on any canary
    ante ice layers [--layers FILE]            exit 1 if two layers share data or an assumption
"""
from __future__ import annotations

import argparse
import json
import sys

from ante.core import io
from ante.ice import canary, layers


def add_parser(sub) -> None:
    ice = sub.add_parser('ice', help='canaries in held-out packs and independence of the defensive layers')
    isub = ice.add_subparsers(dest='ice_command', required=True)
    seed = isub.add_parser('seed')
    seed.add_argument('pack')
    seed.add_argument('--registry', required=True)
    scan = isub.add_parser('scan')
    scan.add_argument('paths', nargs='+')
    scan.add_argument('--registry')
    lay = isub.add_parser('layers')
    lay.add_argument('--layers', help=argparse.SUPPRESS)
    ice.set_defaults(handler=main)


def main(args) -> int:
    try:
        if args.ice_command == 'layers':
            return layers.main(args)
        if args.ice_command == 'seed':
            print(json.dumps(canary.seed(args.pack, args.registry), indent=2))
            return 0
        hits = canary.scan(args.paths, args.registry)
        for hit in hits:
            print(f"CONTAMINATION {hit['where']}: {hit['canary']} (pack {hit['pack'] or 'unknown'})")
        if not hits:
            print(f'ice: no canary in {len(args.paths)} path(s)')
        return 1 if hits else 0
    except (canary.CanaryError, io.InputError, OSError) as exc:
        print(f'INVALID {exc}', file=sys.stderr)
        return 2
