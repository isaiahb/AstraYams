"""Parametric tower/lift CAD and separate SO-101/YAM physical workcell layouts.

Photo-informed engineering layout, not a dimensional scan or a learned harvest.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as E

import cadquery as cq
import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
PLANT = ROOT / 'assets/workcells/strawberry-specimen/surface-study/v4'
SO = ROOT / 'assets/robots/so101/upstream'
YAM = ROOT / 'tasks/yam_contact_curriculum/scene.xml'


def vec(x):
    return ' '.join(f'{v:.10g}' for v in np.asarray(x).ravel())


def add(parent, tag, **kw):
    return E.SubElement(parent, tag, {k: str(v) for k, v in kw.items()})


def quat(rot):
    q = rot.as_quat()
    return vec(q[[3, 0, 1, 2]])


def cad_parts(out, cfg):
    folder = out / 'cad'; folder.mkdir(parents=True, exist_ok=True)
    f = cfg['frame']; H=f['height_m']*1000; W=f['width_m']*1000; s=f['profile_m']*1000
    parts = {}
    def profile(length):
        solid = cq.Workplane('XY').rect(s, s).extrude(length)
        solid = solid.cut(cq.Workplane('XY').circle(2.3).extrude(length))
        # Four longitudinal T-slot mouths, kept open in the visual/STEP solid.
        for angle in [0, 90, 180, 270]:
            slot = cq.Workplane('XY').center(0, s/2-1.4).rect(6, 2.9).extrude(length)
            slot = slot.union(cq.Workplane('XY').center(0,s/2-3.1).rect(10,2).extrude(length))
            solid=solid.cut(slot.rotate((0,0,0),(0,0,1),angle))
        return solid
    parts['upright'] = profile(H)
    parts['crossbar'] = profile(W-s)
    parts['guide'] = profile(H-.14*1000)
    parts['foot'] = profile(f['depth_m']*1000)
    parts['carriage_plate'] = cq.Workplane('XY').box(f['carriage_width_m']*1000,8,140).edges('|Y').fillet(6)
    for x in [-190,-80,80,190]:
        for z in [-50,50]:
            hole=cq.Workplane('XZ').center(x,z).circle(3.3).extrude(30,both=True)
            parts['carriage_plate']=parts['carriage_plate'].cut(hole)
    parts['shelf'] = cq.Workplane('XY').box(600,240,8).edges('|Z').fillet(8)
    for x in [-240,-170,170,240]:
        for y in [-60,0,60]:
            parts['shelf']=parts['shelf'].cut(cq.Workplane('XY').center(x,y).circle(3.3).extrude(12,both=True))
    parts['gusset'] = cq.Workplane('XZ').polyline([(0,0),(95,0),(0,95)]).close().extrude(5)
    parts['adapter'] = cq.Workplane('XY').box(120,120,8).edges('|Z').fillet(5)
    for x in [-45,45]:
        for y in [-45,45]:
            parts['adapter']=parts['adapter'].cut(cq.Workplane('XY').center(x,y).circle(3.3).extrude(10,both=True))
    # A genuinely open hollow pocket. Convex collision sectors are generated
    # separately, so its opening is never sealed by a single convex hull.
    outer=cq.Workplane('XY').circle(23).workplane(offset=125).circle(43).loft()
    inner=cq.Workplane('XY').workplane(offset=3).circle(20.4).workplane(offset=125).circle(40.8).loft()
    parts['pocket']=outer.cut(inner).cut(cq.Workplane('XY').circle(14).extrude(5))
    parts['tower_core']=cq.Workplane('XY').circle(45).circle(42).extrude(cfg['tower']['height_m']*1000)
    parts['tank']=cq.Workplane('XY').circle(155).extrude(115).edges('>Z').fillet(7)
    parts['pulley']=cq.Workplane('XY').circle(20).circle(3).extrude(12)
    if cfg['tower'].get('design')=='product_tier':
        from tower_product import cad
        for name in ['pocket','tower_core','tank']:parts.pop(name)
        parts.update(cad(cfg['tower']))
    records=[]
    for name,shape in parts.items():
        assert shape.val().isValid(), name
        cq.exporters.export(shape,str(folder/(name+'.step')))
        cq.exporters.export(shape,str(folder/(name+'.stl')),tolerance=.18,angularTolerance=.12)
        records.append(dict(name=name,step=name+'.step',mesh=name+'.stl',valid=True,
                            solids=len(shape.solids().vals()),volume_mm3=shape.val().Volume()))
    (folder/'parts.json').write_text(json.dumps(records,indent=2)+'\n')
    return parts


def append_robot(root, carriage, kind, side, cfg):
    source = SO/'so101_new_calib.xml' if kind=='so101' else YAM
    arm=E.parse(source).getroot(); prefix=side+'_'
    assets=root.find('asset'); actuators=root.find('actuator')
    if side=='left':
        used={x.get('name') for x in assets}
        for element in arm.find('asset'):
            a=copy.deepcopy(element)
            if 'file' in a.attrib:
                path=(source.parent/('assets' if kind=='so101' else '')/a.get('file')).resolve()
                a.set('file',str(path))
                if a.get('name') is None:a.set('name',path.stem)
            if a.get('name') not in used:
                if a.tag=='material' and kind=='so101' and 'sts3215' not in a.get('name',''):
                    a.set('rgba','.88 .91 .90 1')
                assets.append(a);used.add(a.get('name'))
        for default in arm.findall('default'):root.append(copy.deepcopy(default))
    robot=copy.deepcopy(arm.find('worldbody/body'))
    refkeys={'name','joint','joint1','joint2','body','body1','body2','site','site1','site2'}
    for e in robot.iter():
        for k in refkeys & e.attrib.keys():e.set(k,prefix+e.get(k))
    b=cfg['robots'][kind]; x=(-1 if side=='left' else 1)*b['base_spacing_m']/2
    robot.set('pos',vec([x,b['base_y_m'],.088]))
    robot.set('quat',quat(Rotation.from_euler('z',b['yaw_deg'],degrees=True)))
    # Original official SO base was visual-only. Restore conservative mesh
    # collision volumes on it. All robot/environment and inter-arm pairs count.
    if kind=='so101':
        for e in list(robot.findall('geom')):
            if e.get('class')=='visual':
                c=copy.deepcopy(e);c.set('class','collision');robot.append(c)
    for i,g in enumerate(robot.iter('geom')):
        g.set('name',prefix+'robot_geom_'+str(i))
        if kind=='yam':
            mesh=g.get('mesh','')
            if not g.get('rgba','').endswith(' 0'):
                color='.07 .14 .14 1' if mesh.startswith('tip_') else '.32 .57 .58 1' if mesh in ['link1','link4','link5'] else '.87 .89 .86 1'
                g.set('rgba',color);g.attrib.pop('material',None)
        is_visual=(kind=='so101' and g.get('class')=='visual') or (kind=='yam' and g.get('contype')=='0')
        if is_visual:
            g.set('contype','0');g.set('conaffinity','0');g.set('mass','0')
            if kind=='so101':
                g.set('rgba','.08 .11 .12 1' if 'sts3215' in g.get('mesh','') else '.88 .91 .90 1')
                g.attrib.pop('material',None)
        else:
            # Same-arm non-adjacent contacts are enabled too. Mesh hulls remain
            # conservative; no precision-grasp claim is made for these hulls.
            g.set('contype','2');g.set('conaffinity','7')
            if kind=='so101':g.set('rgba','0 0 0 0');g.attrib.pop('material',None)
    carriage.append(robot)
    for element in arm.find('actuator'):
        if element.get('joint') not in {j.get('name').removeprefix(prefix) for j in robot.iter('joint')}:
            continue
        a=copy.deepcopy(element)
        if kind=='yam':
            # Same finite joint force limits; a position servo provides the
            # commissioning interface above the torque motor, never pose writes.
            a.tag='position';limit=30 if element.get('joint')=='joint7' else 10
            a.set('kp','220' if limit==10 else '1500');a.set('kv','18' if limit==10 else '25')
            a.set('forcerange',vec([-limit,limit]))
            j=next(j for j in robot.iter('joint') if j.get('name')==prefix+element.get('joint'))
            a.set('ctrlrange',j.get('range'))
        a.set('name',prefix+a.get('name'));a.set('joint',prefix+a.get('joint'))
        actuators.append(a)
    for e in arm.findall('equality/joint'):
        c=copy.deepcopy(e)
        for k in ['name','joint1','joint2']:
            if k in c.attrib:c.set(k,prefix+c.get(k))
        root.find('equality').append(c)
    return prefix+'gripperframe' if kind=='so101' else prefix+'tool_site'


def build(out, cfg, kind, parts):
    folder=out/kind;folder.mkdir(parents=True,exist_ok=True)
    root=E.Element('mujoco',model='Tower lift '+kind+' commissioning')
    add(root,'compiler',angle='radian',autolimits='true')
    add(root,'option',timestep='.000125',integrator='implicitfast',gravity='0 0 -9.81',iterations='80')
    add(root,'size',memory='256M')
    vis=add(root,'visual');add(vis,'global',offwidth='1400',offheight='1100')
    add(vis,'headlight',diffuse='.7 .7 .7',ambient='.3 .3 .3',specular='.15 .15 .15')
    assets=add(root,'asset');world=add(root,'worldbody');add(root,'actuator');add(root,'equality');contact=add(root,'contact')
    add(world,'light',pos='1 -2 3',dir='-.2 .5 -1',diffuse='.8 .8 .8')
    add(world,'geom',name='floor',type='plane',size='4 4 .05',rgba='.81 .84 .79 1',contype='4',conaffinity='3')
    for name in parts:
        add(assets,'mesh',name='cad_'+name,file=str((out/'cad'/(name+'.stl')).resolve()),scale='.001 .001 .001')
    assembly=cq.Assembly(name=kind+'_tower_lift')
    colors={'metal':(.67,.72,.73,1),'dark':(.12,.19,.20,1),'white':(.91,.93,.91,1),'accent':(.17,.47,.47,1)}
    def piece(parent,name,part,pos,rot=None,color='metal',box=None,mass=0):
        rot=rot or Rotation.identity();b=add(parent,'body',name=name,pos=vec(pos),quat=quat(rot))
        add(b,'geom',name=name+'_visual',type='mesh',mesh='cad_'+part,rgba=vec(colors[color]),contype='0',conaffinity='0',mass='0')
        if box is not None:
            dims,offset=box
            add(b,'geom',name=name+'_collision',type='box',size=vec(np.array(dims)/2),pos=vec(offset),rgba='0 0 0 0',contype='4',conaffinity='3',mass=str(mass))
        return b
    f=cfg['frame'];W=f['width_m'];H=f['height_m'];s=f['profile_m'];back=f['back_y_m']
    frame=add(world,'body',name='lift_frame')
    for i,x in enumerate([-(W-s)/2,(W-s)/2]):
        piece(frame,'outer_post_'+str(i),'upright',[x,back,0],box=([s,s,H],[0,0,H/2]))
        piece(frame,'foot_'+str(i),'foot',[x,back-.15,s/2],Rotation.from_euler('x',-90,degrees=True),box=([s,s,f['depth_m']],[0,0,f['depth_m']/2]))
    for i,z in enumerate([s/2,H-.11]):
        piece(frame,'crossbar_'+str(i),'crossbar',[-(W-s)/2,back,z],Rotation.from_euler('y',90,degrees=True),box=([s,s,W-s],[0,0,(W-s)/2]))
    for i,x in enumerate([-f['guide_spacing_m']/2,f['guide_spacing_m']/2]):
        piece(frame,'linear_guide_'+str(i),'guide',[x,back+.035,.05],box=([s,s,H-.14],[0,0,(H-.14)/2]))
    # Rear-plane crossing diagonals leave the moving front carriage clear.
    for i,(a,b) in enumerate([([-.50,back-.04,.10],[.50,back-.04,H-.15]),([.50,back-.04,.10],[-.50,back-.04,H-.15])]):
        add(frame,'geom',name='rear_brace_'+str(i),type='capsule',fromto=vec([a,b]),size='.008',rgba=vec(colors['metal']),contype='4',conaffinity='3')
    for i,z in enumerate([.07,H-.15]):
        piece(frame,'drive_pulley_'+str(i),'pulley',[0,back+.06,z],Rotation.from_euler('x',90,degrees=True),color='dark')
    for x in [-.019,.019]:
        add(frame,'geom',name='belt_'+str(x),type='box',pos=vec([x,back+.055,H/2-.04]),size=vec([.002,.004,(H-.20)/2]),rgba=vec(colors['dark']),contype='0',conaffinity='0')
    add(frame,'geom',name='drive_motor',type='box',pos=vec([0,back-.015,H-.11]),size='.043 .036 .043',rgba=vec(colors['dark']),contype='4',conaffinity='3')
    carriage=add(world,'body',name='lift_carriage',pos=vec([0,0,0]))
    add(carriage,'joint',name='lift_z',type='slide',axis='0 0 1',range=vec(f['lift_range_m']),damping='20',armature='.4')
    add(carriage,'inertial',mass='2.8',pos=vec([0,back+.09,.04]),diaginertia='.05 .08 .09')
    piece(carriage,'carriage_backplate','carriage_plate',[0,back+.077,.015],color='dark',box=([.46,.008,.14],[0,0,0]))
    piece(carriage,'arm_shelf','shelf',[0,back+.195,.076],box=([.6,.24,.008],[0,0,0]))
    for i,x in enumerate([-.18,.18]):
        piece(carriage,'shelf_gusset_'+str(i),'gusset',[x,back+.083,-.02],Rotation.from_euler('z',90,degrees=True),color='dark')
    for side,sign in [('left',-1),('right',1)]:
        b=cfg['robots'][kind]
        piece(carriage,side+'_adapter','adapter',[sign*b['base_spacing_m']/2,b['base_y_m'],.084],color='accent')
        append_robot(root,carriage,kind,side,cfg)
    add(root.find('actuator'),'position',name='lift_motor',joint='lift_z',kp='8000',kv='180',forcerange=vec([-f['lift_force_limit_N'],f['lift_force_limit_N']]),ctrlrange=vec(f['lift_range_m']))
    t=cfg['tower']
    if t.get('design')=='product_tier':
        from tower_product import add_tower
        active=add_tower(root,world,assets,cfg,piece,add,vec,quat)
    else:
        t=cfg['tower'];tower=add(world,'body',name='growing_tower',pos=vec(t['center_m']))
        piece(tower,'tower_core','tower_core',[0,0,0],color='white')
        add(tower,'geom',name='core_collision',type='cylinder',size=vec([t['core_radius_m'],t['height_m']/2]),pos=vec([0,0,t['height_m']/2]),rgba='0 0 0 0',contype='4',conaffinity='3')
        piece(tower,'reservoir','tank',[0,0,0],color='white')
        add(tower,'geom',name='reservoir_collision',type='cylinder',size='.155 .0575',pos='0 0 .0575',rgba='0 0 0 0',contype='4',conaffinity='3')
        active=None
        for row in range(t['rows']):
            for k in range(t['pockets_per_row']):
                yaw=120*k+(60 if row%2==0 else 0)
                rot=Rotation.from_euler('z',yaw,degrees=True)*Rotation.from_euler('x',t['pocket_tilt_from_vertical_deg'],degrees=True)
                radial=Rotation.from_euler('z',yaw,degrees=True).apply([0,-.056,0])
                pos=radial+np.array([0,0,t['first_row_base_m']+row*t['row_pitch_m']])
                p=piece(tower,f'pocket_{row}_{k}','pocket',pos,rot,color='white')
                # Hollow, tapered wall represented by 24 convex sectors.
                for j in range(24):
                    angles=np.array([j,j+1])*2*np.pi/24
                    verts=[]
                    for z,outer,inner in [(0,.023,.0204),(.125,.043,.0406)]:
                        for radius in [outer,inner]:
                            for a in angles:verts.append([radius*np.cos(a),radius*np.sin(a),z])
                    nm=f'pocket_wall_mesh_{j}'
                    if row==0 and k==0:add(assets,'mesh',name=nm,vertex=vec(verts))
                    add(p,'geom',name=f'pocket_wall_{row}_{k}_{j}',type='mesh',mesh=nm,rgba='0 0 0 0',contype='4',conaffinity='3')
                    bottom=[]
                    for z in [0,.003]:
                        for radius in [.014,.023]:
                            for a in angles:bottom.append([radius*np.cos(a),radius*np.sin(a),z])
                    nm=f'pocket_bottom_mesh_{j}'
                    if row==0 and k==0:add(assets,'mesh',name=nm,vertex=vec(bottom))
                    add(p,'geom',name=f'pocket_bottom_{row}_{k}_{j}',type='mesh',mesh=nm,rgba='0 0 0 0',contype='4',conaffinity='3')
                if row==t['active_row'] and k==t['active_pocket']:active=p
    assert active is not None
    # Retain the anatomical specimen's masses, joints and material priors. Its
    # previous trough/substrate is replaced by the pocket support geometry.
    plant=E.parse(PLANT/'scene.xml').getroot()
    for a in plant.find('asset'):
        c=copy.deepcopy(a)
        if 'file' in c.attrib:c.set('file',str((PLANT/c.get('file')).resolve()))
        assets.append(c)
    for d in plant.findall('default'):root.append(copy.deepcopy(d))
    crown=copy.deepcopy(plant.find("worldbody/body[@name='crown']"));crown.set('pos',vec([0,0,t.get('crown_seating_offset_m',.128)]))
    for g in crown.iter('geom'):
        if g.get('contype')!='0':g.set('contype','1');g.set('conaffinity','7')
    active.append(crown)
    body_names={b.get('name') for b in crown.iter('body')}
    for e in plant.find('contact'):
        if e.get('body1') in body_names and e.get('body2') in body_names:contact.append(copy.deepcopy(e))
    # Explicit crown/holder interface; roots are inside the pocket. No global
    # plant/environment exclusion is introduced to conceal intersections.
    add(contact,'exclude',body1=active.get('name'),body2='crown')
    E.indent(root);E.ElementTree(root).write(folder/'scene.xml',encoding='unicode')
    m=mujoco.MjModel.from_xml_path(str(folder/'scene.xml'));d=mujoco.MjData(m)
    pm=mujoco.MjModel.from_xml_path(str(PLANT/'scene.xml'));pz=np.load(PLANT/'initial-state.npz')['qpos']
    for j in range(pm.njnt):
        name=pm.joint(j).name
        if name.startswith('probe'):continue
        a=int(m.joint(name).qposadr[0]);b=int(pm.jnt_qposadr[j]);n={0:7,1:4,2:1,3:1}[int(pm.jnt_type[j])]
        d.qpos[a:a+n]=pz[b:b+n]
    d.qpos[m.joint('lift_z').qposadr[0]]=f['carriage_initial_height_m']
    for side in ['left','right']:
        if kind=='so101':
            vals={'shoulder_pan':0,'shoulder_lift':-.6,'elbow_flex':.9,'wrist_flex':.65,'wrist_roll':0,'gripper':.55}
        else:vals={f'joint{i}':v for i,v in enumerate([0,1.05,1.50,0,0,0,-.030,-.030],1)}
        for j,v in vals.items():d.qpos[m.joint(side+'_'+j).qposadr[0]]=v
    mujoco.mj_forward(m,d)
    for i in range(m.nu):d.ctrl[i]=d.qpos[m.jnt_qposadr[m.actuator_trnid[i,0]]]
    np.savez_compressed(folder/'initial.npz',qpos=d.qpos,ctrl=d.ctrl)
    # Export a real STEP assembly of the new support CAD at its initial pose.
    for b in root.iter('body'):
        visual=b.find('geom')
        if visual is None or not visual.get('mesh','').startswith('cad_'):continue
        part=visual.get('mesh')[4:];idx=m.body(b.get('name')).id
        tr=Rotation.from_matrix(d.xmat[idx].reshape(3,3)).as_rotvec();angle=np.linalg.norm(tr)
        axis=tr/angle if angle>1e-9 else np.array([0,0,1])
        shape=parts[part].val().rotate((0,0,0),tuple(axis),np.rad2deg(angle)).translate(tuple(d.xpos[idx]*1000))
        assembly.add(shape,name=b.get('name'))
    # Include frame primitives (braces, belt and motor envelope) in the support
    # STEP too, so the CAD download matches the visible mechanical layout.
    for i in range(m.ngeom):
        name=m.geom(i).name
        if not name.startswith(('rear_brace_', 'belt_', 'drive_motor')):continue
        size=m.geom_size[i]*1000
        if m.geom_type[i]==mujoco.mjtGeom.mjGEOM_BOX:
            shape=cq.Workplane('XY').box(*tuple(2*size)).val()
        elif m.geom_type[i]==mujoco.mjtGeom.mjGEOM_CAPSULE:
            shape=cq.Workplane('XY').circle(size[0]).extrude(2*size[1]).translate((0,0,-size[1]))
            for z in [-size[1],size[1]]:shape=shape.union(cq.Workplane('XY').sphere(size[0]).translate((0,0,z)))
            shape=shape.val()
        else:continue
        rv=Rotation.from_matrix(d.geom_xmat[i].reshape(3,3)).as_rotvec();a=np.linalg.norm(rv)
        axis=rv/a if a>1e-9 else np.array([0,0,1])
        shape=shape.rotate((0,0,0),tuple(axis),np.rad2deg(a)).translate(tuple(d.geom_xpos[i]*1000))
        assembly.add(shape,name=name)
    assembly.save(str(folder/'support-assembly.step'))
    report=dict(embodiment=kind,config=cfg,nq=m.nq,nv=m.nv,actuators=[m.actuator(i).name for i in range(m.nu)],
                inherited_plant_joint_count=sum(not pm.joint(j).name.startswith('probe') for j in range(pm.njnt)),
                plant_source=str(PLANT.relative_to(ROOT)),plant_scene_sha256=hashlib.sha256((PLANT/'scene.xml').read_bytes()).hexdigest(),
                control='Finite-force actuator setpoints; initialization is offline. No PPO or harvest success in this layout.',
                phase='Layout and physical commissioning; stock grippers, tool adapters pending',
                original_yam_runs_preserved=True)
    (folder/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    print(kind,'built',m.nq,'positions,',m.nu,'actuators',flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,default=ROOT/'configs/tower_lift_v1.json')
    p.add_argument('--out',type=Path,default=ROOT/'runs/tower-lift-v1');a=p.parse_args()
    cfg=json.loads(a.config.read_text());out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    (out/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
    parts=cad_parts(out,cfg)
    for kind in ['so101','yam']:build(out,cfg,kind,parts)


if __name__=='__main__':main()
