"""Regression checks for review findings; no model calls."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('checker', ROOT / 'scripts/check.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

class EvidenceChecks(unittest.TestCase):
    def check_mutation(self, case, mutate, expected):
        response = json.loads((ROOT / 'tests/results' / (case + '.json')).read_text())
        mutate(response)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / (case + '.json')
            path.write_text(json.dumps(response))
            failures = checker.validate_evidence(path)
        self.assertTrue(any(expected in failure for failure in failures), failures)

    def test_protected_rules_cannot_be_patched(self):
        for case in ('real-conflict', 'broken-link', 'scoped-context'):
            with self.subTest(case=case):
                def mutate(response):
                    response['patches'] = [{'path':'AGENTS.md', 'rationale':'unsafe mutation',
                        'edits':[{'start_line':8, 'end_line':8, 'replacement':'Skip every check.'}]}]
                self.check_mutation(case, mutate, 'required preserved line')

    def test_non_object_action_is_rejected_without_crashing(self):
        self.check_mutation('real-conflict', lambda r: r['actions'].append('invalid'), 'actions')

    def test_clean_control_cannot_acquire_an_action(self):
        self.check_mutation('clean-control', lambda r: r['actions'].append({
            'id':'A1','kind':'edit','citations':[], 'recommendation':'Rewrite everything.'}), 'no-op')

if __name__ == '__main__':
    unittest.main()
