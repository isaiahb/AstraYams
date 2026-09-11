"""Import the user's AEROBERRY prototype as articulated CAD, without redrawing it.

This is a fit-review asset. The flexure is a rigid rest-shape and tool contact
is deliberately NOT commissioned. Do not use this model for harvesting RL.
"""
import hashlib
import json
import zipfile
from pathlib import Path
import xml.etree.ElementTree as E

import cadquery as cq
import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/end-effectors/aeroberry-so101-v04'
# Package +X goes toward the stem, +Z is the cutter hinge axis. Map these
# onto the upstream SO-101 wrist using its actual servo-axis datum.
R = np.array([[0., -1., 0.], [0., 0., 1.], [-1., 0., 0.]])
PIVOT_MM = np.array([0., 9., 0.])
SO_PIVOT_M = np.array([.0202, .0188, -.0234])
OFFSET_MM = SO_PIVOT_M * 1000 - R @ PIVOT_MM
FIXED = {'P01_FixedJaw', 'FixedPad'}
PARTS = ['P01_FixedJaw', 'P02_UtilityCarrier', 'P03_Flexure_1p2',
         'P04_BladeCover', 'P05_RearBrace', 'UtilityBlade', 'FixedPad',
         'MovingPad', 'ClampScrew1', 'ClampScrew2']


def prepare(out):
    """Extract embedded BREP, remove its saved opening pose, export true solids."""
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    native = SOURCE / 'AEROBERRY-SO101-GripCut-v0.4.FCStd'
    report = dict(source=str(native.relative_to(ROOT)),
                  source_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),
                  phase='CAD fit review only; tool contact and flexure dynamics not commissioned',
                  training_ready=False, pivot_cad_mm=PIVOT_MM.tolist(),
                  pivot_so101_m=SO_PIVOT_M.tolist(),
                  rotation_cad_to_so101=R.tolist(), offset_mm=OFFSET_MM.tolist(),
                  opening_deg=[0, 14], parts=[])
    with zipfile.ZipFile(native) as archive:
        for name in PARTS:
            brep=out/(name+'.brep')
            brep.write_bytes(archive.read(name+'.Shape.brp'))
            shape=cq.Shape.importBrep(str(brep))
            # FreeCAD's serialized BREP already has its Placement. Removing
            # the TopLoc pose once (not twice) returns closed assembly geometry.
            closed=shape.located(cq.Location())
            assert closed.isValid() and len(closed.Solids()) == 1, name
            cq.exporters.export(closed,str(out/(name+'.step')))
            if name in FIXED:
                rv=Rotation.from_matrix(R).as_rotvec();a=np.linalg.norm(rv)
                local=closed.rotate((0,0,0),tuple(rv/a),np.rad2deg(a)).translate(tuple(OFFSET_MM))
            else:
                local=closed.translate(tuple(-PIVOT_MM))
            cq.exporters.export(local,str(out/(name+'.stl')),tolerance=.08,angularTolerance=.12)
            brep.unlink()
            b=closed.BoundingBox()
            report['parts'].append(dict(name=name,body='fixed' if name in FIXED else 'moving',
                                        valid=True,volume_mm3=closed.Volume(),
                                        closed_bounds_mm=[b.xmin,b.ymin,b.zmin,b.xmax,b.ymax,b.zmax]))
    (out/'import.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def mount(root, robot, side, folder):
    """Replace the stock jaw housing and horn-driven finger at source datums.

    All tool meshes are visible-only until a compliant contact model is built.
    Keep the original servo, arm joints, and their finite-force actuators.
    """
    def add(parent, tag, **kw):
        return E.SubElement(parent, tag, {k:str(v) for k,v in kw.items()})
    def vec(a):return ' '.join(f'{x:.10g}' for x in np.asarray(a).ravel())
    assets=root.find('asset'); prefix=side+'_'
    wrist=robot.find(f".//body[@name='{prefix}gripper']")
    jaw=wrist.find(f"body[@name='{prefix}moving_jaw_so101_v1']")
    wrist.remove(jaw)
    for g in list(wrist.findall('geom')):
        if g.get('mesh')=='wrist_roll_follower_so101_v1':wrist.remove(g)
    # The source gripper link combined servo + old housing; use an explicit
    # 55 g servo prior and add each CAD part's volume-based inertia separately.
    inertial=wrist.find('inertial');inertial.attrib.clear()
    inertial.attrib.update(pos='.0077 .0001 -.0234',mass='.055',diaginertia='0.000010 0.000014 0.000017')
    q=Rotation.from_matrix(R).as_quat()
    moving=add(wrist,'body',name=prefix+'aeroberry_hinge',pos=vec(SO_PIVOT_M),quat=vec(q[[3,0,1,2]]))
    add(moving,'joint',name=prefix+'gripper',axis='0 0 1',type='hinge',range='0 .2443460953',**{'class':'sts3215'})
    add(moving,'inertial',pos='0 0 0',mass='.0001',diaginertia='1e-8 1e-8 1e-8')
    report=json.loads((folder/'import.json').read_text())
    for part in report['parts']:
        name=part['name'];mesh='aeroberry_'+name
        if assets.find(f"mesh[@name='{mesh}']") is None:
            add(assets,'mesh',name=mesh,file=str((folder/(name+'.stl')).resolve()),scale='.001 .001 .001')
        parent=wrist if name in FIXED else moving
        body=add(parent,'body',name=prefix+mesh)
        color='.83 .87 .84 1'
        if name in ['P02_UtilityCarrier','P05_RearBrace']:color='.12 .43 .39 1'
        if 'Pad' in name or 'Flexure' in name:color='.84 .55 .20 1'
        if 'Blade' in name and name=='UtilityBlade' or 'Screw' in name:color='.55 .61 .64 1'
        density=7800 if name=='UtilityBlade' or 'Screw' in name else 1100
        # Solid inertia from the actual tessellated surface, not its convex hull.
        import trimesh
        meshdata=trimesh.load(folder/(name+'.stl'));meshdata.apply_scale(.001)
        meshdata.density=density;mass=part['volume_mm3']*1e-9*density
        inertia=meshdata.moment_inertia
        inertia*=mass/meshdata.mass
        add(body,'inertial',mass=mass,pos=vec(meshdata.center_mass),
            fullinertia=vec([inertia[0,0],inertia[1,1],inertia[2,2],inertia[0,1],inertia[0,2],inertia[1,2]]))
        add(body,'geom',name=prefix+mesh+'_visual',type='mesh',mesh=mesh,rgba=color,
            contype='0',conaffinity='0',mass='0')
    site=wrist.find(f"site[@name='{prefix}gripperframe']")
    site.set('pos',vec((R @ np.array([40.,.8,3.4])+OFFSET_MM)*.001))
    for actuator in root.findall('actuator/position'):
        if actuator.get('joint')==prefix+'gripper':actuator.set('ctrlrange','0 .2443460953')
