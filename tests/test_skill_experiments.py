import copy
import json
import tempfile
import unittest
from pathlib import Path
from astrafactory.skill_experiments import append_event, artifact, digest, read_ledger, snapshot

class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.ledger = self.root/'ledger.jsonl'
        self.evidence = self.root/'evaluation.json'; self.evidence.write_text('{"successes":1}')
        self.proposal = {'hypothesis': 'Test a distinct candidate', 'retrospective': False,
            'skill_graph': {'nodes': [{'id': 'grasp', 'label': 'grasp', 'implementation': 'learned', 'inputs': 'camera'}], 'edges': []},
            'model': {'parameter_count': 5}, 'data': {'training_seeds': [1]}, 'training': {'wall_seconds': None},
            'changes': {'reward': None, 'domain_randomization': None},
            'evaluation': {'thresholds': {'hold_seconds': .5}, 'evaluator_sha256': 'a'*64, 'seeds': [20], 'split': 'development', 'promotion_min_success_rate': 1.0}}
    def append(self, kind, payload): return append_event(self.ledger, 'candidate', kind, payload, self.root)
    def result(self, successes=1):
        return {'evaluation_fingerprint': digest(self.proposal['evaluation']), 'seeds': [20], 'episodes': 1, 'successes': successes, 'evidence': [artifact(self.evidence, self.root)]}
    def test_append_preserves_prefix_and_accepts_measured_threshold(self):
        self.append('proposal', self.proposal); prefix = self.ledger.read_bytes()
        self.append('result', self.result()); self.assertTrue(self.ledger.read_bytes().startswith(prefix))
        self.append('promotion', {'decision': 'accepted', 'reason': 'Frozen threshold met'})
        self.assertEqual(snapshot(self.ledger, self.root)['experiments'][0]['evidence_integrity'], 'verified')
    def test_changed_evaluator_or_seed_is_rejected(self):
        self.append('proposal', self.proposal)
        for changes in ({'evaluation_fingerprint': 'wrong'}, {'seeds': [21]}):
            result = self.result(); result.update(changes)
            with self.assertRaises(ValueError): self.append('result', result)
        self.assertEqual(len(read_ledger(self.ledger)), 1)
    def test_evidence_mutation_blocks_promotion_and_is_visible(self):
        self.append('proposal', self.proposal); self.append('result', self.result())
        self.evidence.write_text('{}')
        with self.assertRaises(ValueError): self.append('promotion', {'decision': 'accepted', 'reason': 'Claim'})
        self.assertEqual(snapshot(self.ledger, self.root)['experiments'][0]['evidence_integrity'], 'missing_or_changed')
    def test_tampering_detected(self):
        self.append('proposal', self.proposal)
        self.ledger.write_text(self.ledger.read_text().replace('Test a distinct candidate', 'Fabricated change'))
        with self.assertRaises(ValueError): read_ledger(self.ledger)
    def test_overlap_retrospective_and_failed_result_cannot_promote(self):
        p = copy.deepcopy(self.proposal); p['data']['training_seeds'] = [20]
        with self.assertRaises(ValueError): self.append('proposal', p)
        self.proposal['retrospective'] = True; self.append('proposal', self.proposal); self.append('result', self.result())
        with self.assertRaises(ValueError): self.append('promotion', {'decision': 'accepted', 'reason': 'Claim'})
    def test_failed_result_cannot_promote(self):
        self.append('proposal', self.proposal); self.append('result', self.result(0))
        with self.assertRaises(ValueError): self.append('promotion', {'decision': 'accepted', 'reason': 'Claim'})
    def test_paired_gate_rejects_regression_and_accepts_strict_gain(self):
        self.proposal['evaluation']['comparison'] = 'paired_success_strict_improvement_no_regression'
        self.append('proposal', self.proposal)
        r = self.result(); r['paired_outcomes'] = [{'seed': 20, 'baseline_success': False, 'candidate_success': True}]
        r['baseline_evidence'] = [artifact(self.evidence, self.root)]
        self.append('result', r); self.append('promotion', {'decision': 'accepted', 'reason': 'One strict paired gain'})
    def test_paired_gate_rejects_equal_success(self):
        self.proposal['evaluation']['comparison'] = 'paired_success_strict_improvement_no_regression'
        self.append('proposal', self.proposal)
        r = self.result(); r['paired_outcomes'] = [{'seed': 20, 'baseline_success': True, 'candidate_success': True}]
        r['baseline_evidence'] = [artifact(self.evidence, self.root)]
        self.append('result', r)
        with self.assertRaises(ValueError): self.append('promotion', {'decision': 'accepted', 'reason': 'No real improvement'})
    def test_provenance_note_blocks_promotion_without_rewriting_proposal(self):
        self.append('proposal', self.proposal); prefix = self.ledger.read_bytes()
        self.append('note', {'message': 'Written metadata differs from actual frozen evaluator', 'blocks_promotion': True})
        self.append('result', self.result())
        with self.assertRaises(ValueError): self.append('promotion', {'decision': 'accepted', 'reason': 'Cannot overlook mismatch'})
        self.assertTrue(self.ledger.read_bytes().startswith(prefix))
        self.assertEqual(len(snapshot(self.ledger, self.root)['experiments'][0]['notes']), 1)
    def test_duplicate_result_rejected(self):
        self.append('proposal', self.proposal); self.append('result', self.result())
        with self.assertRaises(ValueError): self.append('result', self.result())

if __name__ == '__main__': unittest.main()
