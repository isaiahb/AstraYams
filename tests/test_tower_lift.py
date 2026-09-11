"""Commissioning checks on generated tower scenes; no harvest success implied."""
from pathlib import Path
import unittest
import numpy as np
from astrafactory.tower_lift import TowerLiftEnv

ROOT=Path(__file__).resolve().parents[1]/'runs/tower-lift-v1'


@unittest.skipUnless((ROOT/'so101/initial.npz').exists(),'Generate tower lift first')
class TowerLiftChecks(unittest.TestCase):
    def test_embodiments_have_distinct_action_spaces_and_preserve_plant(self):
        for kind,count in [('so101',13),('yam',15)]:
            e=TowerLiftEnv(ROOT/kind);obs,_=e.reset()
            self.assertEqual(e.model.nu,count)
            self.assertTrue(e.observation_space.contains(obs))
            self.assertGreater(e.model.njnt,100)
            self.assertTrue(np.all(e.model.actuator_forcelimited))
            self.assertTrue(np.all(np.isfinite(e.model.actuator_forcerange)))
            with self.assertRaises(ValueError):e.step(np.full(count,np.nan))

    def test_no_teleport_when_lift_force_is_zero(self):
        e=TowerLiftEnv(ROOT/'so101');e.reset()
        before=float(e.data.qpos[e.qids[e.lift]])
        e.model.actuator_forcerange[e.lift]=[0,0]
        action=np.zeros(e.model.nu);action[e.lift]=1
        for _ in range(5):_,_,term,_,info=e.step(action)
        self.assertFalse(term)
        self.assertGreater(e.target[e.lift],before)
        self.assertLess(info['lift_height_m'],before-.005)
        self.assertEqual(info['lift_force_N'],0.)

    def test_recorded_lift_motion_has_finite_forces_and_no_robot_contact(self):
        import json
        for kind in ['so101','yam']:
            result=json.loads((ROOT/kind/'commission/result.json').read_text())
            self.assertFalse(result['invalid'])
            self.assertEqual(result['simulator_warning_count'],0)
            self.assertEqual(result['peak_robot_contact_N'],0.)
            self.assertGreater(result['lift_height_max_m']-result['lift_height_min_m'],.10)
            peaks=np.array(result['peak_actuator_force_N_or_Nm'])
            bounds=np.abs(result['actuator_force_limits']).max(axis=1)
            self.assertTrue(np.all(peaks<=bounds+1e-8))
            self.assertIsNone(result['harvest_success'])


if __name__=='__main__':unittest.main()
