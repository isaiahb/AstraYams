"""Discriminating checks for opposed motion and counterweight load transfer."""
from pathlib import Path
import json
import unittest
import xml.etree.ElementTree as E
import mujoco
import numpy as np
from astrafactory.tower_lift import TowerLiftEnv

ROOT=Path(__file__).resolve().parents[1]/'runs/tower-lift-v4'


def rig_model():
    """Keep the exact rig/drive physics, omit the unrelated growing tower."""
    root=E.parse(ROOT/'rig/scene.xml').getroot();world=root.find('worldbody')
    for child in list(world):
        if child.tag=='body' and child.get('name') not in ['lift_frame','lift_carriage','counterweight_carriage']:
            world.remove(child)
    for tag in ['equality','contact']:
        parent=root.find(tag)
        for child in list(parent):
            if not child.get('name','').startswith(('counterweight_belt','belt_pulley_coupling')):parent.remove(child)
    used={g.get('mesh') for g in world.iter('geom') if g.get('mesh')}
    asset=root.find('asset')
    for child in list(asset):
        if child.tag=='mesh' and child.get('name') not in used:asset.remove(child)
    m=mujoco.MjModel.from_xml_string(E.tostring(root,encoding='unicode'));d=mujoco.MjData(m)
    front=int(m.joint('lift_z').qposadr[0]);rear=int(m.joint('counterweight_z').qposadr[0])
    d.qpos[front]=.84;d.qpos[rear]=.84;d.ctrl[0]=.84
    mujoco.mj_forward(m,d)
    return m,d,front,rear


def unpowered_probe(rear_mass, coupled=True):
    m,d,front,rear=rig_model();b=m.body('counterweight_carriage').id
    m.body_inertia[b]*=rear_mass/m.body_mass[b];m.body_mass[b]=rear_mass
    mujoco.mj_setConst(m,d)
    d.qpos[front]=.84;d.qpos[rear]=.84;d.qvel[:]=0
    m.actuator_forcerange[0]=[0,0]
    d.eq_active[m.equality('counterweight_belt').id]=coupled
    # An upward command cannot set either body's pose.
    d.ctrl[0]=1.2
    for _ in range(round(.25/m.opt.timestep)):mujoco.mj_step(m,d)
    return np.array([d.qpos[front]-.84,d.qpos[rear]-.84]),int(d.warning.number.sum())


@unittest.skipUnless((ROOT/'rig/scene.xml').exists(),'Build V4 first')
class CounterweightChecks(unittest.TestCase):
    def test_counterweight_is_passive_and_present_with_both_arm_variants(self):
        for kind,count in [('rig',1),('so101',13),('yam',15)]:
            e=TowerLiftEnv(ROOT/kind);obs,_=e.reset();m=e.model
            self.assertEqual(m.nu,count)
            self.assertTrue(e.observation_space.contains(obs))
            self.assertNotIn(e.counter_joint,m.actuator_trnid[:,0])
            self.assertEqual(m.body('counterweight_carriage').parentid[0],0)
            self.assertNotEqual(m.body('counterweight_disk').parentid[0],m.body('lift_carriage').id)
            self.assertEqual(mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,'payload_shaft'),-1)

    def test_front_and_rear_guide_shapes_can_pass(self):
        import cadquery as cq
        front=cq.importers.importStep(str(ROOT/'cad/guide_block.step'))
        rear=cq.importers.importStep(str(ROOT/'cad/counter_guide_shoe.step'))
        self.assertTrue(front.val().isValid());self.assertTrue(rear.val().isValid())
        for dz in [-.030,-.015,0,.015,.030]:
            overlap=front.intersect(rear.translate((0,0,dz*1000)))
            self.assertLess(sum(s.Volume() for s in overlap.solids().vals()),1e-5)

    def test_mass_imbalance_reverses_unpowered_motion(self):
        light,w1=unpowered_probe(1.4)
        heavy,w2=unpowered_probe(5.6)
        self.assertEqual(w1+w2,0)
        self.assertLess(light[0],-.01);self.assertGreater(light[1],.01)
        self.assertGreater(heavy[0],.01);self.assertLess(heavy[1],-.01)
        self.assertLess(abs(light.sum()),1e-4);self.assertLess(abs(heavy.sum()),1e-4)

    def test_equal_masses_balance_and_broken_coupling_drops_both(self):
        balanced,w1=unpowered_probe(2.8)
        broken,w2=unpowered_probe(2.8,False)
        self.assertEqual(w1+w2,0)
        self.assertLess(abs(balanced).max(),1e-4)
        self.assertTrue(np.all(broken<-.05))

    def test_rear_mass_reduces_motor_holding_force(self):
        forces=[]
        for mass in [.1,2.8]:
            m,d,front,rear=rig_model();b=m.body('counterweight_carriage').id
            m.body_inertia[b]*=mass/m.body_mass[b];m.body_mass[b]=mass;mujoco.mj_setConst(m,d)
            d.qpos[front]=.84;d.qpos[rear]=.84;d.ctrl[0]=.84
            for _ in range(round(.4/m.opt.timestep)):mujoco.mj_step(m,d)
            forces.append(abs(float(d.actuator_force[0])))
        self.assertGreater(forces[0]-forces[1],20.)

    def test_recorded_motion_is_opposed_in_all_models(self):
        for kind in ['rig','so101','yam']:
            r=json.loads((ROOT/kind/'commission/result.json').read_text())
            self.assertFalse(r['invalid']);self.assertEqual(r['simulator_warning_count'],0)
            self.assertLess(r['front_rear_height_correlation'],-.999)
            self.assertLess(r['peak_belt_constraint_error_m'],1e-4)
            self.assertEqual(r['peak_counterweight_contact_N'],0.)
            self.assertGreater(r['counterweight_height_max_m']-r['counterweight_height_min_m'],.10)
            self.assertTrue(np.all(np.array(r['peak_actuator_force_N_or_Nm'])<=np.abs(r['actuator_force_limits']).max(axis=1)+1e-8))
            m=mujoco.MjModel.from_xml_path(str(ROOT/kind/'scene.xml'))
            q=np.load(ROOT/kind/'commission/rollout.npz')['qpos']
            front=q[:,int(m.joint('lift_z').qposadr[0])]
            for pulley in ['belt_pulley_0','belt_pulley_1']:
                angle=q[:,int(m.joint(pulley).qposadr[0])]
                self.assertLess(np.abs(angle-(front-.84)/.020).max(),1e-3)


if __name__=='__main__':unittest.main()
