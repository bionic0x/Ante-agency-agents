"""ante.core: strict input, canonical profiles, schema and time."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ante.core import canon, io, schema, time  # noqa: E402
from ante import doctrine  # noqa: E402


class StrictInput(unittest.TestCase):
    def write(self, text, suffix='.json'):
        handle = tempfile.NamedTemporaryFile('w', suffix=suffix, delete=False, encoding='utf-8')
        handle.write(text)
        handle.close()
        self.addCleanup(Path(handle.name).unlink)
        return Path(handle.name)

    def test_duplicate_keys_are_rejected_at_any_depth(self):
        for text in ('{"a": 1, "a": 2}', '{"x": {"b": 1, "b": 1}}', '[{"k": 0, "k": 0}]'):
            with self.assertRaisesRegex(io.InputError, 'duplicate object key'):
                io.load_json(self.write(text))

    def test_non_finite_numbers_are_rejected(self):
        for token in ('NaN', 'Infinity', '-Infinity'):
            with self.assertRaisesRegex(io.InputError, 'non-finite'):
                io.load_json(self.write(f'{{"v": {token}}}'))

    def test_errors_never_echo_content(self):
        secret = 'sk-live-THIS-MUST-NOT-LEAK'
        for text in (f'{{"a": "{secret}", "a": 1}}', f'{{"a": "{secret}"', f'"{secret}'):
            with self.assertRaises(io.InputError) as caught:
                io.load_json(self.write(text))
            self.assertNotIn(secret, str(caught.exception))

    def test_size_is_bounded_before_parsing(self):
        with self.assertRaisesRegex(io.InputError, 'larger than 8 bytes'):
            io.load_json(self.write('{"a": "0123456789"}'), max_bytes=8)

    def test_missing_file_is_named_not_traced(self):
        with self.assertRaisesRegex(io.InputError, 'nope.json: file not found'):
            io.load_json(Path(tempfile.gettempdir()) / 'nope.json')

    def test_yaml_follows_the_same_rules(self):
        self.assertEqual({'a': [1, 2]}, io.load_document(self.write('a: [1, 2]\n', '.yaml')))
        with self.assertRaisesRegex(io.InputError, 'duplicate object key'):
            io.load_document(self.write('a: 1\na: 2\n', '.yml'))
        with self.assertRaisesRegex(io.InputError, 'no JSON equivalent'):
            io.load_document(self.write('a: .nan\n', '.yaml'))


class CanonicalProfiles(unittest.TestCase):
    VALUE = {'b': 'ñ', 'a': [1, 2.5, None, True], 'c': {'z': 0, 'y': 'x'}}

    def test_profiles_reproduce_the_historical_byte_streams(self):
        historical = {
            canon.ASCII: json.dumps(self.VALUE, sort_keys=True, separators=(',', ':'), ensure_ascii=True),
            canon.ASCII_STRICT: json.dumps(self.VALUE, sort_keys=True, separators=(',', ':'), allow_nan=False),
            canon.UNICODE: json.dumps(self.VALUE, sort_keys=True, separators=(',', ':'), ensure_ascii=False),
            canon.UNICODE_STRICT: json.dumps(self.VALUE, sort_keys=True, separators=(',', ':'),
                                             ensure_ascii=False, allow_nan=False),
        }
        for profile, expected in historical.items():
            self.assertEqual(expected, canon.dumps(self.VALUE, profile), profile.name)
            self.assertEqual(hashlib.sha256(expected.encode()).hexdigest(), canon.digest(self.VALUE, profile))

    def test_strict_profiles_refuse_nan(self):
        with self.assertRaises(ValueError):
            canon.dumps({'v': float('nan')}, canon.UNICODE_STRICT)

    def test_digest_ignores_key_order(self):
        self.assertEqual(canon.digest({'a': 1, 'b': 2}), canon.digest({'b': 2, 'a': 1}))


class Schema(unittest.TestCase):
    def test_booleans_are_not_integers(self):
        with self.assertRaises(schema.SchemaError):
            schema.integer(True, 'x')
        with self.assertRaises(schema.SchemaError):
            schema.number(False, 'x')
        self.assertIs(schema.boolean(False, 'x'), False)

    def test_exact_keys_names_missing_and_unknown_fields(self):
        with self.assertRaisesRegex(schema.SchemaError, r'root: missing field\(s\) b'):
            schema.exact_keys({'a': 1}, ['a', 'b'], 'root')
        with self.assertRaisesRegex(schema.SchemaError, r'root: unknown field\(s\) z'):
            schema.exact_keys({'a': 1, 'z': 2}, ['a'], 'root')

    def test_blank_text_and_duplicate_ids_fail(self):
        with self.assertRaises(schema.SchemaError):
            schema.text('   ', 'name')
        with self.assertRaisesRegex(schema.SchemaError, 'duplicate id'):
            schema.unique_ids([{'id': 'a'}, {'id': 'a'}], 'items')


class Time(unittest.TestCase):
    def test_offset_is_required_and_normalised(self):
        self.assertEqual('2026-10-28T15:00:00Z', time.iso(time.parse('2026-10-28T16:00:00+01:00')))
        self.assertEqual('2026-10-28T15:00:00Z', time.iso(time.parse('2026-10-28T15:00:00Z')))
        with self.assertRaisesRegex(time.TimeError, 'timezone offset required'):
            time.parse('2026-10-28T15:00:00')
        with self.assertRaisesRegex(time.TimeError, 'not ISO-8601'):
            time.parse('yesterday')


class Doctrine(unittest.TestCase):
    def test_enums_come_from_contracts_json(self):
        raw = json.loads((Path(__file__).resolve().parents[2] / 'strategy/contracts.json').read_text())
        d = doctrine.load()
        self.assertEqual(tuple(raw['epistemic_states']), d.epistemic_states)
        self.assertEqual(tuple(raw['decision_states']), d.decision_states)
        self.assertIn('HOLD', d.decision_states)

    def test_absent_tables_fail_loudly_instead_of_falling_back(self):
        d = doctrine.load()
        if not d.has('coherence_tests'):
            with self.assertRaises(doctrine.MissingTable):
                d.table('coherence_tests')


if __name__ == '__main__':
    unittest.main()
