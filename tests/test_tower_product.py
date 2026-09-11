"""Geometry and access checks for the product-informed tower reconstruction."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as E
import json
import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parents[1]/'runs/tower-lift-v2'

@unittest.skipUnless((ROOT/'so101/scene.xml').exists(),'Build v2 first')
class TowerProductChecks(unittest.TestCase):
    def test_catalog_envelope_and_connected_cad(self):
        c=json.loads((ROOT/'config.json').read_text())['tower']
        self.assertEqual(c['rows']*c['pockets_per_row'],60)
        self.assertAlmostEqual(c['first_row_base_m']+c['rows']*c['row_pitch_m']+c['top_collar_height_m'],1.84)
        self.assertEqual([c['reservoir_width_m'],c['reservoir_depth_m']],[.4,.4])
        import cadquery as cq
        for name in ['tier_module','net_basket','tank','tank_lid']:
            s=cq.importers.importStep(str(ROOT/'cad'/f'{name}.step'))
            self.assertTrue(s.val().isValid(),name)
            self.assertEqual(len(s.solids().vals()),1,name)
        lid=cq.importers.importStep(str(ROOT/'cad/tank_lid.step')).val().BoundingBox()
        self.assertAlmostEqual(lid.xlen,400,places=3);self.assertAlmostEqual(lid.ylen,400,places=3)
        # Measure actual transformed scene vertices, not just the input config.
        import re
        m=mujoco.MjModel.from_xml_path(str(ROOT/'so101/scene.xml'));d=mujoco.MjData(m);mujoco.mj_forward(m,d)
        points=[]
        for i in range(m.ngeom):
            name=m.body(m.geom_bodyid[i]).name
            if m.geom_rgba[i,3]==0 or m.geom_type[i]!=mujoco.mjtGeom.mjGEOM_MESH:continue
            if not re.match(r'^(tier_|basket_|reservoir|caster_|tower_top_)',name):continue
            mesh=m.geom_dataid[i];a=m.mesh_vertadr[mesh]
            vertices=m.mesh_vert[a:a+m.mesh_vertnum[mesh]]
            points.append(vertices@d.geom_xmat[i].reshape(3,3).T+d.geom_xpos[i])
        points=np.concatenate(points);extent=np.ptp(points,axis=0)
        np.testing.assert_allclose(extent,[.4,.4,1.84],atol=2e-5)

    def test_all_sixty_mouths_open_and_rims_collidable(self):
        # Isolate holder geometry for a discriminating contact probe. No plant or
        # robot can make a sealed holder appear to pass this opening test.
        root=E.parse(ROOT/'so101/scene.xml').getroot();world=root.find('worldbody')
        for child in list(world):
            if child.get('name')!='growing_tower':world.remove(child)
        for parent in list(world.iter()):
            for child in list(parent):
                if child.get('name')=='crown':parent.remove(child)
        for name in ['actuator','equality','contact']:
            el=root.find(name)
            if el is not None:root.remove(el)
        p=E.SubElement(world,'body',name='access_probe')
        E.SubElement(p,'freejoint',name='access_probe_joint')
        E.SubElement(p,'geom',name='access_probe_geom',type='sphere',size='.002',mass='.001',contype='1',conaffinity='4')
        m=mujoco.MjModel.from_xml_string(E.tostring(root,encoding='unicode'));d=mujoco.MjData(m)
        mujoco.mj_forward(m,d);pid=m.geom('access_probe_geom').id
        for row in range(12):
            for site in range(5):
                body=m.body(f'basket_{row}_{site}').id
                origin=d.xpos[body].copy();rot=d.xmat[body].reshape(3,3).copy()
                for local,expect_contact in [([0,0,.009],False),([0,0,-.020],False),([.026,0,.0015],True)]:
                    d.qpos[:3]=origin+rot@local;d.qpos[3:7]=[1,0,0,0]
                    mujoco.mj_forward(m,d)
                    found=any(pid in c.geom and c.dist<0 for c in d.contact)
                    self.assertEqual(found,expect_contact,(row,site,local))

if __name__=='__main__':unittest.main()
