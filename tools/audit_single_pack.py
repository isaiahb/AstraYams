"""Static geometry audit; does not infer contact forces or fruit safety."""
from pathlib import Path
import json
import numpy as np
import mujoco as mj
import cadquery as cq
import trimesh
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[1];P=ROOT/'runs/tower-lift-v8'

def transformed(shape,d,i):
    rv=Rotation.from_matrix(d.xmat[i].reshape(3,3)).as_rotvec();a=np.linalg.norm(rv)
    if a>1e-9:shape=shape.rotate((0,0,0),tuple(rv/a),np.rad2deg(a))
    return shape.translate(tuple(d.xpos[i]*1000))

def overlap(a,b):
    aa=a.BoundingBox();bb=b.BoundingBox()
    if any(getattr(aa,k+'max')<=getattr(bb,k+'min')+1e-6 or getattr(bb,k+'max')<=getattr(aa,k+'min')+1e-6 for k in 'xyz'):return 0.
    return float(a.intersect(b).Volume())

def convex_geom(m,d,g):
    """Conservative robot envelope; keep the fixture's hollow STEP geometry."""
    k=m.geom_dataid[g]
    vertices=m.mesh_vert[m.mesh_vertadr[k]:m.mesh_vertadr[k]+m.mesh_vertnum[k]]
    vertices=(vertices@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g])*1000
    hull=trimesh.convex.convex_hull(vertices)
    faces=[cq.Face.makeFromWires(cq.Wire.makePolygon([cq.Vector(*v) for v in hull.vertices[f]],close=True)) for f in hull.faces]
    return cq.Solid.makeSolid(cq.Shell.makeShell(faces))

def main():
    m=mj.MjModel.from_xml_path(str(P/'so101/scene.xml'));d=mj.MjData(m)
    build=json.loads((P/'so101/build.json').read_text());instances=dict(build['instances'])
    shapes={part:cq.importers.importStep(str(P/'cad'/(part+'.step'))).val() for part in set(instances.values())}
    trajectories=np.load(P/'so101/layout/rollout.npz')['qpos'][::2]
    reports=[]
    for label,q in zip(['catch approach','container access','parked'],trajectories):
        d.qpos[:]=q;mj.mj_forward(m,d)
        world={name:transformed(shapes[part],d,m.body(name).id) for name,part in instances.items()}
        net=[n for n in instances if n.startswith('right_pack_net') and 'textile' not in n]
        fixtures=[n for n in instances if n.startswith('pack_') and 'bolt' not in n and 'washer' not in n]
        intrusions=[]
        for a in net:
            for b in fixtures:
                volume=overlap(world[a],world[b])
                if volume>.01:intrusions.append(dict(a=a,b=b,volume_mm3=volume))
        carrier=[]
        for n in ['pack_guide_0','pack_guide_1','pack_rear_stop','pack_latch','pack_web_0','pack_web_1']:
            volume=overlap(world['pack_carrier'],world[n])
            if volume>.01:carrier.append(dict(other=n,volume_mm3=volume))
        # A single convex clamshell would falsely fill its cavity. Test robot
        # envelopes against the actual hollow STEP after broad-phase rejection.
        robot_intrusions=[]
        for g in range(m.ngeom):
            name=m.body(m.geom_bodyid[g]).name or ''
            if not name.startswith(('left_','right_')) or name.endswith('base') or name.startswith('right_pack') or m.geom_rgba[g,3]<=0:continue
            shape=None
            for n in fixtures:
                other=next(i for i in range(m.ngeom) if m.geom_bodyid[i]==m.body(n).id)
                if mj.mj_geomDistance(m,d,g,other,.001,None)>=0:continue
                if shape is None:shape=convex_geom(m,d,g)
                volume=overlap(shape,world[n])
                if volume>.01:robot_intrusions.append(dict(robot_geom=m.geom(g).name,fixture=n,volume_mm3=volume))
        arms={s:[g for g in range(m.ngeom) if (m.body(m.geom_bodyid[g]).name or '').startswith(s+'_') and m.geom_rgba[g,3]>0] for s in ['left','right']}
        arm_clearance=min(mj.mj_geomDistance(m,d,a,b,.2,None) for a in arms['left'] for b in arms['right'])
        # Frame side members lie at X=+/-300 mm with a 20 mm profile. All
        # fixture CAD stays inside the left member's inner plane, for any Z.
        minx=min(world[n].BoundingBox().xmin for n in fixtures)
        reports.append(dict(pose=label,rigid_net_fixture_intersections=intrusions,carrier_obstructions=carrier,robot_fixture_intersections=robot_intrusions,interarm_convex_clearance_mm=arm_clearance*1000,fixture_left_plane_clearance_mm=minx+290))
    result=dict(scope='Exact STEP-solid static intersections for new fixture/rigid net; not contact dynamics, swept paths, deformation, fastener strength or bruise validation',poses=reports)
    (P/'cad-fit-checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
