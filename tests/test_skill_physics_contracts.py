"""Regression checks for training guidance and reset-only randomization."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.skill_randomization import SkillRandomization
from astrafactory.contact_downstream_skills_v3 import expert_label

class Contracts(unittest.TestCase):
    def test_velocity_and_load_are_not_angular_error(self):
        x=np.zeros(15);x[2]=-1.;x[6:]=2.
        env=SimpleNamespace(task=SimpleNamespace(force=4.))
        with patch('astrafactory.contact_downstream_skills_v3.observe',return_value=x):
            self.assertEqual(expert_label(env)[2],-1.)
            x[3]=.09
            self.assertEqual(expert_label(env)[2],0.)
            env.task.force=33.
            self.assertEqual(expert_label(env)[2],.4)

    def test_nominal_identity_and_seeded_mass_friction(self):
        a=CurriculumEnv('tasks/yam_contact_curriculum');b=CurriculumEnv('tasks/yam_contact_curriculum')
        try:
            x,_=a.reset(seed=2100)
            y,_=SkillRandomization(b,'nominal','nominal').reset(seed=2100)
            np.testing.assert_allclose(x,y,atol=1e-10,rtol=0)
            dr=SkillRandomization(b)
            y,i=dr.reset(seed=100);z,j=dr.reset(seed=100)
            np.testing.assert_array_equal(y,z);self.assertEqual(i,j)
            mass=b.model.body_mass[b.task.peg_body]
            self.assertGreaterEqual(mass,.036);self.assertLessEqual(mass,.044)
            self.assertEqual(b.specification['abort_contact_force_n'],80)
            with self.assertRaises(ValueError):SkillRandomization(a,'stress-v1','training')
        finally:a.close();b.close()

if __name__=='__main__':unittest.main()
