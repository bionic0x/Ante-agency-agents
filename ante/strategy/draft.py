"""``--draft-with PROVIDER --model ID``: a model drafts a command's input, unsigned.

Drafting is the only path in the strategy layer that calls a model, and only when
asked. The result is **not** an artefact and cannot be chained:

- every claim is forced to ``HYPOTHESIS`` with ``source.origin = "system"``, so
  nothing a model wrote can enter a chain as evidence (invariant 7);
- the proposed input sits under ``"input"`` beside a ``"draft"`` header with
  ``signed: false``; a human edits it, removes the header, and runs the command
  on the edited file — that run produces the artefact;
- the provider must be declared in ``strategy/providers.json`` and have an
  adapter here; the model id is explicit (no model is selected from memory).

INPUT is a brief: free text describing the situation the draft should cover.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ante.core import io
from ante.paths import ROOT, STRATEGY


class DraftError(ValueError):
    pass


def _anthropic(model: str, prompt: str) -> str:
    from ante.nexus import anthropic
    try:
        result = anthropic._invoke(model, prompt, ROOT)
    except anthropic.AdapterError as exc:
        raise DraftError(f'anthropic adapter: {exc}') from None
    return result.get('output') or ''


ADAPTERS = {'anthropic': _anthropic}


def _providers() -> set[str]:
    data = json.loads((STRATEGY / 'providers.json').read_text(encoding='utf-8'))
    providers = data['providers']
    return set(providers) if isinstance(providers, dict) else {p['id'] for p in providers}


def _first_json_object(text: str) -> dict:
    fenced = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.S)
    candidate = fenced.group(1) if fenced else text[text.find('{'): text.rfind('}') + 1]
    try:
        value = io.parse_json(candidate, 'draft')
    except io.InputError as exc:
        raise DraftError(f'the model did not return one strict JSON object ({exc})') from None
    if not isinstance(value, dict):
        raise DraftError('the model did not return a JSON object')
    return value


def prompt_for(command, brief: str, parents: list[dict]) -> str:
    from ante.strategy.commands import COMMANDS
    module_doc = __import__(command.run.__module__, fromlist=['__doc__']).__doc__ or ''
    upstream = [{'command': p['command'], 'body': p['body'], 'claims': p['claims']} for p in parents]
    return (
        f'Draft the input document for the `ante {command.name}` command.\n\n'
        f'Specification:\n{module_doc}\n\n'
        f'Envelope fields: "claims" (list of {{id, text, status, source: {{ref, origin}}, date, limit}}). '
        f'Commands available: {", ".join(COMMANDS)}.\n\n'
        f'Upstream artefacts (JSON):\n{json.dumps(upstream, ensure_ascii=False)}\n\n'
        f'Brief:\n{brief}\n\n'
        'Return exactly one JSON object and nothing else. Mark anything you are not certain of as UNKNOWN.'
    )


def draft(command, brief_path: str, parents: list[dict], provider: str, model: str | None, at: str) -> dict:
    if provider not in _providers():
        raise DraftError(f'provider {provider} is not declared in strategy/providers.json')
    if provider not in ADAPTERS:
        raise DraftError(f'no drafting adapter for provider {provider}')
    if not model:
        raise DraftError('--model is required with --draft-with (no model is chosen from memory)')
    brief = io.read_text(brief_path, Path(brief_path).name)
    proposal = _first_json_object(ADAPTERS[provider](model, prompt_for(command, brief, parents)))
    proposal.pop('at', None)
    for claim in proposal.get('claims', []) if isinstance(proposal.get('claims'), list) else []:
        if isinstance(claim, dict):
            claim['status'] = 'HYPOTHESIS'
            claim['source'] = {'ref': f'draft:{provider}:{model}', 'origin': 'system'}
    return {
        'draft': {'command': command.name, 'provider': provider, 'model': model, 'drafted_at': at,
                  'signed': False, 'status': 'HYPOTHESIS',
                  'instructions': 'Review and edit the input, remove this header, then run the command on it.'},
        'input': proposal,
    }
