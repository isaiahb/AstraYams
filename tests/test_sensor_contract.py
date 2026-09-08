import numpy as np
import unittest
from astrafactory.sensor_contract import JointTargetCodec, simulation_feedback, SIM_FINGER_STROKE_M


class SensorContractTests(unittest.TestCase):
    def test_sim_gripper_units_and_command_direction_agree(self):
        q=np.zeros(7); q[6]=-SIM_FINGER_STROKE_M
        v=np.zeros(7); v[6]=-SIM_FINGER_STROKE_M/2
        obs=simulation_feedback(q,v,q,np.zeros(7))
        assert obs.shape==(28,)
        self.assertAlmostEqual(obs[6],1)
        self.assertAlmostEqual(obs[13],.5)
        self.assertAlmostEqual(obs[20],1)
        codec=JointTargetCodec(obs[14:21],np.tile([-2,2],(6,1)))
        action=np.zeros(7);action[6]=1
        target=codec.update(action)
        expected_sim=q[6]+.0006
        self.assertAlmostEqual(float(target[6]),-expected_sim/SIM_FINGER_STROKE_M,places=6)
    
    
    def test_commands_bounded_and_bad_feedback_rejected(self):
        codec=JointTargetCodec(np.ones(7),np.tile([-1,1],(6,1)))
        result=codec.update(np.full(7,100))
        assert np.all(result[:6]==1)
        result[:]=99
        assert np.all(codec.target<=1)
        with self.assertRaises(ValueError):codec.update(np.full(7,np.nan))
        with self.assertRaises(ValueError):simulation_feedback(np.zeros(6),np.zeros(7),np.zeros(7),np.zeros(7))
