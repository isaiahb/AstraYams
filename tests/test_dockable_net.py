"""Regression gates bind the CAD review to the actual recorded bench assets."""
import hashlib,json,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'runs/tower-lift-v16/tool-study'

def load(name):return json.loads((P/name).read_text())

class DockableNetEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (P/'retention-bench/docking-summary.json').exists():
            raise unittest.SkipTest('Build V16 and run its retention/docking experiments first')

    def test_interference_and_form_capture(self):
        report=load('design.json')
        assert len(report['checks'])>=30
        assert max(x['overlap_mm3'] for x in report['checks'])<.001
        assert all(x['overlap_mm3']>1 for x in report['shear_blocking'])
        assert all(x['valid'] for x in report['parts'])
        assert all(x['solid_count']==1 for x in report['parts'] if x['name']!='net_textile')

    def test_retention_evidence_uses_current_cad(self):
        report=load('retention-bench/summary.json')
        for name,expected in report['cad_sha256'].items():
            assert hashlib.sha256((P/'cad'/name).read_bytes()).hexdigest()==expected
        cases={x['label']:x for x in report['tests']}
        for name in ['low-friction','half-timestep']:
            r=cases[name]
            assert r['max_key_shift_mm']<1 and r['max_tool_rotation_deg']<2
            assert r['finite'] and r['warnings']==0
            assert r['peak_contact_force_N']<50
        # Frictionless challenge establishes retention, not the 2-degree precision target.
        assert cases['zero-friction']['max_key_shift_mm']<1
        assert cases['open-jaw-control']['final_key_shift_mm']>50

    def test_dock_release_leaves_no_finger_contact(self):
        reports=load('retention-bench/docking-summary.json')
        assert {r['dt_s'] for r in reports}=={.00025,.000125}
        for r in reports:
            for name,expected in r['cad_sha256'].items():
                assert hashlib.sha256((P/'cad'/name).read_bytes()).hexdigest()==expected
            assert r['net_supported_by_dock'] and not r['finger_contact_remaining']
            assert r['max_net_origin_shift_mm']<2
            assert abs(r['stage_final_m'][0]+.068)<.001
            assert r['warnings']==0 and r['peak_contact_N']<20
