"""Check the generated photo rig's topology and finite-actuator replay.

Dimensions below establish agreement with the editable reconstruction, not the
real apparatus. Run tools/build_tower_lift.py and review_tower_lift.py first.
"""
from pathlib import Path
import json
import unittest
import mujoco
import numpy as np
from astrafactory.tower_lift import TowerLiftEnv

ROOT = Path(__file__).resolve().parents[1] / 'runs/tower-lift-v3'


@unittest.skipUnless((ROOT/'rig/scene.xml').exists(), 'Build v3 first')
class PhotoRigChecks(unittest.TestCase):
    def test_braces_in_two_side_planes_and_posts_above_crossbeam(self):
        m = mujoco.MjModel.from_xml_path(str(ROOT/'rig/scene.xml'))
        d = mujoco.MjData(m)
        mujoco.mj_forward(m, d)
        c = json.loads((ROOT/'config.json').read_text())['frame']
        braces = [b for b in range(m.nbody) if m.body(b).name.startswith('side_brace_')]
        self.assertEqual(len(braces), 4)
        for b in braces:
            # Invisible box is the physical envelope, in the same local frame
            # as the STEP-derived member. Its endpoints must meet the frame.
            g = next(g for g in range(m.ngeom) if m.geom_bodyid[g] == b
                     and m.geom_type[g] == mujoco.mjtGeom.mjGEOM_BOX)
            axis = d.geom_xmat[g].reshape(3, 3)[:, 2]
            ends = np.array([d.geom_xpos[g]-axis*m.geom_size[g, 2],
                             d.geom_xpos[g]+axis*m.geom_size[g, 2]])
            self.assertAlmostEqual(ends[0, 0], ends[1, 0])
            self.assertAlmostEqual(abs(ends[0, 0]), (c['width_m']-c['profile_m'])/2)
            np.testing.assert_allclose(sorted(ends[:, 2]),
                                       [c['profile_m']/2, c['brace_attachment_height_m']], atol=1e-6)
            np.testing.assert_allclose(sorted(abs(ends[:, 1])), [0, c['depth_m']/2-.025], atol=1e-6)
        self.assertLess(d.xpos[m.body('crossbar_working').id, 2], c['height_m']-.5)
        self.assertFalse(any('rear_x' in m.body(b).name for b in range(m.nbody)))

    def test_photographed_payload_and_proposed_arms_are_distinct_models(self):
        for kind, nu in [('rig', 1), ('so101', 13), ('yam', 15)]:
            e = TowerLiftEnv(ROOT/kind)
            e.reset()
            names = {e.model.body(b).name for b in range(e.model.nbody)}
            self.assertEqual(e.model.nu, nu)
            self.assertEqual('circular_payload' in names, kind == 'rig')
            self.assertEqual('proposed_arm_bridge' in names, kind != 'rig')
            if kind == 'rig':
                self.assertFalse(any(n.startswith(('left_', 'right_')) for n in names))
            self.assertIn('crown', names)

    def test_compact_parts_are_valid_solids_and_guide_channel_is_open(self):
        import cadquery as cq
        for name in ['carriage_plate', 'guide_block', 'side_brace', 'corner_plate', 'bridge_bracket']:
            part = cq.importers.importStep(str(ROOT/'cad'/f'{name}.step'))
            self.assertTrue(part.val().isValid(), name)
            self.assertEqual(len(part.solids().vals()), 1, name)
        block = cq.importers.importStep(str(ROOT/'cad/guide_block.step'))
        probe = cq.Workplane('XY').box(20, 20, 60)
        self.assertLess(sum(s.Volume() for s in block.intersect(probe).solids().vals()), 1e-5)

    def test_unpowered_carriage_falls_instead_of_following_setpoint(self):
        e = TowerLiftEnv(ROOT/'rig')
        e.reset()
        before = float(e.data.qpos[e.qids[e.lift]])
        e.model.actuator_forcerange[e.lift] = [0, 0]
        for _ in range(5):
            _, _, invalid, _, info = e.step(np.ones(1))
        self.assertFalse(invalid)
        self.assertGreater(e.target[e.lift], before)
        self.assertLess(info['lift_height_m'], before-.005)
        self.assertEqual(info['lift_force_N'], 0.)

    def test_recorded_motion_is_finite_and_within_actuator_limits(self):
        for kind in ['rig', 'so101', 'yam']:
            result = json.loads((ROOT/kind/'commission/result.json').read_text())
            self.assertFalse(result['invalid'])
            self.assertEqual(result['simulator_warning_count'], 0)
            peaks = np.array(result['peak_actuator_force_N_or_Nm'])
            limits = np.abs(result['actuator_force_limits']).max(axis=1)
            self.assertTrue(np.all(np.isfinite(peaks)))
            self.assertTrue(np.all(peaks <= limits+1e-8))
            self.assertGreater(result['lift_height_max_m']-result['lift_height_min_m'], .10)
            self.assertIsNone(result['harvest_success'])


if __name__ == '__main__':
    unittest.main()
