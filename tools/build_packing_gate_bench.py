"""Build an isolated packing bench with contact-held net and passive release.

Plant and lift coordinates are frozen for this packing experiment. Both robot
arms retain dynamics and finite-torque servo control. No runtime tool weld,
scripted gate angle, berry teleportation, or learned-policy claim is supplied.
"""
from pathlib import Path
import copy
import argparse
import json
import math
import xml.etree.ElementTree as E
import cadquery as cq
import mujoco as mj
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation
from packing_gate_cad import parts
from build_single_pack import vec, add

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'runs/tower-lift-v9'
OUT = RUN / 'gate-bench'


def main(opening_deg=math.degrees(.9),lever_offset_mm=70,paired=False,underslung=False,offset_column=False):
    OUT.mkdir(parents=True, exist_ok=True)
    root = E.parse(RUN / 'so101/scene.xml').getroot()
    old = mj.MjModel.from_xml_path(str(RUN / 'so101/scene.xml'))
    od = mj.MjData(old)
    od.qpos[:] = np.load(ROOT / 'runs/tower-lift-v8/so101/layout/rollout.npz')['qpos'][0]
    mj.mj_forward(old, od)
    frozen = []
    # Preserve the settled pose when eliminating joints from the isolated bench.
    for b in root.iter('body'):
        joints = list(b.findall('joint'))
        if not joints or any(j.get('name', '').startswith(('left_', 'right_')) for j in joints):
            continue
        bi = old.body(b.get('name')).id
        pa = old.body_parentid[bi]
        rp = od.xmat[pa].reshape(3, 3)
        rot = Rotation.from_matrix(rp.T @ od.xmat[bi].reshape(3, 3)).as_quat()
        b.set('pos', vec(rp.T @ (od.xpos[bi]-od.xpos[pa])))
        b.set('quat', vec(rot[[3, 0, 1, 2]]))
        b.attrib.pop('euler', None)
        for j in joints:
            frozen.append(j.get('name')); b.remove(j)
    for e in list(root.find('equality')):
        root.find('equality').remove(e)
    for a in list(root.find('actuator')):
        if not a.get('joint', '').startswith(('left_', 'right_')):
            root.find('actuator').remove(a)
    assets = root.find('asset')
    world = root.find('worldbody')
    # Existing floor mask only admitted original robots. New berry/tool/flex
    # collision groups must also collide with the visible ground.
    ground=root.find(".//geom[@name='floor']")
    ground.set('conaffinity',str(int(ground.get('conaffinity','3')) | 8 | 16 | 32))
    # Isolated packing fixture: remove the growing tower/plant assembly. A
    # duplicate test berry must not be initialized through a frozen crop.
    world.remove(world.find("body[@name='growing_tower']"))
    contact = root.find('contact')
    present = {b.get('name') for b in root.iter('body')}
    for ex in list(contact):
        if ex.tag == 'exclude' and (ex.get('body1') not in present or ex.get('body2') not in present): contact.remove(ex)
    for side in ['left', 'right']:
        # The imported base is welded to the carriage; MuJoCo's automatic
        # parent filter does not cover this static-base/shoulder pair.
        add(contact, 'exclude', body1=side+'_base', body2=side+'_shoulder')
    net = root.find(".//body[@name='right_packing_net']")
    wrist = root.find(".//body[@name='right_gripper']")
    nb = old.body('right_packing_net').id
    net_pose = (od.xpos[nb].copy(), od.xquat[nb].copy())
    wrist.remove(net); world.append(net)
    net.set('pos', vec(net_pose[0])); net.set('quat', vec(net_pose[1]))
    add(net, 'freejoint', name='right_net_free')
    # Replace the old fixed textile/retainer by an actual moving net floor.
    for child in list(net):
        if child.tag == 'body' and any(s in child.get('name','') for s in ['retainer', 'textile', 'screw']):
            net.remove(child)

    # Locate outboard cams from the designed low access pose and gate angle.
    # Their positions are fixed throughout the simulation.
    ref = {'q': [-1.5985743892369286, -1.1059664078107765, .34456105302708984, 1.5580627293335232, 1.5995279184943938]}
    for j, q in zip(['shoulder_pan','shoulder_lift','elbow_flex','wrist_flex','wrist_roll'], ref['q']):
        od.qpos[old.joint('right_'+j).qposadr[0]] = q
    mj.mj_forward(old, od)
    nr = od.xmat[nb].reshape(3,3)
    opening = math.radians(opening_deg)
    lever = np.array([-.040,0,-.005]) + Rotation.from_euler('y',opening).apply([-.040,lever_offset_mm*.001,0])
    cam = od.xpos[nb] + nr @ lever - np.array([0,0,.0085])
    deck_world = od.xpos[old.body('pack_deck').id].copy()
    height = (cam[2] - (deck_world[2]+(0 if underslung else .008)))*1000
    shapes = parts(height-(8 if offset_column else 0),lever_offset_mm,paired)
    instances = []
    for name, shape in shapes.items():
        assert shape.val().isValid(), name
        cq.exporters.export(shape, str(RUN/'cad'/(name+'.step')))
        cq.exporters.export(shape, str(RUN/'cad'/(name+'.stl')), tolerance=.08, angularTolerance=.15)
        add(assets,'mesh',name=name,file=str(RUN/'cad'/(name+'.stl')),scale='.001 .001 .001')

    def piece(parent,name,part,pos=(0,0,0),rot=None,color='.12 .43 .40 1',density=1100):
        rot = Rotation.identity() if rot is None else rot
        q = rot.as_quat(); b = add(parent,'body',name=name,pos=vec(pos),quat=vec(q[[3,0,1,2]]))
        add(b,'geom',name=name+'_visual',type='mesh',mesh=part,rgba=color,mass='0',contype='0',conaffinity='0')
        mesh=trimesh.load(RUN/'cad'/(part+'.stl'),force='mesh');mesh.apply_scale(.001);mesh.density=density
        I=mesh.moment_inertia
        add(b,'inertial',pos=vec(mesh.center_mass),mass=mesh.mass,fullinertia=vec([I[0,0],I[1,1],I[2,2],I[0,1],I[0,2],I[1,2]]))
        instances.append((name,part));return b

    piece(net,'right_gate_fixed_ears','gate_fixed_ears')
    gate=add(net,'body',name='right_net_gate',pos='-.040 0 -.005')
    add(gate,'joint',name='right_gate_hinge',type='hinge',axis='0 1 0',range='0 1.8326',
        stiffness='.006',springref='-2.6666667',damping='.001',solreflimit='.001 1',solimplimit='.99 .999 .0001',armature='.000003',frictionloss='.0002')
    ring=piece(gate,'right_gate_floor','gate_floor_ring')
    piece(gate,'right_gate_shaft','gate_shaft',color='.65 .71 .72 1',density=7800)
    trigger=piece(gate,'right_gate_trigger','gate_trigger_lever',[0,lever_offset_mm*.001,0])
    for y in [-.028,.028]:
        piece(net,'right_gate_bearing_'+str(y),'gate_bearing',[-.040,y,-.005],color='.65 .71 .72 1',density=7800)
    deck=root.find(".//body[@name='pack_deck']")
    footpos=cam-deck_world;footpos[0]-=.020 if offset_column else (.033 if lever_offset_mm>70 else .015);footpos[2]=-.004 if underslung else .004
    piece(deck,'pack_gate_roller_foot','gate_roller_foot',footpos,density=2700)
    postpos=cam-deck_world;postpos[2]=0 if underslung else .008
    if offset_column:postpos[:2]+=(nr@np.array([-.012,0,0]))[:2]
    piece(deck,'pack_gate_roller_post','gate_roller_post',postpos,density=2700)
    roller=piece(deck,'pack_gate_roller','gate_roller',cam-deck_world,Rotation.from_matrix(nr),color='.55 .62 .63 1')
    add(roller,'joint',name='roller_spin',type='hinge',axis='0 1 0',damping='.00002',armature='.0000001')
    if offset_column:
        piece(deck,'pack_gate_fork','gate_roller_fork',cam-deck_world,Rotation.from_matrix(nr),density=2700)
        piece(deck,'pack_gate_axle','gate_roller_axle',cam-deck_world,Rotation.from_matrix(nr),color='.65 .71 .72 1',density=7800)
    triggers=[trigger]
    mounting_holes=[(footpos[0]-.020,footpos[1]+y) for y in [-.010,.010]]
    if paired:
        triggers.append(piece(gate,'right_gate_trigger_opposite','gate_trigger_lever',[0,-lever_offset_mm*.001,0]))
        opposite_cam=cam+nr@np.array([0,-2*lever_offset_mm*.001,0])
        opposite_foot=opposite_cam-deck_world;opposite_foot[0]+=.033;opposite_foot[2]=-.004 if underslung else .004
        piece(deck,'pack_gate_roller_foot_opposite','gate_roller_offset_foot' if offset_column else 'gate_roller_foot',opposite_foot,Rotation.identity() if offset_column else Rotation.from_euler('z',180,degrees=True),density=2700)
        opposite_post=opposite_cam-deck_world;opposite_post[2]=0 if underslung else .008
        if offset_column:opposite_post[:2]+=(nr@np.array([-.012,0,0]))[:2]
        piece(deck,'pack_gate_roller_post_opposite','gate_roller_offset_post' if offset_column else 'gate_roller_post',opposite_post,density=2700)
        roller2=piece(deck,'pack_gate_roller_opposite','gate_roller',opposite_cam-deck_world,Rotation.from_matrix(nr),color='.55 .62 .63 1')
        add(roller2,'joint',name='roller_spin_opposite',type='hinge',axis='0 1 0',damping='.00002',armature='.0000001')
        if offset_column:
            piece(deck,'pack_gate_fork_opposite','gate_roller_fork',opposite_cam-deck_world,Rotation.from_matrix(nr),density=2700)
            piece(deck,'pack_gate_axle_opposite','gate_roller_axle',opposite_cam-deck_world,Rotation.from_matrix(nr),color='.65 .71 .72 1',density=7800)
        mounting_holes.extend((opposite_foot[0]+.020,opposite_foot[1]+y) for y in [-.010,.010])
    if underslung:
        deck_shape=cq.importers.importStep(str(RUN/'cad/pack_deck.step'))
        for k,(x,y) in enumerate(mounting_holes):
            bore=cq.Workplane('XY').center(x*1000,y*1000).circle(2.1).extrude(5)
            countersink=cq.Workplane('XY').workplane(offset=1.9).center(x*1000,y*1000).circle(2.1).workplane(offset=2.1).circle(4.2).loft()
            deck_shape=deck_shape.cut(bore).cut(countersink)
            piece(deck,'pack_gate_mount_screw_'+str(k),'gate_mount_screw',[x,y,0],color='.65 .71 .72 1',density=7800)
            piece(deck,'pack_gate_mount_nut_'+str(k),'gate_mount_nut',[x,y,0],color='.65 .71 .72 1',density=7800)
        cq.exporters.export(deck_shape,str(RUN/'cad/pack_deck.step'))
        cq.exporters.export(deck_shape,str(RUN/'cad/pack_deck.stl'))
        dm=trimesh.load(RUN/'cad/pack_deck.stl',force='mesh');dm.apply_scale(.001);dm.density=2700;di=dm.moment_inertia
        inertial=deck.find('inertial');inertial.set('mass',str(dm.mass));inertial.set('pos',vec(dm.center_mass));inertial.set('fullinertia',vec([di[0,0],di[1,1],di[2,2],di[0,1],di[0,2],di[1,2]]))

    # Actual woven grid with shared crossing nodes. Pinned perimeter vertices
    # follow the gate; moving nodes carry the 1.5 g textile mass.
    points=[];edges=[];interior={};boundary=[];radius=.035
    values=np.arange(-.028,.0281,.007)
    def point(x,y,pinned=False):
        z=.002-.016*(1-(x*x+y*y)/radius**2)
        points.append([.040+x,y,z]);boundary.append(pinned);return len(points)-1
    for i,x in enumerate(values):
        for j,y in enumerate(values):
            if x*x+y*y < (.034**2):interior[(i,j)]=point(x,y)
    for axis in [0,1]:
        for row,a in enumerate(values):
            extent=math.sqrt(radius**2-a*a)
            start=point(-extent,a,True) if axis==0 else point(a,-extent,True)
            end=point(extent,a,True) if axis==0 else point(a,extent,True)
            indices=[interior[(k,row) if axis==0 else (row,k)] for k in range(len(values)) if ((k,row) if axis==0 else (row,k)) in interior]
            line=[start]+indices+[end]
            edges.extend(zip(line[:-1],line[1:]))
    count=sum(not b for b in boundary); bodies=[];vertices=[]
    for i,(p,pinned) in enumerate(zip(points,boundary)):
        if pinned:bodies.append('right_net_gate');vertices.append(p);continue
        name=f'packing_fiber_{i}'
        b=add(gate,'body',name=name,pos=vec(p))
        add(b,'inertial',mass=.0015/count,pos='0 0 0',diaginertia='1e-11 1e-11 1e-11')
        for k in range(3):add(b,'joint',name=f'{name}_{k}',type='slide',axis=vec(np.eye(3)[k]),damping='.00001')
        bodies.append(name);vertices.append([0,0,0])
    deform=root.find('deformable')
    if deform is None:deform=add(root,'deformable')
    flex=add(deform,'flex',name='packing_textile',dim='1',radius='.00035',body=' '.join(bodies),
        vertex=vec(vertices),element=' '.join(map(str,np.array(edges).ravel())),rgba='.47 .49 .39 1')
    add(flex,'edge',stiffness='60',damping='.015')
    add(flex,'contact',priority='2',margin='.0002',contype='16',conaffinity='98',
        friction='.5 .001 .0001',solref='.0005 1',solimp='.999 .999 .0001',selfcollide='none')

    # Reuse the existing detailed strawberry's actual skin/calyx/achene meshes.
    berry=add(world,'body',name='packing_berry',pos=vec(net_pose[0]+[0,0,.060]))
    add(berry,'freejoint',name='packing_berry_free')
    skinasset=root.find("asset/mesh[@name='fruit_detail_primary_skin']")
    skin=trimesh.load(skinasset.get('file'),force='mesh').convex_hull
    skin.density=.018/skin.volume
    I=skin.moment_inertia
    add(berry,'inertial',mass='.018',pos=vec(skin.center_mass),fullinertia=vec([I[0,0],I[1,1],I[2,2],I[0,1],I[0,2],I[1,2]]))
    for kind,color in [('skin','.63 .035 .019 1'),('achenes','.58 .38 .105 1'),('calyx','.16 .31 .055 1')]:
        add(berry,'geom',name='packing_berry_'+kind,type='mesh',mesh='fruit_detail_primary_'+kind,mass='0',rgba=color,contype='0',conaffinity='0')
    add(berry,'geom',name='packing_berry_contact',type='mesh',mesh='fruit_detail_primary_skin',mass='0',rgba='0 0 0 0',
        contype='32',conaffinity='91',friction='.5 .001 .0001',solref='.003 1',solimp='.95 .99 .0005')

    # Use decomposition for the two jaw meshes and fixed ring/handle, so an
    # invisible single convex hull does not fill the jaw or net openings.
    manifest=json.loads((ROOT/'runs/tower-lift-v8/contact-meshes/manifest.json').read_text())
    for record in manifest['records']:
        name=record['name']
        if name=='pack_net_retainer':continue
        for k,path in enumerate(record['parts']):
            add(assets,'mesh',name='contact_'+name+'_'+str(k),file=str(ROOT/'runs/tower-lift-v8/contact-meshes'/path))
        for body in list(root.iter('body')):
            for geom in list(body.findall('geom')):
                if geom.get('mesh')!=name:continue
                if name!='pack_net_frame' and geom.get('contype','0')=='0':continue
                if name=='pack_net_frame' and geom.get('contype','0')!='0':continue
                if name!='pack_net_frame':body.remove(geom)
                for k,path in enumerate(record['parts']):
                    g=copy.deepcopy(geom);g.set('mesh','contact_'+name+'_'+str(k));g.set('name',(geom.get('name') or name)+'_piece_'+str(k));g.set('rgba','0 0 0 0');g.set('mass','0')
                    g.set('contype','8' if name=='pack_net_frame' else '2');g.set('conaffinity','99' if name=='pack_net_frame' else '127')
                    g.set('friction','.6 .001 .0001');g.set('solref','.001 1');body.append(g)
    # Gate ring: 16 convex arc segments, plus its actual lever/shaft envelope.
    for k in range(16):
        theta=np.linspace(k*2*np.pi/16,(k+1)*2*np.pi/16,5)
        vertices=[[.040+r*np.cos(a),r*np.sin(a),z] for r in [.0345,.0375] for a in theta for z in [0,.002]]
        hull=trimesh.convex.convex_hull(vertices);path=OUT/f'gate-ring-contact-{k}.stl';hull.export(path)
        add(assets,'mesh',name=f'gate_ring_contact_{k}',file=str(path))
        add(gate,'geom',name=f'gate_ring_contact_{k}',type='mesh',mesh=f'gate_ring_contact_{k}',mass='0',rgba='0 0 0 0',contype='8',conaffinity='99',friction='.5 .001 .0001',solref='.001 1')
    for k,trigger_body in enumerate(triggers):
        add(trigger_body,'geom',name='gate_trigger_contact'+('_opposite' if k else ''),type='mesh',mesh='gate_trigger_lever',mass='0',rgba='0 0 0 0',contype='8',conaffinity='99',friction='.2 .001 .0001',solref='.001 1')
    # Commission fixture contacts. The container stays hollow: four thin
    # tapered walls and a bottom, rather than one filled convex hull.
    for b in root.iter('body'):
        name=b.get('name','')
        if not name.startswith('pack_') or name in ['pack_clamshell','pack_carrier']:continue
        if offset_column and name=='pack_gate_roller_post_opposite':
            stem_height=height*.001-.016
            for k,(pos,size) in enumerate([([0,.025,stem_height/2],[.005,.005,stem_height/2]),([0,.0125,height*.001-.012],[.005,.0175,.004])]):
                add(b,'geom',name=name+'_contact_'+str(k),type='box',pos=vec(pos),size=vec(size),mass='0',rgba='0 0 0 0',contype='64',conaffinity='58',friction='.5 .001 .0001',solref='.002 1')
            continue
        if name.startswith('pack_gate_fork'):
            # Three pieces retain the U opening; a convex hull would fill it.
            for k,(pos,size) in enumerate([([-.012,0,-.010],[.005,.0155,.002]),([-.006,-.014,-.0045],[.011,.0015,.0075]),([-.006,.014,-.0045],[.011,.0015,.0075])]):
                add(b,'geom',name=name+'_contact_'+str(k),type='box',pos=vec(pos),size=vec(size),mass='0',rgba='0 0 0 0',contype='64',conaffinity='58',friction='.5 .001 .0001',solref='.002 1')
            continue
        for g in list(b.findall('geom')):
            if g.get('rgba','').endswith(' 0'):continue
            c=copy.deepcopy(g);c.set('name',g.get('name','')+'_contact');c.set('rgba','0 0 0 0');c.set('mass','0');c.set('contype','64');c.set('conaffinity','58');c.set('friction','.5 .001 .0001');c.set('solref','.002 1');b.append(c)
    carrier=root.find(".//body[@name='pack_carrier']")
    # Preserve the hollow carrier. A single convex mesh falsely fills its
    # 8 mm deep recess. Slot openings in the covered base remain simplified.
    for name,pos,size in [('base',[0,0,.0015],[.0695,.104,.0015]),
            ('left',[-.067,0,.007],[.0025,.104,.004]),('right',[.067,0,.007],[.0025,.104,.004]),
            ('back',[0,-.1015,.007],[.0645,.0025,.004]),('front',[0,.1015,.007],[.0645,.0025,.004])]:
        add(carrier,'geom',name='carrier_'+name+'_contact',type='box',pos=vec(pos),size=vec(size),mass='0',rgba='0 0 0 0',contype='64',conaffinity='58',friction='.5 .001 .0001',solref='.002 1')
    box=root.find(".//body[@name='pack_clamshell']")
    for axis in [0,1]:
        for sign in [-1,1]:
            v=[]
            for z in [0,.076]:
                hx=.054+.0075*z/.076;hy=.084+.009*z/.076
                for t in [0,.0007]:
                    for side in [-1,1]:
                        v.append([sign*(hx-t),side*hy,z] if axis==0 else [side*hx,sign*(hy-t),z])
            path=OUT/f'container-wall-{axis}-{sign}.stl';trimesh.convex.convex_hull(v).export(path)
            name=f'container_wall_{axis}_{sign}';add(assets,'mesh',name=name,file=str(path));add(box,'geom',name=name,type='mesh',mesh=name,mass='0',rgba='0 0 0 0',contype='64',conaffinity='58',friction='.4 .001 .0001',solref='.003 1')
    add(box,'geom',name='container_floor',type='box',size='.054 .084 .00035',pos='0 0 .00035',mass='0',rgba='0 0 0 0',contype='64',conaffinity='58',friction='.4 .001 .0001',solref='.003 1')
    root.find('option').set('timestep','.00025');root.find('option').set('noslip_iterations','3')
    root.find('option').set('iterations','60')
    for a in root.find('actuator'):
        if a.get('name')=='right_gripper':a.set('forcerange','-.35 .35')
    E.indent(root);E.ElementTree(root).write(OUT/'scene.xml',encoding='unicode')
    m=mj.MjModel.from_xml_path(str(OUT/'scene.xml'));d=mj.MjData(m)
    sourceq=np.load(ROOT/'runs/tower-lift-v8/so101/layout/rollout.npz')['qpos'][0]
    for j in range(old.njnt):
        name=old.joint(j).name;dest=mj.mj_name2id(m,mj.mjtObj.mjOBJ_JOINT,name)
        if dest<0:continue
        count={0:7,1:4,2:1,3:1}[int(old.jnt_type[j])]
        d.qpos[m.jnt_qposadr[dest]:m.jnt_qposadr[dest]+count]=sourceq[old.jnt_qposadr[j]:old.jnt_qposadr[j]+count]
    for i in range(m.nu):d.ctrl[i]=d.qpos[m.jnt_qposadr[m.actuator_trnid[i,0]]]
    d.ctrl[m.actuator('right_gripper').id]=-.015
    mj.mj_forward(m,d)
    np.savez_compressed(OUT/'initial.npz',qpos=d.qpos,ctrl=d.ctrl)
    report=dict(scope=__doc__,frozen_joints=frozen,nq=m.nq,nv=m.nv,net_free_joint='right_net_free',
        gate_joint='right_gate_hinge',spring_stiffness_Nm_per_rad=.006,spring_reference_rad=-2.6666667,
        textile_mass_kg=.0015,textile_edge_stiffness_N_per_m=60,textile_edge_damping_Ns_per_m=.015,
        berry_mass_kg=.018,gripper_torque_cap_Nm=.35,cam_center_m=cam.tolist(),
        lever_offset_mm=lever_offset_mm,paired_rollers=paired,underslung_roller_feet=underslung,offset_second_column=offset_column,mounting_holes_deck_m=mounting_holes if underslung else [],cam_design_opening_deg=opening_deg,new_cad_instances=instances,low_access_joint_pose=ref['q'],
        calibration='Uncalibrated friction, spring and textile priors. No bruise-safety claim. No full harvesting claim.')
    (OUT/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['frozen_joints','new_cad_instances']},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,default=RUN);p.add_argument('--opening-deg',type=float,default=math.degrees(.9));p.add_argument('--lever-offset-mm',type=float,default=70);p.add_argument('--paired-rollers',action='store_true');p.add_argument('--underslung-feet',action='store_true');p.add_argument('--offset-second-column',action='store_true');a=p.parse_args();RUN=a.run.resolve();OUT=RUN/'gate-bench';main(a.opening_deg,a.lever_offset_mm,a.paired_rollers,a.underslung_feet,a.offset_second_column)
