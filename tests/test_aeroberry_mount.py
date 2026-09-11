"""Geometry/frame regressions; these do not establish physical tool fitness."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as E

import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from aeroberry_tool import prepare, R, OFFSET_MM, PIVOT_MM, SO_PIVOT_M
from build_tower_lift import append_robot


class AeroberryMount(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.folder=Path(cls.temp.name)
        cls.report=prepare(cls.folder)
        cls.xml=E.Element('mujoco')
        E.SubElement(cls.xml,'compiler',angle='radian',autolimits='true')
        for tag in ['asset','actuator','equality']:E.SubElement(cls.xml,tag)
        world=E.SubElement(cls.xml,'worldbody');carriage=E.SubElement(world,'body',name='mount')
        cfg=json.loads((ROOT/'configs/tower_lift_v5.json').read_text())
        cfg['end_effector']['generated_dir']=str(cls.folder)
        append_robot(cls.xml,carriage,'so101','left',cfg)
        cls.model=mujoco.MjModel.from_xml_string(E.tostring(cls.xml,encoding='unicode'))

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_source_solid_volumes_survive_import(self):
        volumes={p['name']:p['volume_mm3'] for p in self.report['parts']}
        self.assertEqual(len(volumes),10)
        self.assertAlmostEqual(volumes['P01_FixedJaw'],29541.695364338,places=5)
        self.assertAlmostEqual(volumes['P02_UtilityCarrier'],6929.062852084,places=5)
        self.assertAlmostEqual(volumes['FixedPad'],24,places=6)

    def test_servo_pivot_uses_upstream_datum(self):
        np.testing.assert_allclose((R@PIVOT_MM+OFFSET_MM)*.001,SO_PIVOT_M,atol=1e-12)
        self.assertAlmostEqual(np.linalg.det(R),1)
        # The cutter's positive opening is opposite the stock finger convention.
        np.testing.assert_allclose(R[:,2],[0,1,0])

    def test_opening_moves_carrier_but_not_fixed_jaw(self):
        m=self.model;d=mujoco.MjData(m)
        fixed=m.body('left_aeroberry_P01_FixedJaw').id
        moving=m.body('left_aeroberry_P02_UtilityCarrier').id
        qid=m.joint('left_gripper').qposadr[0]
        mujoco.mj_forward(m,d);fixedpose=d.xmat[fixed].copy();movingpose=d.xmat[moving].copy()
        pivot=d.xpos[m.body('left_aeroberry_hinge').id].copy()
        d.qpos[qid]=np.deg2rad(14);mujoco.mj_forward(m,d)
        np.testing.assert_allclose(d.xmat[fixed],fixedpose,atol=1e-12)
        np.testing.assert_allclose(d.xpos[m.body('left_aeroberry_hinge').id],pivot,atol=1e-12)
        delta=movingpose.reshape(3,3).T@d.xmat[moving].reshape(3,3)
        self.assertAlmostEqual(np.rad2deg(np.arccos((np.trace(delta)-1)/2)),14,places=5)
        self.assertEqual(m.nu,6)

    def test_no_training_readiness_claim_for_rigid_flexure(self):
        self.assertFalse(self.report['training_ready'])
        self.assertIn('tool contact',self.report['phase'])
        self.assertIsNone(self.xml.find(".//body[@name='left_moving_jaw_so101_v1']"))
        fixed=self.xml.find(".//body[@name='left_gripper']")
        self.assertFalse(any(g.get('mesh')=='wrist_roll_follower_so101_v1' for g in fixed.findall('geom')))

if __name__=='__main__':unittest.main()
