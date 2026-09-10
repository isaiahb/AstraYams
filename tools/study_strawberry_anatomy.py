"""Reproducible anatomy v4, preserving v3 morphology and physical recordings."""
from pathlib import Path
import json,hashlib,shutil
import xml.etree.ElementTree as E
import numpy as np,mujoco,trimesh
from PIL import Image,ImageDraw,ImageFont
from strawberry_surface import make_fruit,enrich

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'assets/workcells/strawberry-specimen/surface-study/v3'
OUT=OLD.parent/'v4'
def dump(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def scene(f,path):
    root=E.Element('mujoco');assets=E.SubElement(root,'asset');world=E.SubElement(root,'worldbody')
    E.SubElement(world,'body',name='fruit_'+f['id']);E.SubElement(world,'light',pos='-.15 -.25 .2',diffuse='.8 .8 .8',ambient='.3 .3 .3')
    E.SubElement(assets,'texture',type='skybox',builtin='flat',rgb1='.91 .93 .88',rgb2='.91 .93 .88',width='32',height='32')
    visual=E.SubElement(root,'visual');E.SubElement(visual,'headlight',ambient='.4 .4 .4',diffuse='.7 .7 .7',specular='.12 .12 .12')
    enrich(root,dict(truss=[dict(fruit=f)]),path.parent/path.stem);E.ElementTree(root).write(path,encoding='unicode')

def library():
    OUT.mkdir(parents=True,exist_ok=True);folder=OUT/'library';folder.mkdir(exist_ok=True)
    library=json.loads((OLD/'shape-library.json').read_text());reports={}
    for i,e in enumerate(library['examples']):
        f=e['parameters'];f['surface_recipe']=4
        # Explicit priors, independent of the outline fit; not cultivar labels.
        f['calyx_parameters']=dict(span_scale=[.90,1.05,.80,.94,1.08,.86][i],tip_curl_m=[-.001,.001,.002,-.002,0,.001][i],sepals=5)
        meshes,report=make_fruit(f)
        site_file=folder/(e['id']+'-sites.json');dump(site_file,report.pop('sites'));report['achene_site_file']=str(site_file.relative_to(OUT))
        reports[e['id']]=report;model=trimesh.Scene()
        for kind,g in meshes.items():model.add_geometry(g,node_name=kind)
        model.export(folder/(e['id']+'.glb'));scene(f,folder/(e['id']+'.xml'))
        print('Anatomy example',e['name'],report['achene_count'],'sites',flush=True)
    dump(OUT/'shape-library.json',library);dump(OUT/'anatomy-audit.json',reports)

def build():
    root=E.parse(OLD/'scene.xml').getroot();spec=json.loads((OLD/'reference-graph.json').read_text())
    for parent in root.iter():
        for el in list(parent):
            if el.get('name','').startswith('fruit_detail_'):parent.remove(el)
    for branch in spec['truss']:
        if 'fruit' in branch:branch['fruit']['surface_recipe']=4
    report=enrich(root,spec,OUT/'meshes')
    for fid,r in report.items():
        site_file=OUT/'meshes'/(fid+'-sites.json');dump(site_file,r.pop('sites'));r['achene_site_file']=str(site_file.relative_to(OUT))
    E.indent(root);E.ElementTree(root).write(OUT/'scene.xml',encoding='unicode')
    dump(OUT/'reference-graph.json',spec);dump(OUT/'plant-anatomy-audit.json',report)
    a=mujoco.MjModel.from_xml_path(str(OLD/'scene.xml'));b=mujoco.MjModel.from_xml_path(str(OUT/'scene.xml'))
    attrs=['body_mass','body_inertia','body_ipos','body_iquat','body_parentid','body_pos','body_quat','jnt_pos','jnt_axis','jnt_stiffness','dof_damping','dof_armature','qpos_spring','qpos0','actuator_gainprm','actuator_biasprm','actuator_gear','actuator_forcerange']
    checks={key:bool(np.array_equal(getattr(a,key),getattr(b,key))) for key in attrs}
    collision=[]
    for i in range(a.ngeom):
        if a.geom_contype[i] or a.geom_conaffinity[i]:
            j=b.geom(a.geom(i).name).id
            for key in ['geom_type','geom_bodyid','geom_size','geom_pos','geom_quat','geom_friction','geom_solref','geom_solimp','geom_contype','geom_conaffinity']:
                assert np.array_equal(getattr(a,key)[i],getattr(b,key)[j]),(a.geom(i).name,key)
            if a.geom_type[i]==mujoco.mjtGeom.mjGEOM_MESH:
                x,y=a.geom_dataid[i],b.geom_dataid[j]
                for key,adr,num in [('mesh_vert','mesh_vertadr','mesh_vertnum'),('mesh_face','mesh_faceadr','mesh_facenum')]:
                    v0=getattr(a,key)[getattr(a,adr)[x]:getattr(a,adr)[x]+getattr(a,num)[x]]
                    v1=getattr(b,key)[getattr(b,adr)[y]:getattr(b,adr)[y]+getattr(b,num)[y]]
                    assert np.array_equal(v0,v1),(a.geom(i).name,key)
            collision.append(a.geom(i).name)
    assert all(checks.values()),checks
    z=np.load(OLD/'initial-state.npz');d0=mujoco.MjData(a);d1=mujoco.MjData(b)
    for d in [d0,d1]:d.qpos[:]=z['qpos'];d.qvel[:]=z['qvel'];d.ctrl[:]=z['ctrl']
    # Replay compatibility requires more than identical masses: short identical
    # stepping catches accidental changes in contact or dynamics configuration.
    mujoco.mj_step(a,d0,nstep=100);mujoco.mj_step(b,d1,nstep=100)
    assert np.array_equal(d0.qpos,d1.qpos) and np.array_equal(d0.qvel,d1.qvel)
    dump(OUT/'physics-equivalence.json',dict(source_sha256=sha(OLD/'scene.xml'),revision_sha256=sha(OUT/'scene.xml'),exact_compiled_checks=checks,collision_geometries_checked=len(collision),identical_100_step_qpos_qvel=True,
         scope='Appearance-only revision. V3 rest, contact and control trajectories are reused after exact physical checks; no new training or material calibration.'))
    shutil.copy2(OLD/'initial-state.npz',OUT/'initial-state.npz')
    print('Full plant physical equivalence verified',flush=True)

def export():
    import render_strawberry_specimen as exporter
    for kind in ['rest','neighbor','neighbor-control']:
        folder=OUT/kind;folder.mkdir(exist_ok=True)
        link=folder/'rollout.npz'
        if not link.exists():link.symlink_to(Path('../../v3')/kind/'rollout.npz')
    exporter.P=OUT;exporter.export(kinds=['rest','neighbor','neighbor-control'])
    for kind in ['rest','neighbor','neighbor-control']:
        dump(OUT/kind/'provenance.json',dict(trajectory_source=f'../../v3/{kind}/rollout.npz',trajectory_sha256=sha(OLD/kind/'rollout.npz'),appearance_only=True,physical_equivalence='../physics-equivalence.json'))
    cad_context()

def cad_context():
    context=json.loads((OLD/'cad-context.json').read_text())
    poses={o['body']:(o['position'],o['quaternion']) for o in context['objects']}
    objects=[o for o in json.loads((OUT/'rest/replay.json').read_text())['objects'] if o['body']!='probe']
    for o in objects:o.update(position=poses[o['body']][0],quaternion=poses[o['body']][1])
    context.update(objects=objects,source_scene=str((OUT/'scene.xml').relative_to(ROOT)),source_pose=str((OUT/'initial-state.npz').relative_to(ROOT)),scope='V4 appearance on the exact same V3 physical plant and settled pose; tool placement remains static CAD.')
    dump(OUT/'cad-context.json',context)
    dump(ROOT/'cad/harvest-tools/rev-b/specimen-source.json',dict(context='/'+str((OUT/'cad-context.json').relative_to(ROOT)),physics_review='/'+str((OUT/'plant.html').relative_to(ROOT)),morphology_review='/'+str((OUT/'index.html').relative_to(ROOT)),source_sha256=sha(OUT/'scene.xml')))

def render():
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',22)
    lib=json.loads((OUT/'shape-library.json').read_text())['examples'];e=lib[4]
    board=Image.new('RGB',(1500,1050),'#e8eddf');draw=ImageDraw.Draw(board)
    for row,base in enumerate([OLD,OUT]):
        root=E.parse(base/'library/4.xml').getroot()
        head=root.find('./visual/headlight');head.set('ambient','.4 .4 .4');head.set('diffuse','.7 .7 .7');head.set('specular','.12 .12 .12')
        light=root.find('./worldbody/light');light.set('ambient','.3 .3 .3');light.set('diffuse','.8 .8 .8')
        sky=root.find('./asset/texture');sky.set('rgb1','.91 .93 .88');sky.set('rgb2','.91 .93 .88')
        m=mujoco.MjModel.from_xml_string(E.tostring(root,encoding='unicode'));d=mujoco.MjData(m);mujoco.mj_forward(m,d)
        m.vis.global_.offwidth=500;m.vis.global_.offheight=500;r=mujoco.Renderer(m,460,500)
        cam=mujoco.MjvCamera();cam.orthographic=1;cam.lookat[:]=[0,0,-.002-e['parameters']['length']/2];cam.distance=.072
        for col,(az,el) in enumerate([(-90,0),(0,0),(-90,-72)]):
            cam.azimuth=az;cam.elevation=el;r.update_scene(d,cam);r.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=0
            board.paste(Image.fromarray(r.render()),(col*500,row*525+45))
            draw.text((col*500+20,row*525+12),('V3 · ' if row==0 else 'V4 · ')+['Fitted front','Assumed side','Calyx from above'][col],font=font,fill='#2b402d')
        r.close()
    board.save(OUT/'anatomy-comparison.png')
    import reshape_strawberry as shared
    shared.OUT=OUT;shared.OLD=OLD;shared.render()
    image=Image.open(OUT/'comparison.png');d=ImageDraw.Draw(image);d.rectangle((0,0,1400,58),fill='#edf1e7');d.text((20,15),'V3 · repeated cap and seed rows',font=font,fill='#263f2d');d.text((720,15),'V4 · surface anatomy, same physics',font=font,fill='#263f2d');image.save(OUT/'comparison.png')

def fit():
    """Recheck source-view projection after surface indentation changes."""
    profiles=json.loads((OLD/'outline-profiles.json').read_text())['profiles']
    baseline={x['id']:x for x in json.loads((OLD/'projection-fit.json').read_text())};results=[]
    for e in json.loads((OUT/'shape-library.json').read_text())['examples']:
        f=e['parameters'];p=next(p for p in profiles if p['id']==f['morphology']['id'])
        truth=np.asarray(Image.open(OLD/'reference'/('mask-'+p['id']+'.png')))>0
        g=trimesh.load(OUT/'library'/e['id']/('fruit_detail_'+f['id']+'_skin.stl'),force='mesh')
        xy=np.c_[p['x_min_px']+(-g.vertices[:,2]-.002)/f['length']*p['length_px'],p['anchor_y_px']-g.vertices[:,0]/f['radius']*p['half_width_px']]
        mask=Image.new('L',(truth.shape[1],truth.shape[0]));draw=ImageDraw.Draw(mask)
        for face in g.faces:draw.polygon([tuple(x) for x in xy[face]],fill=255)
        pred=np.asarray(mask)>0;iou=float((pred&truth).sum()/(pred|truth).sum());previous=baseline[e['id']]['fitted_view_iou']
        results.append(dict(name=e['name'],v3_iou=previous,v4_iou=iou,delta=iou-previous))
        assert abs(iou-previous)<.01,(e['name'],iou,previous)
    dump(OUT/'projection-regression.json',dict(results=results,scope='In-sample source-view regression only. All changes less than 0.01 IoU; no new 3D validation.'))
    print('Fitted-view outline regression checked',flush=True)

def native():
    import build_strawberry_specimen as builder
    path=Path('/tmp/strawberry-anatomy-v4-native')
    builder.build(path,OUT/'reference-graph.json',detailed_fruit=True)
    a=mujoco.MjModel.from_xml_path(str(OUT/'scene.xml'));b=mujoco.MjModel.from_xml_path(str(path/'scene.xml'))
    attrs=['body_mass','body_inertia','body_ipos','body_pos','body_quat','jnt_stiffness','dof_damping','qpos_spring','qpos0']
    checks={k:bool(np.allclose(getattr(a,k),getattr(b,k),rtol=1e-10,atol=1e-12)) for k in attrs}
    def tensors(m):
        result=[]
        for inertia,q in zip(m.body_inertia,m.body_iquat):
            r=np.zeros(9);mujoco.mju_quat2Mat(r,q);r=r.reshape(3,3);result.append(r@np.diag(inertia)@r.T)
        return np.asarray(result)
    t0,t1=tensors(a),tensors(b)
    error=np.linalg.norm(t0-t1,axis=(1,2));scale=np.linalg.norm(t0,axis=(1,2))
    checks['body_frame_inertia_tensors']=bool(np.all(error<=1e-9*scale+1e-20))
    assert all(checks.values()),checks
    dump(OUT/'native-builder-check.json',dict(checks=checks,max_inertia_tensor_difference_kg_m2=float(abs(t0-t1).max()),
        max_relative_tensor_norm_error=float(np.max(error/np.maximum(scale,1e-30))),
        max_inertia_quaternion_component_difference=float(abs(a.body_iquat-b.body_iquat).max()),
        scope='Canonical builder reproduces physical model within floating-point tolerances. Inertia is compared by body-frame tensor Frobenius norm, not near-zero individual components.',rtol=1e-10,atol=1e-12,tensor_norm_rtol=1e-9,tensor_norm_atol=1e-20))
    print('Canonical full-plant builder compatibility checked',flush=True)

if __name__=='__main__':
    import sys
    for step in sys.argv[1:] or ['library','build','export','render','fit','native']:globals()[step]()
