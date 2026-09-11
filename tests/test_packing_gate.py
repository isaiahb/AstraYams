"""Mechanical commissioning invariants; not a full packing acceptance test."""
from pathlib import Path
import json
import unittest
import mujoco as mj
import numpy as np
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'runs/tower-lift-v9';B=RUN/'gate-bench'
class PackingGateChecks(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not (B/'scene.xml').exists():raise unittest.SkipTest('Generate packing gate bench first')
  cls.m=mj.MjModel.from_xml_path(str(B/'scene.xml'))
 def test_tool_can_slip_and_floor_is_passive(self):
  m=self.m;j=m.joint('right_net_free').id;self.assertEqual(m.jnt_type[j],mj.mjtJoint.mjJNT_FREE)
  gate=m.joint('right_gate_hinge').id
  self.assertFalse(np.any(m.actuator_trnid[:,0]==gate));self.assertGreater(m.jnt_stiffness[gate],0)
  self.assertEqual(m.neq,0);self.assertTrue(np.all(np.isfinite(m.actuator_forcerange)))
  self.assertGreater(m.nflex,0);self.assertGreater(m.flex_edgestiffness[0],0)
 def test_container_mass_is_carried_by_lift(self):
  m=self.m;b=m.body('pack_clamshell').id;parents=[]
  while b:parents.append(m.body(b).name);b=m.body_parentid[b]
  self.assertIn('lower_lift_carriage',parents);self.assertFalse(any(n.startswith(('left_','right_')) for n in parents))
 def test_sampled_gate_sweep_has_no_rigid_overlap(self):
  data=json.loads((RUN/'cad/gate-sweep-checks.json').read_text())
  self.assertEqual(len(data['records']),32)
  self.assertTrue(all(r['intersection_mm3']<.01 for r in data['records']))
 def test_ground_contact_admits_new_mobile_objects(self):
  m=self.m;floor=m.geom('floor').id
  for name in ['packing_berry_contact','right_pack_net_frame_visual_piece_0','gate_ring_contact_0']:
   g=m.geom(name).id
   self.assertTrue((m.geom_contype[g]&m.geom_conaffinity[floor]) or (m.geom_contype[floor]&m.geom_conaffinity[g]))
  r=json.loads((B/'ground-contact-check/result.json').read_text())
  self.assertGreater(r['final']['berry_com'][2],0)
  self.assertLess(r['final']['berry_com'][2],.035)
  self.assertGreater(r['final']['forces_N']['berry'],.1)
 def test_loaded_net_holds_in_stationary_contact_test(self):
  r=json.loads((B/'hold-gate-v2/result.json').read_text())
  self.assertEqual(r['warnings'],0);self.assertLess(r['maximum_grip_translation_error_mm'],.5)
  self.assertLess(r['maximum_grip_rotation_error_deg'],1)
  local=np.array(r['final']['berry_in_net_frame']);self.assertLess(np.linalg.norm(local[:2]),.035)
  self.assertGreater(local[2],-.04);self.assertGreater(r['final']['forces_N']['berry'],.1)
if __name__=='__main__':unittest.main()
