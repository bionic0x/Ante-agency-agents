#!/usr/bin/env python3
import hashlib
import datetime as dt
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('capabilities', ROOT / 'scripts/agent-capabilities.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
NOW = dt.datetime(2026, 9, 15, tzinfo=dt.timezone.utc)

class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.agent = 'agents-orchestrator'
        self.policy = {'host': 'claude-code', 'agent_id': self.agent, 'scope': 'fixture review',
                       'owner': 'Fixture owner', 'authority_ref': 'fixture-only',
                       'expires': '2026-09-16T00:00:00Z', 'allowed_tools': ['Read']}
        self.observation = {'host': 'claude-code', 'agent_id': self.agent, 'host_version': 'fixture',
                            'evidence_ref': 'fixture-only', 'configuration_ref': 'fixture-config',
                            'observed_at': '2026-09-14T00:00:00Z', 'valid_until': '2026-09-16T00:00:00Z',
                            'resolved_tools': ['Read', 'Bash'],
                            'source_sha256': hashlib.sha256(m.resolve_agent(self.agent).read_bytes()).hexdigest()}

    def test_omission_is_unknown_not_none(self):
        r = m.inspect(self.agent, at=NOW)
        self.assertEqual('HOST_INHERITED', r['declaration_state'])
        self.assertIsNone(r['host_resolved_capabilities'])
        self.assertEqual('unspecified', r['declared_class'])
        self.assertFalse(r['verified_authority'])

    def test_supplied_host_tools_do_not_create_authority(self):
        r = m.inspect(self.agent, self.observation, self.policy, NOW)
        self.assertEqual(['Bash'], r['outside_scope_policy'])
        self.assertEqual(['Read'], r['candidate_authorized_capabilities'])
        self.assertFalse(r['verified_authority'])

    def test_rejects_expired_or_wrong_observation(self):
        for field, value in [('valid_until', '2020-01-01T00:00:00Z'), ('agent_id', 'someone-else')]:
            o = {**self.observation, field: value}
            with self.assertRaises(ValueError): m.inspect(self.agent, o, at=NOW)

    def test_policy_requires_registered_tokens_and_live_scope(self):
        for field, value in [('allowed_tools', ['Bash']), ('expires', '2020-01-01T00:00:00Z'), ('owner', '')]:
            with self.assertRaises(ValueError): m.inspect(self.agent, policy={**self.policy, field: value}, at=NOW)

    def test_render_is_scoped_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'orchestrator.md'
            r = m.render(self.agent, self.policy, p, NOW)
            self.assertIn('\ntools: Read\n', p.read_text())
            self.assertFalse(r['authority_granted'])
            with self.assertRaises(ValueError): m.render(self.agent, self.policy, p, NOW)

    def test_cannot_expand_explicit_profile(self):
        source = next(p for p in m.privileges.agent_files(ROOT)
                      if 'tools' in m.privileges.frontmatter(p) and
                      'Write' not in m.privileges.parse_tools(m.privileges.frontmatter(p)['tools']))
        policy = {**self.policy, 'agent_id': source.stem, 'allowed_tools': ['Write']}
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, 'cannot expand'):
                m.render(source.stem, policy, Path(d) / 'agent.md', NOW)

    def test_explicit_null_is_invalid(self):
        with self.assertRaises(ValueError): m.privileges.parse_tools(None)

if __name__ == '__main__': unittest.main()
