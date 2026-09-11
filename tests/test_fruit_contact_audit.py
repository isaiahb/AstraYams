"""Physical measurement checks on known-mass fixtures, not fruit-damage validation."""
import unittest
import mujoco
import numpy as np
from astrafactory.fruit_contact_audit import FruitContactAudit


class ContactAuditTests(unittest.TestCase):
    def test_fruit_to_fruit_load_is_assigned_to_both(self):
        m = mujoco.MjModel.from_xml_string('''<mujoco><option gravity="0 0 0"/>
        <worldbody><body name="fruit_a" pos="-.019 0 0"><freejoint/>
        <geom name="berry_a" type="sphere" size=".02" mass=".02"/></body>
        <body name="fruit_b" pos=".019 0 0"><freejoint/>
        <geom name="berry_b" type="sphere" size=".02" mass=".02"/></body>
        </worldbody></mujoco>''')
        d = mujoco.MjData(m); mujoco.mj_step(m, d)
        audit = FruitContactAudit(m); audit.sample(d, float(d.time), m.opt.timestep)
        pairs = audit.report()['pairs']
        self.assertEqual({p['fruit'] for p in pairs}, {'fruit_a', 'fruit_b'})
        self.assertGreater(pairs[0]['normal_impulse_Ns'], 0.)
        self.assertEqual(pairs[0]['normal_impulse_Ns'], pairs[1]['normal_impulse_Ns'])

    def test_opposing_compression_does_not_cancel(self):
        m = mujoco.MjModel.from_xml_string('''<mujoco><option gravity="0 0 0"/>
        <worldbody><geom name="left_probe" type="sphere" pos="-.035 0 0" size=".02"/>
        <geom name="right_probe" type="sphere" pos=".035 0 0" size=".02"/>
        <body name="fruit_test"><freejoint/>
        <geom name="berry_test" type="sphere" size=".02" mass=".02"/></body>
        </worldbody></mujoco>''')
        d = mujoco.MjData(m); mujoco.mj_step(m, d)
        audit = FruitContactAudit(m); audit.sample(d, float(d.time), m.opt.timestep)
        self.assertEqual(len(audit.report()['pairs']), 2)
        self.assertGreater(sum(p['normal_impulse_Ns'] for p in audit.report()['pairs']), 0.)
        self.assertLess(float(np.linalg.norm(d.qvel)), 1e-8)

    def test_flexible_strand_contact_is_attributed(self):
        m = mujoco.MjModel.from_xml_string('''<mujoco><option timestep=".0002"/>
        <worldbody><flexcomp name="strand" type="grid" count="3 1 1"
          spacing=".03 .03 .03" dim="1" radius=".002" mass=".001">
          <pin id="0 2"/><edge stiffness="100" damping=".02"/></flexcomp>
        <body name="fruit_test" pos="0 0 .023"><freejoint/>
        <geom name="berry_test" type="sphere" size=".02" mass=".02"/>
        </body></worldbody></mujoco>''')
        d = mujoco.MjData(m); audit = FruitContactAudit(m)
        for _ in range(500):
            mujoco.mj_step(m, d); audit.sample(d, float(d.time), m.opt.timestep)
        pairs = audit.report()['pairs']
        self.assertTrue(any(p['counterpart'] == 'flex:strand' and p['normal_impulse_Ns'] > 0 for p in pairs))

    def test_static_weight_and_flesh_classification(self):
        m = mujoco.MjModel.from_xml_string('''<mujoco><option timestep=".0005"/>
        <worldbody><geom name="plate" type="plane" size="1 1 .1"/>
        <body name="fruit_test" pos="0 0 .02"><freejoint/>
        <geom name="berry_test" type="sphere" size=".02" mass=".02"/>
        </body></worldbody></mujoco>''')
        d = mujoco.MjData(m)
        for _ in range(2000): mujoco.mj_step(m, d)
        audit = FruitContactAudit(m)
        for _ in range(200):
            mujoco.mj_step(m, d); audit.sample(d, float(d.time), m.opt.timestep)
        pair = audit.report()['pairs'][0]
        self.assertEqual(pair['surface'], 'flesh')
        self.assertEqual(pair['counterpart'], 'plate')
        self.assertAlmostEqual(pair['normal_impulse_Ns'], .02 * 9.81 * .1, delta=.0002)
        self.assertIsNone(audit.report()['damage_probability'])
        self.assertIsNone(audit.report()['contact_pressure_Pa'])

    def test_observer_does_not_modify_state_or_count_free_flight(self):
        m = mujoco.MjModel.from_xml_string('''<mujoco><worldbody>
        <body name="fruit_test" pos="0 0 1"><freejoint/>
        <geom name="berry_test" type="sphere" size=".02" mass=".02"/>
        </body></worldbody></mujoco>''')
        d = mujoco.MjData(m); mujoco.mj_step(m, d)
        before = (d.qpos.copy(), d.qvel.copy(), d.qacc.copy(), d.ctrl.copy())
        audit = FruitContactAudit(m); audit.sample(d, float(d.time), m.opt.timestep)
        for a, b in zip(before, [d.qpos, d.qvel, d.qacc, d.ctrl]):
            np.testing.assert_array_equal(a, b)
        self.assertEqual(audit.report()['pairs'], [])
        with self.assertRaises(ValueError): audit.sample(d, float(d.time), m.opt.timestep)


if __name__ == '__main__': unittest.main()
