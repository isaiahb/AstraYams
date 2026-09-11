"""Add supported Concept-A packing CAD to the preserved V7 robot layout.

This is an offline assembly/reach study. The net is a fixed CAD fit at the jaw,
not a demonstrated friction grasp; textile, latching and packing are untrained.
"""
import argparse,copy,json,shutil,math
from pathlib import Path
import xml.etree.ElementTree as E
import cadquery as cq
import mujoco
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation
from packing_shelf_cad import parts

ROOT=Path(__file__).resolve().parents[1]

def vec(v):return ' '.join(f'{x:.10g}' for x in np.asarray(v).ravel())
def add(p,t,**kw):return E.SubElement(p,t,{k:str(v) for k,v in kw.items()})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'runs/tower-lift-v8');args=parser.parse_args()
    out=args.out.resolve();source=ROOT/'runs/tower-lift-v7';folder=out/'so101'
    folder.mkdir(parents=True,exist_ok=True);shutil.copytree(source/'cad',out/'cad',dirs_exist_ok=True)
    shutil.copytree(source/'references',out/'references',dirs_exist_ok=True)
    shutil.copytree(source/'end-effector',out/'end-effector',dirs_exist_ok=True)
    cfg=json.loads((source/'config.json').read_text());cfg['revision']='v8-single-clamshell-shelf'
    cfg['packing']=dict(concept='A',container_count=1,shelf_center_m=[-.205,.171,-.112],container_envelope_mm=[123,186,81.8],
        container_source='https://pactivevergreen.com/products/yyy9772',container_cad='Approximate envelope, not supplier CAD',
        carrier_size_mm=[139,208,11],lid_open_deg=95,loaded_container_handling='Shelf and future supported dock only; arms never lift filled containers',
        status='CAD assembly and offline reach checks; no packing, net grasp, textile, gate or exchange physics validation')
    (out/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
    shapes=parts();records=json.loads((source/'cad/parts.json').read_text())
    for name,shape in shapes.items():
        assert shape.val().isValid(),name
        cq.exporters.export(shape,str(out/'cad'/(name+'.step')))
        cq.exporters.export(shape,str(out/'cad'/(name+'.stl')),tolerance=.35 if name=='pack_net_textile' else .10,angularTolerance=.50 if name=='pack_net_textile' else .10)
        records.append(dict(name=name,step=name+'.step',mesh=name+'.stl',valid=True,solids=len(shape.solids().vals()),volume_mm3=shape.val().Volume()))
    (out/'cad/parts.json').write_text(json.dumps(records,indent=2)+'\n')
    root=E.parse(source/'so101/scene.xml').getroot();assets=root.find('asset')
    lower=root.find(".//body[@name='lower_lift_carriage']")
    for x in [-.102,-.085]:
        for z in [-.04,.04]:
            # The new through-bolt replaces the old short faceplate bolt.
            old=lower.find(f"body[@name='lower_plate_bolt_{x}_{z}']")
            if old is not None:lower.remove(old)
    palette={'teal':(.12,.43,.40,1),'dark':(.10,.16,.17,1),'metal':(.65,.71,.72,1),'clear':(.65,.83,.89,.24),'mesh':(.47,.49,.39,1),'soft':(.74,.78,.72,1)}
    for name in shapes:add(assets,'mesh',name=name,file=str(out/'cad'/(name+'.stl')),scale='.001 .001 .001')
    # New CAD pieces each get an explicit density prior and an inertial tensor.
    # Contact solids remain uncommissioned for this static fit review.
    instances=[]
    def piece(parent,name,part,pos=(0,0,0),rot=None,color='teal',density=1100):
        rot=rot or Rotation.identity();q=rot.as_quat();b=add(parent,'body',name=name,pos=vec(pos),quat=vec(q[[3,0,1,2]]))
        add(b,'geom',name=name+'_visual',type='mesh',mesh=part,rgba=vec(palette[color]),mass='0',contype='0',conaffinity='0')
        mesh=trimesh.load(out/'cad'/(part+'.stl'),force='mesh');mesh.apply_scale(.001);mesh.density=density
        mass=mesh.mass;I=mesh.moment_inertia
        if mass>0:
            add(b,'inertial',pos=vec(mesh.center_mass),mass=mass,fullinertia=vec([I[0,0],I[1,1],I[2,2],I[0,1],I[0,2],I[1,2]]))
        instances.append((name,part));return b
    piece(lower,'pack_mount_plate','pack_mount_plate',density=2700)
    for k,x in enumerate([-.283,-.130]):piece(lower,'pack_web_'+str(k),'pack_web',[x,0,0],density=2700)
    deck=piece(lower,'pack_deck','pack_deck',[-.205,.171,-.112],density=2700)
    for k,x in enumerate([-.072,.072]):piece(deck,'pack_guide_'+str(k),'pack_guide',[x,0,.004],color='dark')
    piece(deck,'pack_rear_stop','pack_rear_stop',[0,-.112,.004],color='dark')
    piece(deck,'pack_latch','pack_latch',[0,.119,.0115],color='dark')
    piece(deck,'pack_latch_pin','pack_latch_pin',[-.009,.119,.006],Rotation.from_euler('y',90,degrees=True),color='metal',density=7800)
    carrier=piece(deck,'pack_carrier','pack_carrier',[0,0,.004],color='dark')
    piece(carrier,'pack_liner','pack_liner',[0,0,.003],color='soft',density=300)
    box=piece(carrier,'pack_clamshell','pack_clamshell',[0,0,.0045],color='clear',density=1380)
    lid=piece(box,'pack_lid','pack_lid',[-.063,0,.078],Rotation.from_euler('y',-95,degrees=True),color='clear',density=1380)
    for k,y in enumerate([-.065,.065]):piece(box,'pack_hinge_'+str(k),'pack_hinge',[-.063,y,.078],Rotation.from_euler('x',90,degrees=True),color='clear',density=1380)
    piece(carrier,'pack_lid_clip','pack_lid_clip',[-.064,-.080,.072],color='teal')
    piece(lower,'pack_net_dock','pack_net_dock',[-.205,.079,-.159],color='teal')
    piece(lower,'pack_dock_support','pack_dock_support',[-.205,.062,-.127],color='teal',density=2700)
    # Four explicit mounting bolts enter existing holes; grip length/grade and
    # receiver thread engagement need hardware verification.
    for x in [-.102,-.085]:
        for z in [-.04,.04]:
            piece(lower,f'pack_bolt_{x}_{z}','pack_m5_bolt',[x,.028,z],Rotation.from_euler('x',-90,degrees=True),color='metal',density=7800)
            piece(lower,f'pack_washer_{x}_{z}','pack_washer',[x,.046,z],Rotation.from_euler('x',-90,degrees=True),color='metal',density=7800)
    wrist=root.find(".//body[@name='right_gripper']")
    net=add(wrist,'body',name='right_packing_net',pos='-.049 0 -.165',quat=vec(Rotation.from_euler('y',90,degrees=True).as_quat()[[3,0,1,2]]))
    piece(net,'right_pack_net_frame','pack_net_frame')
    piece(net,'right_pack_net_retainer','pack_net_retainer',[0,0,.004])
    piece(net,'right_pack_net_textile','pack_net_textile',color='mesh',density=1100)
    for k,a in enumerate([45,135,225,315]):piece(net,'right_pack_net_screw_'+str(k),'pack_net_screw',[.0405*math.cos(math.radians(a)),.0405*math.sin(math.radians(a)),0],color='metal',density=7800)
    add(net,'site',name='packing_net_center',pos='0 0 0',size='.001',rgba='0 0 0 0')
    # CAD-only placeholder grip fit; solve and audit actual datum/clearance
    # before exporting review poses. No runtime motion is supplied here.
    E.indent(root);E.ElementTree(root).write(folder/'scene.xml',encoding='unicode')
    m=mujoco.MjModel.from_xml_path(str(folder/'scene.xml'));d=mujoco.MjData(m)
    initial=np.load(source/'so101/initial.npz');d.qpos[:]=initial['qpos'];d.ctrl[:]=initial['ctrl']
    # Nominal 17.8 mm handle fit from sections through the actual jaw meshes.
    # This is a geometric fit, not friction/contact-force validation.
    d.qpos[m.joint('right_gripper').qposadr[0]]=.0276
    mujoco.mj_forward(m,d)
    for i in range(m.nu):d.ctrl[i]=d.qpos[m.jnt_qposadr[m.actuator_trnid[i,0]]]
    np.savez_compressed(folder/'initial.npz',qpos=d.qpos,ctrl=d.ctrl)
    assembly=cq.Assembly(name='Concept_A_support')
    assembly.add(cq.importers.importStep(str(source/'so101/support-assembly.step')),name='preserved_V7_rig')
    detail=cq.Assembly(name='Single_pack_fixture')
    for name,part in instances:
        i=m.body(name).id;rv=Rotation.from_matrix(d.xmat[i].reshape(3,3)).as_rotvec();ang=np.linalg.norm(rv)
        shape=shapes[part].val()
        if ang>1e-9:shape=shape.rotate((0,0,0),tuple(rv/ang),np.rad2deg(ang))
        shape=shape.translate(tuple(d.xpos[i]*1000));assembly.add(shape,name=name);detail.add(shape,name=name)
    assembly.save(str(folder/'support-assembly.step'));detail.save(str(out/'cad/packing-assembly.step'))
    report=dict(phase=cfg['packing']['status'],training_ready=False,source='tower-lift-v7',preserved_joint_count=m.nq,
        new_cad_parts=len(shapes),new_mass_kg=sum(float(m.body(name).mass[0]) for name,_ in instances),
        no_loaded_container_on_robot=True,instances=instances)
    (folder/'build.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
