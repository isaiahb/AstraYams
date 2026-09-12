"""Assemble whole-plant candidates into an explicit indoor working context.

Uses the existing anatomy generator, without overwriting its v1 checkpoint.
All output is static geometry; scene hardware has no simulated mechanics yet.
"""
from pathlib import Path
from collections import Counter
import importlib.util
import json, hashlib, shutil
import numpy as np
import trimesh

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=ROOT/'runs/hemp-indoor-v1'
CFG=json.loads((HERE/'config.json').read_text())
SPEC=importlib.util.spec_from_file_location('anatomy',HERE.parent/'whole-plant/build.py')
B=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(B)
BASE=dict(B.C)
GROUPS={};ORGANS=[];SPECIMENS=[]
HARDWARE=[]


def join_group(kind,g,prefix,rot,offset):
    out=GROUPS.setdefault(kind,{'vertices':[],'faces':[],'colors':[],'organs':[]})
    nv,nf=len(out['vertices']),len(out['faces'])
    out['vertices'].extend((np.array(g['vertices'])@rot.T+offset).round(7).tolist())
    out['faces'].extend((np.array(g['faces'])+nv).tolist())
    out['colors'].extend(g['colors'])
    out['organs'].extend([{'id':prefix+r['id'],'first_face':nf+r['first_face'],'end_face':nf+r['end_face']} for r in g['organs']])


def specimen(s):
    B.C={**BASE,**s,'id':f"indoor-{s['id']}"}
    B.R=np.random.default_rng(s['seed']);B.GROUPS={};B.ORGANS=[]
    B.build()
    a=s['yaw_rad'];rot=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]])
    offset=np.array([s['x_m'],s['y_m'],CFG['bench']['surface_z_m']+B.C['pot_depth_m']])
    prefix=s['id']+'/'
    for kind,g in B.GROUPS.items():join_group(kind,g,prefix,rot,offset)
    for item in B.ORGANS:
        o={**item,'id':prefix+item['id'],'parent':prefix+item['parent'] if item['parent'] else None,'specimen':s['id']}
        o['attachment']=(rot@np.array(item['attachment'])+offset).round(7).tolist()
        if 'centerline' in item:o['centerline']=(np.array(item['centerline'])@rot.T+offset).round(7).tolist()
        ORGANS.append(o)
    plant_vertices=np.concatenate([np.array(g['vertices']) for k,g in B.GROUPS.items() if k not in ['root','pot','substrate']])@rot.T+offset
    SPECIMENS.append({**s,'substrate_origin_m':offset.tolist(),'bounds_m':[plant_vertices.min(0).tolist(),plant_vertices.max(0).tolist()],
       'organ_counts':dict(Counter(o['kind'] for o in B.ORGANS)),
       'geometry_sha256':hashlib.sha256(plant_vertices.tobytes()).hexdigest()})


def hardware(kind,name,model,color,parent=None,representation='assumed scene geometry'):
    id_='hardware/'+name
    ORGANS.append({'id':id_,'kind':kind,'parent':parent,'attachment':model.centroid.round(7).tolist(),'representation':representation})
    out=GROUPS.setdefault(kind,{'vertices':[],'faces':[],'colors':[],'organs':[]})
    nv,nf=len(out['vertices']),len(out['faces'])
    out['vertices'].extend(model.vertices.round(7).tolist());out['faces'].extend((model.faces+nv).tolist())
    out['colors'].extend([color]*len(model.vertices));out['organs'].append({'id':id_,'first_face':nf,'end_face':nf+len(model.faces)})
    HARDWARE.append({'id':id_,'kind':kind,'bounds_m':model.bounds.tolist()})
    return id_


def box(kind,name,pos,size,color,parent=None):
    m=trimesh.creation.box(extents=size);m.apply_translation(pos)
    return hardware(kind,name,m,color,parent)


def rod(kind,name,start,end,radius,color,parent=None):
    m=trimesh.creation.cylinder(radius=radius,segment=[start,end],sections=12)
    return hardware(kind,name,m,color,parent)


def surroundings():
    l=CFG['bench']['length_m'];d=CFG['bench']['depth_m'];z=CFG['bench']['surface_z_m']
    metal=[.55,.61,.58];white=[.80,.84,.79];dark=[.13,.18,.17]
    bench=box('bench','tray',[0,0,z-.012],[l,d,.024],white)
    for x in [-l/2+.07,0,l/2-.07]:
        for y in [-d/2+.06,d/2-.06]:
            box('bench',f'leg-{x}-{y}',[x,y,(z-.025)/2],[.035,.035,z-.025],metal,bench)
        box('bench',f'cross-{x}',[x,0,z-.048],[.035,d-.08,.048],metal,bench)
    for y in [-d/2+.013,d/2-.013]:
        box('bench',f'lip-{y}',[0,y,z+.017],[l,.026,.034],white,bench)
    for x in [-l/2+.013,l/2-.013]:
        box('bench',f'end-{x}',[x,0,z+.017],[.026,d,.034],white,bench)
    # Frame carries the light bars and optional net; no unsupported floating lights.
    for x in [-l/2+.04,l/2-.04]:
        for y in [-d/2+.04,d/2-.04]:
            box('rack',f'post-{x}-{y}',[x,y,1.20],[.025,.025,2.40],metal)
    for y in [-d/2+.04,d/2-.04]:box('rack',f'light-rail-{y}',[0,y,2.38],[l-.05,.025,.025],metal)
    for x in [-.93,-.31,.31,.93]:
        box('rack',f'hanger-crossbar-{x}',[x,0,2.38],[.025,d-.05,.025],metal)
        box('light',f'bar-{x}',[x,0,CFG['lighting_z_m']],[.055,.70,.035],dark)
        box('diffuser',f'diffuser-{x}',[x,0,CFG['lighting_z_m']-.02],[.049,.68,.006],[.95,.96,.82])
        for y in [-.29,.29]:rod('rack',f'hanger-{x}-{y}',[x,y,CFG['lighting_z_m']+.015],[x,y,2.38],.0018,metal)
    # Water line is visual route context, not a fluid model or emitter prescription.
    rod('irrigation','main-line',[-1.15,.37,z+.045],[1.15,.37,z+.045],.008,dark,bench)
    for s in CFG['specimens']:
        x,y=s['x_m'],s['y_m'];h=z+BASE['pot_depth_m']
        points=[[x,.37,z+.045],[x,.30,h+.05],[x,y+.17,h+.05],[x,y+.11,h-.012]]
        parent='hardware/main-line'
        for i,(a,b) in enumerate(zip(points[:-1],points[1:])):
            parent=rod('irrigation',f"{s['id']}-feed-{i}",a,b,.003,dark,parent)
    # Optional trellis is hidden by default: partner usage is unknown.
    nz=z+BASE['pot_depth_m']+CFG['trellis']['height_above_substrate_m'];rr=CFG['trellis']['cord_radius_m']
    for y in [-.42,.42]:rod('trellis',f'edge-y-{y}',[-1.21,y,nz],[1.21,y,nz],rr*1.5,[.65,.70,.57])
    for x in [-1.21,1.21]:rod('trellis',f'edge-x-{x}',[x,-.42,nz],[x,.42,nz],rr*1.5,[.65,.70,.57])
    for i,x in enumerate(np.arange(-1.1,1.2,.20)):rod('trellis',f'grid-x-{i}',[x,-.42,nz],[x,.42,nz],rr,[.65,.70,.57])
    for i,y in enumerate(np.arange(-.3,.4,.20)):rod('trellis',f'grid-y-{i}',[-1.21,y,nz],[1.21,y,nz],rr,[.65,.70,.57])


def save():
    OUT.mkdir(parents=True,exist_ok=True)
    scene=trimesh.Scene();triangles=0;ids={o['id'] for o in ORGANS};lookup={o['id']:o for o in ORGANS}
    assert len(ids)==len(ORGANS)
    for o in ORGANS:
        assert o['parent'] is None or o['parent'] in ids
        visited=set();p=o
        while p['parent']:
            assert p['id'] not in visited;visited.add(p['id']);p=lookup[p['parent']]
    for kind,g in GROUPS.items():
        v=np.array(g['vertices']);f=np.array(g['faces']);triangles+=len(f)
        assert np.isfinite(v).all() and f.min()>=0 and f.max()<len(v)
        assert (np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)>1e-14).all()
        m=trimesh.Trimesh(v,f,vertex_colors=np.round(np.array(g['colors'])*255).astype(np.uint8),process=False)
        scene.add_geometry(m,node_name=kind,geom_name=kind)
    (OUT/'plant.glb').write_bytes(scene.export(file_type='glb'))
    metadata={'config':CFG,'specimens':SPECIMENS,'organs':ORGANS,'groups':{k:{'organs':g['organs'],'triangles':len(g['faces'])} for k,g in GROUPS.items()}}
    (OUT/'review-data.json').write_text(json.dumps(metadata,separators=(',',':')))
    (OUT/'plant.json').write_text(json.dumps({**metadata,'groups':GROUPS},separators=(',',':')))
    (OUT/'anatomy-graph.json').write_text(json.dumps({'config':CFG,'specimens':SPECIMENS,'organs':ORGANS},separators=(',',':')))
    report={'status':CFG['status'],'unique_ids':True,'parents_resolve':True,'acyclic':True,'nondegenerate_meshes':True,
      'specimens':SPECIMENS,'triangles':triangles,'physical_contact_validated':False,'growth_model':False,'fitted_domain_randomization':False,
      'geometry_source_sha256':hashlib.sha256((HERE.parent/'whole-plant/build.py').read_bytes()).hexdigest(),
      'scene_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'config_sha256':hashlib.sha256((HERE/'config.json').read_bytes()).hexdigest(),
      'glb_sha256':hashlib.sha256((OUT/'plant.glb').read_bytes()).hexdigest()}
    (OUT/'report.json').write_text(json.dumps(report,indent=2))
    shutil.copy2(HERE/'review.html',OUT/'index.html')
    print(json.dumps({'output':str(OUT),'triangles':triangles,'specimens':len(SPECIMENS),'status':report['status']}))


if __name__=='__main__':
    for s in CFG['specimens']:specimen(s)
    surroundings();save()
