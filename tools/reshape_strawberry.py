"""Compact fruit shapes, corresponding collision/COM/inertia, fresh full-plant physics."""
from pathlib import Path
import json,time,hashlib
import xml.etree.ElementTree as E
import numpy as np,mujoco,trimesh
from PIL import Image,ImageDraw,ImageFont
from strawberry_surface import reshape_physical,enrich,envelope

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/workcells/strawberry-specimen/surface-study/v2'
BASE=ROOT/'assets/workcells/strawberry-specimen/fruit-study/v14'
REC=ROOT/'assets/workcells/strawberry-specimen/recovery-study/v2'
OLD=ROOT/'assets/workcells/strawberry-specimen/surface-study/v1'
CAD=ROOT/'cad/harvest-tools/rev-b'
def dump(p,x):p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(x,indent=2)+'\n')
def build():
    OUT.mkdir(exist_ok=True,parents=True);root=E.parse(BASE/'scene.xml').getroot();spec=json.loads((BASE/'reference-graph.json').read_text())
    spec=reshape_physical(root,spec);report=enrich(root,spec,OUT/'meshes');E.indent(root);E.ElementTree(root).write(OUT/'scene.xml',encoding='unicode')
    dump(OUT/'reference-graph.json',spec)
    a=mujoco.MjModel.from_xml_path(str(BASE/'scene.xml'));b=mujoco.MjModel.from_xml_path(str(OUT/'scene.xml'))
    for attr in ['body_mass','body_parentid','body_pos','body_quat','jnt_stiffness','dof_damping','dof_armature','qpos_spring','qpos0']:
        assert np.array_equal(getattr(a,attr),getattr(b,attr)),attr
    fruits={b.body('fruit_'+f).id for f in report};others=[i for i in range(b.nbody) if i not in fruits]
    assert np.array_equal(a.body_inertia[others],b.body_inertia[others])
    assert np.array_equal(a.body_ipos[others],b.body_ipos[others])
    for branch in spec['truss']:
        if 'fruit' not in branch:continue
        f=branch['fruit'];i=b.body('fruit_'+f['id']).id
        g0=a.geom('berry_'+f['id']).id;g1=b.geom('berry_'+f['id']).id
        def bounds(model,g):
            idx=model.geom_dataid[g];verts=model.mesh_vert[model.mesh_vertadr[idx]:model.mesh_vertadr[idx]+model.mesh_vertnum[idx]]
            return np.ptp(verts,axis=0)*1000
        report[f['id']].update(old_envelope_dimensions_mm=bounds(a,g0).tolist(),new_envelope_dimensions_mm=bounds(b,g1).tolist(),mass_g=float(b.body_mass[i]*1000),
           old_com_m=a.body_ipos[i].tolist(),new_com_m=b.body_ipos[i].tolist(),old_inertia_kg_m2=a.body_inertia[i].tolist(),new_inertia_kg_m2=b.body_inertia[i].tolist(),
           density_assumption_kg_m3=1000.,collision_mesh_volume_mm3=float(envelope(f).volume*1e9))
    dump(OUT/'shape-audit.json',dict(fruit=report,nq=b.nq,nv=b.nv,
       unchanged='All masses, non-fruit inertias, plant attachments, springs, damping, topology and timestep.',
       changed='Fruit collision envelopes, appearance, COM and inertia; fresh gravity response required.',
       references=['https://www.jstage.jst.go.jp/article/jsbbs/71/2/71_19106/_html/-char/en','https://strawberrycenterblog.com/2025/11/25/strawberry-anatomy-part-2-the-fruit/'],
       assumptions='Compact-conic shape ratios and 1000 kg/m3 homogeneous density are design priors, not fitted specimen measurements.'))
    print('Built compact shapes with new collision envelopes and inertias',flush=True)

def settle():
    m=mujoco.MjModel.from_xml_path(str(OUT/'scene.xml'));d=mujoco.MjData(m)
    src=mujoco.MjModel.from_xml_path(str(ROOT/'assets/workcells/strawberry-specimen/support-study/v2/scene.xml'))
    z=np.load(REC/'initial-state.npz')
    for j in range(m.njnt):
        k=src.joint(m.joint(j).name).id;n=4 if int(m.jnt_type[j])==1 else 1;nv=3 if n==4 else 1
        q=m.jnt_qposadr[j];v=m.jnt_dofadr[j];d.qpos[q:q+n]=z['qpos'][src.jnt_qposadr[k]:src.jnt_qposadr[k]+n];d.qvel[v:v+nv]=z['qvel'][src.jnt_dofadr[k]:src.jnt_dofadr[k]+nv]
    for i in range(3):d.ctrl[m.actuator(f'probe_{i}').id]=d.qpos[m.joint(f'probe_{i}').qposadr[0]]
    pg=m.geom('probe_surface').id;m.geom_contype[pg]=m.geom_conaffinity[pg]=0;mujoco.mj_forward(m,d)
    bids=[m.body('fruit_'+s).id for s in ['primary','secondary_a','secondary_b','green']]
    q=[d.qpos.copy()];v=[d.qvel.copy()];ts=[0.];positions=[d.xpos[bids].copy()];history=[];tc=time.time()
    for tenth in range(1,801):
        mujoco.mj_step(m,d,nstep=round(.1/m.opt.timestep));mujoco.mj_forward(m,d)
        assert not any(w.number for w in d.warning)
        q.append(d.qpos.copy());v.append(d.qvel.copy());ts.append(float(d.time));positions.append(d.xpos[bids].copy())
        if tenth%50==0:
            span=float(np.ptp(np.array(positions[-51:]),axis=0).max()*1000);speed=float(abs(d.qvel).max())
            row=dict(time_s=float(d.time),last_5s_fruit_span_mm=span,max_generalized_speed=speed);history.append(row);print('Settling',row,'wall',round(time.time()-tc,1),flush=True)
            if tenth>=200 and span<.01 and speed<1e-4:break
    out=OUT/'rest';out.mkdir(exist_ok=True);np.savez_compressed(out/'rollout.npz',qpos=q,qvel=v,t=ts,fruit_positions=positions)
    np.savez_compressed(OUT/'initial-state.npz',qpos=d.qpos,qvel=d.qvel,ctrl=d.ctrl)
    dump(out/'result.json',dict(kind='rest',seconds=float(d.time),history=history,quiet=span<.01 and speed<1e-4,
       scope='Fresh full-plant gravity settling from preceding state after the fruit shape change. Original elastic/damped plant law; no replayed old-shape motion.'))
    print('Settled',d.time,'s',flush=True)

def export():
    import render_strawberry_specimen as exporter
    exporter.P=OUT;exporter.export(kinds=['rest','neighbor','neighbor-control'])
    m=mujoco.MjModel.from_xml_path(str(OUT/'scene.xml'));d=mujoco.MjData(m);z=np.load(OUT/'initial-state.npz');d.qpos[:]=z['qpos'];mujoco.mj_forward(m,d)
    r=json.loads((OUT/'rest/replay.json').read_text());objects=[o for o in r['objects'] if o['body']!='probe']
    for o in objects:
        i=m.body(o['body']).id;o.update(position=d.xpos[i].tolist(),quaternion=d.xquat[i][[1,2,3,0]].tolist())
    i=m.geom('berry_primary').id;k=m.geom_dataid[i];vv=m.mesh_vert[m.mesh_vertadr[k]:m.mesh_vertadr[k]+m.mesh_vertnum[k]]
    vv=vv@d.geom_xmat[i].reshape(3,3).T+d.geom_xpos[i];body=m.body('fruit_primary').id
    shift=np.array([-d.xipos[body][0],-d.xipos[body][1],.012-vv[:,2].min()])
    dump(OUT/'cad-context.json',dict(objects=objects,world_to_cad_translation_mm=(shift*1000).tolist(),fruit_attachment_cad_mm=((d.xpos[body]+shift)*1000).tolist(),
           source_scene=str((OUT/'scene.xml').relative_to(ROOT)),source_pose=str((OUT/'initial-state.npz').relative_to(ROOT)),scope='New compact collision geometry, fresh full-plant settled pose. Tool placement remains static CAD.'))
    dump(CAD/'specimen-source.json',dict(context='/'+str((OUT/'cad-context.json').relative_to(ROOT)),physics_review='/'+str((OUT/'index.html').relative_to(ROOT)),source_sha256=hashlib.sha256((OUT/'scene.xml').read_bytes()).hexdigest()))

def render():
    models=[mujoco.MjModel.from_xml_path(str(OLD/'scene.xml')),mujoco.MjModel.from_xml_path(str(OUT/'scene.xml'))]
    states=[np.load(REC/'initial-state.npz')['qpos'],np.load(OUT/'initial-state.npz')['qpos']]
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',24);images=[]
    for j,(m,q) in enumerate(zip(models,states)):
        d=mujoco.MjData(m);d.qpos[:]=q;mujoco.mj_forward(m,d);m.geom_rgba[m.geom('probe_surface').id,3]=0
        m.vis.global_.offwidth=1400;m.vis.global_.offheight=1000;r=mujoco.Renderer(m,760,700);cam=mujoco.MjvCamera();cam.lookat[:]=[-.007,-.03,.137];cam.distance=.135;cam.azimuth=99;cam.elevation=-10
        r.update_scene(d,cam);r.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=0;im=Image.fromarray(r.render());im.save(OUT/('shape-before.png' if j==0 else 'shape-after.png'));images.append(im)
        if j==1:
            cam.lookat[:]=[.02,.015,.28];cam.distance=.70;cam.elevation=-18;r.update_scene(d,cam);Image.fromarray(r.render()).save(OUT/'whole-plant.png')
        r.close()
    out=Image.new('RGB',(1400,820),'#edf1e7');out.paste(images[0],(0,60));out.paste(images[1],(700,60));draw=ImageDraw.Draw(out)
    draw.text((20,15),'BEFORE / narrow, long taper',font=font,fill='#263f2d');draw.text((720,15),'AFTER / broader shoulders, compact body',font=font,fill='#263f2d');out.save(OUT/'comparison.png')
    print('Rendered shape comparison',flush=True)

if __name__=='__main__':
    import sys
    for name in sys.argv[1:] or ['build','settle','export','render']:globals()[name]()
