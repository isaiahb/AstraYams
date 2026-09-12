"""A measured-outline, uncalibrated hemp leaf contact diagnostic. No robot policy.

Run with the project's existing simulation Python. Geometry data attribution is
in ../reference-data/provenance.json. No author source code is reused.
"""
from pathlib import Path
import argparse
import json
import hashlib
import xml.etree.ElementTree as ET
import numpy as np
import mujoco
from scipy.spatial import Delaunay
from matplotlib.path import Path as Outline

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[1]
OUT = ROOT / 'runs/hemp-leaf-contact-v1'


def vec(x):
    return ' '.join(f'{v:.9g}' for v in np.ravel(x))


def add(p, tag, **kw):
    return ET.SubElement(p, tag, {k: str(v) for k, v in kw.items()})


def simplify(points, eps):
    if len(points) < 3:
        return points
    axis = points[-1] - points[0]
    if np.linalg.norm(axis) < 1e-12:
        dist = np.linalg.norm(points - points[0], axis=1)
    else:
        delta=points-points[0]
        dist = np.abs(axis[0]*delta[:,1]-axis[1]*delta[:,0]) / np.linalg.norm(axis)
    k = int(np.argmax(dist))
    if dist[k] <= eps:
        return points[[0, -1]]
    return np.vstack([simplify(points[:k+1], eps)[:-1], simplify(points[k:], eps)])


def geometry():
    ref = BASE / 'reference-data'
    raw = np.loadtxt(ref / 'out_FUT75_2_12_4a_7.txt')
    landmarks = np.loadtxt(ref / 'land_FUT75_2_12_4a_7.txt')
    axis = landmarks[17] - landmarks[-1]  # Seven-leaflet sample, central tip.
    length = np.linalg.norm(axis)
    axis /= length
    transform = np.array([axis, [-axis[1], axis[0]]]).T * .11 / length
    raw = (raw - landmarks[-1]) @ transform
    path = Outline(raw, closed=True)
    half = len(raw)//2
    boundary = np.vstack([simplify(raw[:half+1], .0003)[:-1],
                          simplify(np.vstack([raw[half:], raw[:1]]), .0003)[:-1]])
    x, y = np.meshgrid(np.arange(raw[:,0].min(), raw[:,0].max(), .006),
                       np.arange(raw[:,1].min(), raw[:,1].max(), .006))
    grid = np.column_stack([x.ravel(), y.ravel()])
    points = np.vstack([boundary, grid[path.contains_points(grid)]])
    points = np.unique(np.round(points, 8), axis=0)
    faces = Delaunay(points).simplices
    tri = points[faces]
    inside = path.contains_points(tri.mean(1), radius=.00015)
    for a, b in [(0,1), (1,2), (2,0)]:
        for t in [.25, .5, .75]:
            inside &= path.contains_points(tri[:,a]*(1-t)+tri[:,b]*t, radius=.0003)
    faces = faces[inside]
    # Keep the connected component containing the attachment. Isolated triangles
    # would otherwise be free particles; any lost area is explicitly reported.
    root = int(np.argmin(np.linalg.norm(points, axis=1)))
    connected = {root}
    while True:
        expanded = connected | set(faces[np.any(np.isin(faces,list(connected)),axis=1)].ravel())
        if expanded == connected:
            break
        connected = expanded
    faces = faces[np.all(np.isin(faces,list(connected)),axis=1)]
    used = np.unique(faces)
    remap = np.full(len(points), -1)
    remap[used] = np.arange(len(used))
    points, faces = points[used], remap[faces]
    a=points[faces[:,1]]-points[faces[:,0]];b=points[faces[:,2]]-points[faces[:,0]]
    area = np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0]).sum()/2
    raw_area = abs(np.dot(raw[:,0],np.roll(raw[:,1],1))-
                   np.dot(raw[:,1],np.roll(raw[:,0],1)))/2
    pin = np.flatnonzero(np.linalg.norm(points,axis=1)<.008)
    assert len(pin) >= 3 and len(faces)>0
    assert abs(area/raw_area-1)<.08, f'Silhouette area mismatch exceeds diagnostic limit: {area/raw_area-1:.3f}; vertices={len(points)}; root={root}'
    return raw, np.column_stack([points,np.zeros(len(points))]), faces, pin, {
        'vertices':len(points),'triangles':len(faces),'pin_vertices':len(pin),
        'reference_area_m2_at_assumed_scale':raw_area,'mesh_area_m2':area,
        'relative_area_difference':float(area/raw_area-1),
        'central_leaflet_length_m':.11,'scale_status':'assumed; not established from source scan',
        'shape_status':'measured 2D outline; simplified triangulation, assumed initially planar pose'}


def build(dt, points, faces, pin, geom_report):
    r=ET.Element('mujoco',model='hemp_leaf_contact_diagnostic')
    add(r,'compiler',angle='radian',autolimits='true')
    add(r,'option',timestep=dt,integrator='implicitfast',iterations=100,cone='elliptic')
    visual=add(r,'visual');add(visual,'global',offwidth=960,offheight=720)
    add(visual,'headlight',ambient='.45 .45 .45',diffuse='.7 .7 .7',specular='.03 .03 .03')
    defaults=add(r,'default')
    add(defaults,'geom',condim=3,friction='.35 .003 .001',solref='.004 1')
    w=add(r,'worldbody');act=add(r,'actuator')
    add(w,'light',pos='0 -.2 .6',dir='0 .2 -1')
    add(w,'geom',name='floor',type='plane',size='.35 .35 .01',rgba='.88 .90 .84 1')
    add(w,'geom',name='bench_support',type='box',pos='-.013 0 .095',size='.012 .016 .095',rgba='.31 .39 .36 1')
    parent=add(w,'body',name='node',pos='0 0 .20')
    add(parent,'geom',name='fixed_stem_section',type='capsule',fromto='0 0 -.04 0 0 .04',size='.003',rgba='.27 .38 .13 1')
    contacts=add(r,'contact');add(contacts,'exclude',body1='node',body2='petiole_0')
    for i in range(5):
        parent=add(parent,'body',name=f'petiole_{i}',pos='0 0 0' if i==0 else '.01 0 0')
        rad=.0016-(i+.5)*.00012
        bend=25e6*np.pi*rad**4/4/.01
        twist=25e6/(2*1.3)*np.pi*rad**4/2/.01
        for axis,k in zip(np.eye(3),[twist,bend,bend]):
            add(parent,'joint',type='hinge',axis=vec(axis),stiffness=k,damping=k*.06,armature=1e-8)
        # The distal segment is the bonded leaf attachment. Exclude its contact
        # with this leaf only; the external probe still collides with it.
        add(parent,'geom',name=f'petiole_surface_{i}',type='capsule',fromto='0 0 0 .01 0 0',size=rad,density=850,rgba='.29 .43 .12 1',contype=4 if i==4 else 1,conaffinity=1)
    end=add(parent,'body',name='leaf_junction',pos='.01 0 0')
    mass=geom_report['mesh_area_m2']*.16
    flex=add(end,'flexcomp',name='leaf',type='direct',dim=2,point=vec(points),
             element=' '.join(map(str,faces.ravel())),mass=mass,radius='.0002',rgba='.19 .38 .09 1')
    add(flex,'pin',id=' '.join(map(str,pin)))
    add(flex,'edge',equality='true',damping='.0005',solref='.004 1')
    add(flex,'elasticity',young=15e6,poisson=.3,thickness=.0004,elastic2d='bend',damping=.001)
    add(flex,'contact',selfcollide='auto',internal='false',contype=2,conaffinity=1,condim=3,friction='.35 .003 .001',solref='.004 1')
    probe=add(w,'body',name='probe')
    add(probe,'geom',name='probe_surface',type='sphere',size=.009,mass=.02,rgba='.93 .50 .10 1',contype=1,conaffinity=7)
    for i in range(3):
        add(probe,'joint',name=f'probe_{i}',type='slide',axis=vec(np.eye(3)[i]),damping=.1)
        add(act,'position',name=f'probe_{i}',joint=f'probe_{i}',kp=25,kv=.7,forcerange='-.2 .2')
    ET.indent(r)
    xml=ET.tostring(r,encoding='unicode')
    return mujoco.MjModel.from_xml_string(xml),xml


def command(t):
    start=np.array([.12,.004,.26]);end=np.array([.12,.004,.155])
    if t<.5:return start
    if t<2.:u=(t-.5)/1.5
    elif t<2.6:return end
    elif t<4.1:u=1-(t-2.6)/1.5
    else:return start
    u=u*u*(3-2*u)
    return start+(end-start)*u


def run(dt,control,points,faces,pin,geometry_report):
    m,xml=build(dt,points,faces,pin,geometry_report);d=mujoco.MjData(m)
    adr=[m.joint(f'probe_{i}').qposadr[0] for i in range(3)]
    d.qpos[adr]=command(0);d.ctrl[:]=command(0);mujoco.mj_forward(m,d)
    for _ in range(round(5/dt)):
        mujoco.mj_step(m,d)
        if any(x.number for x in d.warning):raise RuntimeError('Settling is unstable')
    # Preserve all velocities after settling. No poses are reset during contact.
    first=d.flexvert_xpos.copy();frames=[];qs=[];peak=penetration=0.;hits=set();duration=0.
    pg=m.geom('probe_surface').id
    quiet=[]
    for step in range(round(6/dt)):
        t=step*dt;d.ctrl[:]=command(0 if control else t);mujoco.mj_step(m,d)
        force=0.;touched=False
        for j,c in enumerate(d.contact):
            if pg not in c.geom:continue
            f=np.zeros(6);mujoco.mj_contactForce(m,d,j,f);force+=max(0,f[0])
            penetration=max(penetration,max(0,-c.dist))
            for gid in c.geom:
                if gid>=0 and gid!=pg:hits.add(m.geom(gid).name)
            if 0 in c.flex:hits.add('leaf');touched=True
        peak=max(peak,force);duration+=dt*touched
        if step%round(.04/dt)==0:
            frames.append({'t':round((step+1)*dt,6),'vertices':d.flexvert_xpos.round(7).tolist(),
                           'positions':d.geom_xpos.round(7).tolist(),'rotations':d.geom_xmat.round(7).tolist(),
                           'force_n':float(force)})
            qs.append(d.qpos.copy())
            if t<.45:quiet.append(d.flexvert_xpos.copy())
        if any(x.number for x in d.warning) or not np.isfinite(d.qpos).all():
            raise RuntimeError('Unstable run; do not promote or render as passing')
    report={'dt_s':dt,'control':control,'simulator':mujoco.__version__,'recorded_seconds':6,
            'settling_seconds':5,'peak_probe_normal_force_n':float(peak),'max_probe_penetration_mm':float(penetration*1000),
            'probe_contacted':sorted(hits),'leaf_contact_duration_s':duration,
            'pre_intervention_drift_mm':float(np.max(np.linalg.norm(np.array(quiet)-first,axis=2))*1000),
            'final_difference_from_initial_mm':float(np.max(np.linalg.norm(d.flexvert_xpos-first,axis=1))*1000),
            'warnings':[int(w.number) for w in d.warning],
            'scope':'Assumed material contact diagnostic. Scripted finite-force probe; no learned policy, cutting, or biological calibration.'}
    geoms=[{'name':m.geom(i).name,'type':int(m.geom_type[i]),'size':m.geom_size[i].tolist(),'rgba':m.geom_rgba[i].tolist()} for i in range(m.ngeom)]
    return report,{'faces':faces.tolist(),'geoms':geoms,'frames':frames},np.array(qs),xml


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--geometry-only',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    raw,points,faces,pin,g=geometry()
    np.savez_compressed(OUT/'geometry.npz',raw_outline=raw,vertices=points,faces=faces)
    (OUT/'geometry-report.json').write_text(json.dumps(g,indent=2))
    (OUT/'geometry.json').write_text(json.dumps({'raw_outline':raw.tolist(),'vertices':points.tolist(),'faces':faces.tolist(),'pins':pin.tolist(),'report':g},separators=(',',':')))
    _,xml=build(.0005,points,faces,pin,g);(OUT/'candidate.xml').write_text(xml)
    if args.geometry_only:return
    reports=[];logs={}
    for name,dt,control in [('contact',.0005,False),('control',.0005,True),('refined',.00025,False)]:
        try:
            report,replay,q,xml=run(dt,control,points,faces,pin,g)
        except RuntimeError as error:
            failure={'status':'rejected','stage':name,'dt_s':dt,'reason':str(error),'biologically_calibrated':False,
                     'source_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                     'next_check':'Condition the finite-element mesh and assess explicit bending-force timestep sensitivity; do not weaken material assumptions merely to pass.'}
            (OUT/'failure.json').write_text(json.dumps(failure,indent=2))
            raise
        reports.append(report);logs[name]=(replay,q,xml)
        (OUT/f'{name}.json').write_text(json.dumps(replay,separators=(',',':')))
        (OUT/f'{name}-report.json').write_text(json.dumps(report,indent=2))
        (OUT/f'{name}.xml').write_text(xml)
        np.savez_compressed(OUT/f'{name}.npz',qpos=q)
        print(name,json.dumps(report),flush=True)
    force_error=abs(reports[2]['peak_probe_normal_force_n']-reports[0]['peak_probe_normal_force_n'])/max(reports[0]['peak_probe_normal_force_n'],1e-9)
    tip_difference=max(np.max(np.linalg.norm(np.array(a['vertices'])-np.array(b['vertices']),axis=1)) for a,b in zip(logs['contact'][0]['frames'],logs['refined'][0]['frames']))
    summary={'geometry':g,'runs':reports,'refinement_peak_force_relative_difference':force_error,
             'refinement_max_vertex_difference_mm':float(tip_difference*1000),
             'numerical_checks_pass':bool('leaf' in reports[0]['probe_contacted'] and not reports[1]['probe_contacted'] and reports[0]['max_probe_penetration_mm']<1 and force_error<.15 and tip_difference<.002),
             'biologically_calibrated':False,
             'assumptions':{'blade_areal_mass_kg_per_m2':.16,'blade_effective_young_pa':15e6,'blade_thickness_m':.0004,
                            'petiole_effective_young_pa':25e6,'petiole_length_m':.05,'petiole_density_kg_per_m3':850,
                            'contact_friction':.35,'tissue_model':'isotropic elastic blade; in-plane edge constraints; no explicit veins, turgor, growth or fracture'},
             'source_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2))
    np.savez_compressed(OUT/'geometry.npz',raw_outline=raw,vertices=points,faces=faces)
    print('SUMMARY',json.dumps(summary),flush=True)


if __name__=='__main__':main()
