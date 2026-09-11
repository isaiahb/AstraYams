"""Check built direct mounting geometry and the shared front belt constraint."""
import json
import os
from pathlib import Path
import unittest
import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SCENE=ROOT/'runs'/os.environ.get('TOWER_LIFT_RUN','tower-lift-v7')/'so101'

class StackedCarriageChecks(unittest.TestCase):
    def setUp(self):
        if not (SCENE/'scene.xml').exists():
            self.skipTest('Build the selected tower-lift config before artifact checks')
        self.cfg=json.loads((SCENE.parent/'config.json').read_text())
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

    def test_corrected_mount_orientation_and_parked_clearance(self):
        if self.cfg['revision']!='v7-upright-compact-so101':
            self.skipTest('V7 orientation acceptance only')
        m,d=self.m,self.d
        # The complete base is inverted from V6 around its mounting normal:
        # base +X is now down while +Z still points outward from the plate.
        for side in ['left','right']:
            axes=d.xmat[m.body(side+'_base').id].reshape(3,3)
            np.testing.assert_allclose(axes[:,0],[0,0,-1],atol=1e-9)
        upper=d.xpos[m.body('carriage_faceplate').id][2]
        lower=d.xpos[m.body('lower_carriage_faceplate').id][2]
        self.assertAlmostEqual(upper-lower,.2,places=8)
        # Explicit distance queries include visual-only tool solids. They are
        # conservative convex envelopes, not evidence of enabled tool contact.
        geoms={s:[i for i in range(m.ngeom)
                  if (m.body(m.geom_bodyid[i]).name or '').startswith(s+'_')
                  and m.geom_rgba[i,3]>0] for s in ['left','right']}
        jaw=int(m.joint('left_gripper').qposadr[0])
        for degrees in [14,7,0]:
            d.qpos[jaw]=np.deg2rad(degrees);mujoco.mj_forward(m,d)
            distance=min(mujoco.mj_geomDistance(m,d,a,b,.1,None)
                         for a in geoms['left'] for b in geoms['right'])
            self.assertGreater(distance,.03, f'Parked jaw pose {degrees} degrees')
            for contact in d.contact:
                arm=any((m.body(m.geom_bodyid[g]).name or '').startswith(('left_','right_'))
                        for g in [contact.geom1,contact.geom2])
                if arm:self.assertGreaterEqual(contact.dist,-.0001)

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
            gap=self.cfg['frame']['vertical_carriage_spacing_m']
            maximum=max(maximum,abs(upper-lower-gap),abs(upper+rear-start[0]-start[2]))
        delta=d.qpos[ids]-start
        self.assertGreater(delta[0],.02)
        np.testing.assert_allclose(delta,[delta[0],delta[0],-delta[0]],atol=2e-5)
        self.assertLess(maximum,2e-5)
        self.assertEqual(int(mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_ACTUATOR,'lower_lift_motor')),-1)
        self.assertEqual(int(d.warning.number.sum()),0)

if __name__=='__main__':unittest.main()
