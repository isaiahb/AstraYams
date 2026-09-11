"""Check built direct mounting geometry and the shared front belt constraint."""
import json
from pathlib import Path
import unittest
import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SCENE=ROOT/'runs/tower-lift-v6/so101'

class StackedCarriageChecks(unittest.TestCase):
    def setUp(self):
        if not (SCENE/'scene.xml').exists():
            self.skipTest('Build configs/tower_lift_v6.json before artifact checks')
        self.m=mujoco.MjModel.from_xml_path(str(SCENE/'scene.xml'))
        self.d=mujoco.MjData(self.m)
        initial=np.load(SCENE/'initial.npz')
        self.d.qpos[:]=initial['qpos'];self.d.ctrl[:]=initial['ctrl']
        mujoco.mj_forward(self.m,self.d)

    def test_actual_stock_base_soles_touch_vertical_plates(self):
        m,d=self.m,self.d
        for side,plate in [('left','carriage_faceplate'),('right','lower_carriage_faceplate')]:
            base=m.body(side+'_base').id;mount=m.body(plate).id
            self.assertEqual(m.body_parentid[base],mount)
            np.testing.assert_allclose(d.xmat[base].reshape(3,3)[:,2],[0,1,0],atol=1e-9)
            k=m.mesh('base_so101_v2').id
            geom=next(i for i in range(m.ngeom) if m.geom_bodyid[i]==base and m.geom_dataid[i]==k and m.geom_contype[i]==0)
            adr=m.mesh_vertadr[k]
            vertices=m.mesh_vert[adr:adr+m.mesh_vertnum[k]]@d.geom_xmat[geom].reshape(3,3).T+d.geom_xpos[geom]
            face=d.xpos[mount][1]+.003
            self.assertAlmostEqual(vertices[:,1].min(),face,places=7)
            sole=vertices[vertices[:,1]<face+.00015]
            self.assertLess(np.max(np.abs(sole[:,0]-d.xpos[mount][0])),.245/2)
            self.assertLess(np.max(np.abs(sole[:,2]-d.xpos[mount][2])),.115/2)

    def test_no_platform_or_adapter_geometry(self):
        parts=json.loads((SCENE.parent/'cad/parts.json').read_text())
        forbidden={'arm_bridge','bridge_bracket','bridge_web','adapter','shelf'}
        self.assertFalse(forbidden & {p['name'] for p in parts})
        names=[self.m.body(i).name or '' for i in range(self.m.nbody)]
        self.assertFalse(any('proposed_' in n or 'shelf' in n or 'adapter' in n for n in names))
        self.assertEqual(sum('carriage_faceplate' in n for n in names),2)
        self.assertEqual(sum('carriage_belt_clamp' in n for n in names),2)

    def test_lower_slider_follows_front_and_opposes_rear(self):
        m,d=self.m,self.d
        ids=[int(m.joint(n).qposadr[0]) for n in ['lift_z','lower_lift_z','counterweight_z']]
        actuator=m.actuator('lift_motor').id;start=d.qpos[ids].copy()
        self.assertFalse(any(m.actuator_trnid[i,0]==m.joint('lower_lift_z').id for i in range(m.nu)))
        maximum=0.
        for _ in range(round(.7/m.opt.timestep)):
            d.ctrl[actuator]=start[0]+.08*min(d.time,.5)
            mujoco.mj_step(m,d)
            upper,lower,rear=d.qpos[ids]
            maximum=max(maximum,abs(upper-lower-.30),abs(upper+rear-start[0]-start[2]))
        delta=d.qpos[ids]-start
        self.assertGreater(delta[0],.02)
        np.testing.assert_allclose(delta,[delta[0],delta[0],-delta[0]],atol=2e-5)
        self.assertLess(maximum,2e-5)
        self.assertEqual(int(mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_ACTUATOR,'lower_lift_motor')),-1)
        self.assertEqual(int(d.warning.number.sum()),0)

if __name__=='__main__':unittest.main()
