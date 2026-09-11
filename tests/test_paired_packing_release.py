"""Checks for the supported-release experiment, not harvest qualification."""
from pathlib import Path
import json,unittest
import mujoco as mj
import numpy as np
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'runs/tower-lift-v15';B=RUN/'gate-bench'

class PairedPackingChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (B/'commission-summary.json').exists():raise unittest.SkipTest('Generate and summarize the paired release experiment first')
        cls.m=mj.MjModel.from_xml_path(str(B/'scene.xml'));cls.summary=json.loads((B/'commission-summary.json').read_text())

    def test_fixture_and_gate_cad_clearances(self):
        self.assertTrue(self.summary['fixture_fit']['passed'])
        sweep=json.loads((RUN/'cad/gate-sweep-checks.json').read_text())
        self.assertEqual(len(sweep['records']),48)
        self.assertTrue(all(r['intersection_mm3']<.01 for r in sweep['records']))

    def test_passive_release_and_fixture_collision_masks(self):
        m=self.m
        self.assertEqual(m.jnt_type[m.joint('right_net_free').id],mj.mjtJoint.mjJNT_FREE)
        gate=m.joint('right_gate_hinge').id
        self.assertFalse(np.any(m.actuator_trnid[:,0]==gate));self.assertEqual(m.neq,0)
        for name in ['roller_spin','roller_spin_opposite']:self.assertIsNotNone(m.joint(name))
        for body in ['pack_gate_fork','pack_gate_fork_opposite','pack_gate_roller_post_opposite']:
            geoms=[i for i in range(m.ngeom) if m.geom_bodyid[i]==m.body(body).id and m.geom_contype[i]]
            self.assertGreater(len(geoms),0)
            for i in geoms:
                tool=m.geom('gate_trigger_contact').id
                self.assertTrue((m.geom_contype[i]&m.geom_conaffinity[tool]) or (m.geom_contype[tool]&m.geom_conaffinity[i]))

    def test_deposition_at_two_steps_does_not_claim_qualification(self):
        self.assertEqual(len(self.summary['cases']),2)
        for c in self.summary['cases']:
            self.assertTrue(c['deposition_observed']);self.assertTrue(c['net_empty'])
            self.assertEqual(c['result']['warnings'],0)
            # These are explicitly sampled checks, not an all-time peak claim.
            for key in ['net_fixture','robot_fixture','interarm']:
                self.assertLess(c['result']['peak_forces_N'][key],.01)
        self.assertFalse(self.summary['release_ready'])
        self.assertFalse(self.summary['damage_validated']);self.assertFalse(self.summary['learned_policy'])

    def test_force_audit_resolves_brief_impacts(self):
        for c in self.summary['cases']:
            r=c['result'];f=r['solver_step_fruit_contacts']
            self.assertAlmostEqual(f['sampling_hz'],1/r['dt'])
            self.assertGreaterEqual(f['peak_fixture_force_N'],r['peak_forces_N']['berry_fixture'])
            self.assertIn('container_floor',f['first_fixture_event']['parts'])
            self.assertGreater(f['first_fixture_event']['time_s'],1)

if __name__=='__main__':unittest.main()
