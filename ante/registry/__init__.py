"""Catalog, divisions, tools and runbooks.

The installer runtime (``install.sh`` → ``resolve-agents.py`` → ``build-catalog.py``,
and ``registry.py`` for the shell) must run from a copy of ``scripts/`` alone: the
protected ``test-install-functional.py`` installs from exactly such a copy. Those
programs therefore stay self-contained in ``scripts/`` (decision D-008), and this
package reads them instead of moving them.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ante._compat import load_script
from ante.paths import ROOT

RUNBOOKS = ROOT / 'strategy' / 'runbooks.json'


@lru_cache(maxsize=1)
def _catalog_module():
    return load_script('build-catalog.py', 'ante_registry_catalog')


@lru_cache(maxsize=1)
def _registry_module():
    return load_script('registry.py', 'ante_registry_registry')


def agents() -> list[dict]:
    """Every canonical agent with its frontmatter fields (``build-catalog.collect``)."""
    _divisions, roster, _runbooks = _catalog_module().collect()
    return roster


def agent_slugs() -> set[str]:
    return {agent['slug'] for agent in agents()}


def divisions() -> dict:
    return _registry_module().load_section('divisions', ROOT / 'divisions.json')


def tools() -> list[tuple[str, dict]]:
    module = _registry_module()
    return module.ordered_tools(module.load_section('tools', ROOT / 'tools.json'))


def runbooks(path: Path = RUNBOOKS) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding='utf-8'))
    return {runbook['slug']: runbook for runbook in data['runbooks']}
