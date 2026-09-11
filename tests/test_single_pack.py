"""Acceptance checks for the generated single-pack CAD layout, not dynamics."""
import json
from pathlib import Path
import unittest

import mujoco as mj
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'runs/tower-lift-v8'


class SinglePackChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (RUN / 'cad-fit-checks.json').exists():
            raise unittest.SkipTest('Build, review and audit tower-lift-v8 first')
        cls.m = mj.MjModel.from_xml_path(str(RUN / 'so101/scene.xml'))
        cls.fit = json.loads((RUN / 'cad-fit-checks.json').read_text())

    def test_container_load_bypasses_robot_and_v7_mounts_are_preserved(self):
        m = self.m
        for name in ['pack_clamshell', 'pack_carrier', 'pack_deck']:
            b = m.body(name).id
            ancestors = []
            while b:
                ancestors.append(m.body(b).name)
                b = m.body_parentid[b]
            self.assertIn('lower_lift_carriage', ancestors)
            self.assertFalse(any(n.startswith(('left_', 'right_')) for n in ancestors))
        old = mj.MjModel.from_xml_path(str(ROOT / 'runs/tower-lift-v7/so101/scene.xml'))
        self.assertEqual(m.nq, old.nq)
        self.assertEqual(m.nu, old.nu)
        np.testing.assert_allclose(m.jnt_range, old.jnt_range)
        np.testing.assert_allclose(m.actuator_forcerange, old.actuator_forcerange)
        for side, plate in [('left', 'carriage_faceplate'), ('right', 'lower_carriage_faceplate')]:
            b = m.body(side + '_base').id
            self.assertEqual(m.body_parentid[b], m.body(plate).id)
            np.testing.assert_allclose(m.body_pos[b], old.body(side + '_base').pos)
            np.testing.assert_allclose(m.body_quat[b], old.body(side + '_base').quat)

    def test_review_poses_fit_without_claiming_motion_validation(self):
        self.assertEqual(len(self.fit['poses']), 3)
        for pose in self.fit['poses']:
            with self.subTest(pose=pose['pose']):
                self.assertFalse(pose['rigid_net_fixture_intersections'])
                self.assertFalse(pose['carrier_obstructions'])
                self.assertFalse(pose['robot_fixture_intersections'])
                self.assertGreater(pose['interarm_convex_clearance_mm'], 0)
                self.assertGreater(pose['fixture_left_plane_clearance_mm'], 0)
        reach = json.loads((RUN / 'reach-checks.json').read_text())
        for pose in reach['poses']:
            self.assertLess(pose['position_error_m'], .003)
            if pose['normal_z'] is not None:
                self.assertGreater(pose['normal_z'], .97)
            self.assertFalse(pose['enabled_contact_penetrations_m'])
        replay = json.loads((RUN / 'so101/replay.json').read_text())
        self.assertFalse(replay['training_ready'])
        self.assertEqual(replay['label'], 'static_CAD_fit_review')
        self.assertEqual(len(replay['frames']), 3)


if __name__ == '__main__':
    unittest.main()
