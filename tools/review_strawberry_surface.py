"""Upgrade the shared full-plant surface without changing plant physics.

Uses the complete recovery-v2 model and its recorded relaxing-material trial.
Includes a fresh paired physics check from a loaded contact state.
"""
from pathlib import Path
import json,hashlib,copy
import xml.etree.ElementTree as E
import numpy as np,mujoco,trimesh
from PIL import Image,ImageDraw,ImageFont
from strawberry_surface import enrich
from study_strawberry_recovery import MaxwellArm

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/workcells/strawberry-specimen/surface-study/v1'
BASE=ROOT/'assets/workcells/strawberry-specimen/support-study/v2'
REC=ROOT/'assets/workcells/strawberry-specimen/recovery-study/v2'
CAD=ROOT/'cad/harvest-tools/rev-b'
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def build():
    OUT.mkdir(exist_ok=True,parents=True);root=E.parse(BASE/'scene.xml').getroot()
    spec=json.loads((ROOT/'assets/workcells/strawberry-specimen/fruit-study/v14/reference-graph.json').read_text())
    reports=enrich(root,spec,OUT/'meshes');E.indent(root);E.ElementTree(root).write(OUT/'scene.xml',encoding='unicode')
    models=[mujoco.MjModel.from_xml_path(str(p/'scene.xml')) for p in [BASE,OUT]]
    a,b=models;checks={}
    for attr in ['body_mass','body_inertia','body_ipos','body_iquat','body_pos','body_quat','body_parentid','jnt_type','jnt_pos','jnt_axis','jnt_stiffness','dof_damping','dof_armature','qpos0','qpos_spring','actuator_gainprm','actuator_biasprm','actuator_forcerange','exclude_signature']:
        x,y=getattr(a,attr),getattr(b,attr);checks[attr]=dict(shape=list(x.shape),max_error=float(np.max(abs(x.astype(float)-y.astype(float)))) if x.size else 0.)
        assert np.array_equal(x,y),attr
    # Compare by name: appended visual geoms reorder geom indices.
    geom_checks=['geom_type','geom_contype','geom_conaffinity','geom_friction','geom_solref','geom_solimp','geom_size','geom_pos','geom_quat']
    for i in range(a.ngeom):
        name=a.geom(i).name
        if not name:continue
        j=b.geom(name).id
        for attr in geom_checks:assert np.array_equal(getattr(a,attr)[i],getattr(b,attr)[j]),(name,attr)
    assert a.nq==b.nq and a.nv==b.nv and a.nbody==b.nbody
    assert a.opt.timestep==b.opt.timestep
    old_active=int(np.sum((a.geom_contype!=0)|(a.geom_conaffinity!=0)));new_active=int(np.sum((b.geom_contype!=0)|(b.geom_conaffinity!=0)))
    assert old_active==new_active
    dump(OUT/'build-audit.json',dict(full_plant_qpos=a.nq,full_plant_dof=a.nv,body_count=a.nbody,joint_count=a.njnt,
         original_collision_geom_count=old_active,new_collision_geom_count=new_active,exact_physics_arrays=checks,
         original_scene_sha256=sha(BASE/'scene.xml'),new_scene_sha256=sha(OUT/'scene.xml'),
         recovery_initial_state_sha256=sha(REC/'initial-state.npz'),surface=reports,
         scope='Full plant retained; no frozen foliage. Surface is visual only; original collision, COM/inertia, springs, damping and recovery laws retained.'))
    print('Full-plant physics arrays match exactly',a.nq,a.nv,flush=True)

def physics_check():
    z=np.load(REC/'relaxing-1s/rollout.npz');i=int(np.argmin(abs(z['t']-5.5)));starts=z['qpos'][i]
    commands=np.load(BASE/'support/commands.npz')['command_world'];proto=json.loads((BASE/'protocol.json').read_text())
    ff=np.array(proto['gravity_feedforward_joint_m']);trajectories=[];forces=[]
    for path in [BASE,OUT]:
        mujoco.set_mjcb_passive(None);m=mujoco.MjModel.from_xml_path(str(path/'scene.xml'));d=mujoco.MjData(m)
        d.qpos[:]=starts;d.qvel[:]=z['qvel'][i];pg=m.geom('probe_surface').id;m.geom_contype[pg]=m.geom_conaffinity[pg]=0
        arm=MaxwellArm(m,d.qpos);arm.qv[:]=z['maxwell_qv'][i];mujoco.set_mjcb_passive(arm.callback)
        motors=[m.actuator(f'support_{ax}_motor').id for ax in 'xyz'];samples=[];contact=[]
        try:
            for k in range(round(.25/m.opt.timestep)+1):
                t=float(z['t'][i])+k*m.opt.timestep
                d.ctrl[motors]=commands[min(round(t/.01),len(commands)-1)]-np.array([-.11,-.095,.10])-np.array([0,.06,0])+ff
                mujoco.mj_forward(m,d)
                if k%40==0:samples.append(d.qpos.copy());contact.append(d.sensor('stem_force').data.copy())
                mujoco.mj_step(m,d);arm.advance(d.qpos,m.opt.timestep)
            assert not any(w.number for w in d.warning)
        finally:mujoco.set_mjcb_passive(None)
        trajectories.append(np.array(samples));forces.append(np.array(contact))
    qe=float(abs(trajectories[0]-trajectories[1]).max());fe=float(abs(forces[0]-forces[1]).max())
    dump(OUT/'physics-regression.json',dict(duration_s=.25,starting_recorded_time_s=float(z['t'][i]),
          material='Same rotational Maxwell arm, including saved internal state',max_generalized_position_difference=qe,
          max_stem_force_difference_n=fe,passed=qe<1e-10 and fe<1e-9,
          scope='Fresh paired contact-state continuation; verifies appearance did not alter dynamics. Not biological calibration.'))
    assert qe<1e-10 and fe<1e-9,(qe,fe)
    print('Paired dynamics difference',qe,fe,flush=True)

def export():
    # Reuse the exact existing full-plant pose recording, replacing only fruit visuals.
    r=json.loads((REC/'relaxing-1s/replay.json').read_text());m=mujoco.MjModel.from_xml_path(str(OUT/'scene.xml'));d=mujoco.MjData(m)
    initial=np.load(REC/'initial-state.npz');d.qpos[:]=initial['qpos'];mujoco.mj_forward(m,d)
    r['objects']=[o for o in r['objects'] if not o['body'].startswith('fruit_')]
    fruit_objects=[]
    for i in range(m.ngeom):
        if not (m.geom(i).name or '').startswith('fruit_detail_'):continue
        a=m.geom_dataid[i];v=m.mesh_vert[m.mesh_vertadr[a]:m.mesh_vertadr[a]+m.mesh_vertnum[a]]
        f=m.mesh_face[m.mesh_faceadr[a]:m.mesh_faceadr[a]+m.mesh_facenum[a]]
        geo=trimesh.Trimesh(v,f,process=False);rot=np.zeros(9);mujoco.mju_quat2Mat(rot,m.geom_quat[i])
        geo.vertices=geo.vertices@rot.reshape(3,3).T+m.geom_pos[i];trimesh.repair.fix_normals(geo,multibody=True)
        name=m.geom(i).name;path=OUT/'meshes'/(name+'-local.stl');geo.export(path);rgb=[round(c*255) for c in m.geom_rgba[i,:3]]
        fruit_objects.append(dict(name=name,body=m.body(m.geom_bodyid[i]).name,color=rgb[0]*65536+rgb[1]*256+rgb[2],mesh_path=str(path.relative_to(ROOT))))
    r['objects']+=fruit_objects;r['scope']='Original full-plant recovery-v2 recorded dynamics, shared detailed berries. Maxwell law remains an uncalibrated hypothesis. No harvest claim.'
    (OUT/'replay.json').write_text(json.dumps(r,separators=(',',':')))
    # CAD context is the same whole plant at its shared settled pose. No severed
    # fruit, fake straight stem or independent berry orientation is introduced.
    ids={m.body(n).id for n in ['probe','stage_frame','support_z','support_y','support_x']}
    objs=[]
    for o in r['objects']:
        bid=m.body(o['body']).id
        if bid in ids:continue
        objs.append(dict(o,position=d.xpos[bid].tolist(),quaternion=d.xquat[bid][[1,2,3,0]].tolist()))
    # Keep gravity vertical. Translate the entire specimen, not individual organs.
    skin=trimesh.load(OUT/'meshes/fruit_detail_primary_skin-local.stl',force='mesh');b=m.body('fruit_primary').id
    points=skin.vertices@d.xmat[b].reshape(3,3).T+d.xpos[b]
    target=d.xipos[b];shift=np.array([-target[0],-target[1],.012-points[:,2].min()])
    context=dict(objects=objs,world_to_cad_translation_mm=(shift*1000).tolist(),
       source_scene=str((OUT/'scene.xml').relative_to(ROOT)),source_pose='recovery-study/v2/initial-state.npz',
       fruit_attachment_cad_mm=((d.xpos[b]+shift)*1000).tolist(),
       scope='Whole-plant static placement from the full physics model. CAD tools remain mechanism concepts, not an executed harvest.')
    dump(OUT/'cad-context.json',context)
    # All future CAD refreshes consume this shared specimen context.
    dump(CAD/'specimen-source.json',dict(context='/'+str((OUT/'cad-context.json').relative_to(ROOT)),physics_review='/'+str((OUT/'index.html').relative_to(ROOT)),
          source_sha256=sha(OUT/'scene.xml'),scope=context['scope']))
    print('Exported shared full plant,',len(objs),'CAD-context meshes',flush=True)

def render():
    m=mujoco.MjModel.from_xml_path(str(OUT/'scene.xml'));old=mujoco.MjModel.from_xml_path(str(BASE/'scene.xml'))
    z=np.load(REC/'relaxing-1s/rollout.npz');font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',22)
    def shot(model,name,close=True,index=0):
        d=mujoco.MjData(model);d.qpos[:]=z['qpos'][index];mujoco.mj_forward(model,d)
        model.geom_rgba[model.geom('probe_surface').id,3]=0
        model.vis.global_.offwidth=1500;model.vis.global_.offheight=1000
        r=mujoco.Renderer(model,900,1400);cam=mujoco.MjvCamera();b=model.body('fruit_primary').id
        cam.lookat[:]=d.xipos[b] if close else [.02,.02,.28]
        cam.distance=.112 if close else .68;cam.azimuth=104;cam.elevation=-14 if close else -18
        r.update_scene(d,cam)
        if close:r.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=0
        im=Image.fromarray(r.render());r.close();im.save(OUT/(name+'.png'));return im
    before=shot(old,'berry-before');after=shot(m,'berry-after');shot(m,'whole-plant',False)
    sheet=Image.new('RGB',(1400,510),'#edf1e7');sheet.paste(before.resize((700,450)),(0,60));sheet.paste(after.resize((700,450)),(700,60))
    dr=ImageDraw.Draw(sheet);dr.text((20,16),'BEFORE / original specimen berry',font=font,fill='#2a3f2a');dr.text((720,16),'AFTER / shared surface, same physics',font=font,fill='#2a3f2a');sheet.save(OUT/'comparison.png')
    print('Rendered berry comparison and full plant',flush=True)

if __name__=='__main__':
    build();physics_check();export();render()
