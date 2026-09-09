"""An isolated, continuous contact surface supported by articulated leaf ribs.

Alternative to both disconnected panels and a stiff finite-element shell. This
retains reduced hinge mechanics; it is not a calibrated membrane/tissue model.
"""
from pathlib import Path
import argparse, json, time
import xml.etree.ElementTree as ET
import numpy as np
import mujoco

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/workcells/strawberry-specimen/leaf-study/rib-surface-v2'
SPEC=json.loads((ROOT/'tasks/strawberry_specimen/reference-graph.json').read_text())
L=next(x['length'] for x in SPEC['leaves'] if x['id']=='left')
W=L/SPEC['leaflet_profile']['length_to_width']
PROFILE=np.array(SPEC['leaflet_profile']['normalized_halfwidth_stations'])

def v(a):return ' '.join(f'{x:.12g}' for x in np.ravel(a))
def add(p,t,**attrs):return ET.SubElement(p,t,{k:str(x) for k,x in attrs.items()})

def build(output=OUT,dt=.00025):
    output.mkdir(parents=True,exist_ok=True)
    r=ET.Element('mujoco',model='continuous_rib_supported_leaf')
    add(r,'compiler',angle='radian',autolimits='true')
    add(r,'option',timestep=dt,gravity='0 0 -9.81',integrator='implicitfast',iterations=100,cone='elliptic')
    vis=add(r,'visual');add(vis,'global',offwidth=960,offheight=700)
    add(vis,'headlight',ambient='.4 .4 .4',diffuse='.6 .6 .6')
    world=add(r,'worldbody');act=add(r,'actuator')
    add(world,'light',pos='0 -.1 .5',dir='0 .2 -1')
    add(world,'geom',name='bench',type='plane',size='.3 .3 .01',rgba='.9 .91 .87 1')
    add(world,'geom',name='clamp',type='box',pos=v([.009+L*.125,0,.132]),size=v([L*.125+.003,.026,.007]),rgba='.46 .53 .48 1',contype=0,conaffinity=0)
    anchor=add(world,'body',name='anchor',pos='0 0 .14')
    verts=[];bodies=[];faces=[];rows=[];prev=anchor;n=20
    # Uniform axial mass cells. The first quarter is clamped, matching the old isolated test.
    for i in range(n+1):
        t=i/n;hw=max(.0005,W*.5*np.interp(t,PROFILE[:,0],PROFILE[:,1])*(1 if i%2 else .90))
        if i>5:
            b=add(prev,'body',name=f'rib_{i}',pos=v([.009+L*i/n if i==6 else L/n,0,0]))
            # Constant EI approximation: k=EI/dx, with the same EI as four old panels.
            add(b,'joint',name=f'bend_{i}',type='hinge',axis='0 1 0',stiffness=.009*n/4,damping=.0009*n/4,armature='2e-8')
            # Mass/inertia from each material strip; ribs themselves are not extra material.
            mass=.0008/n
            add(b,'inertial',pos='0 0 0',mass=mass,diaginertia=v([mass*(hw**2/3+.00045**2/12),mass*((L/n)**2+.00045**2)/12,mass*(hw**2/3+(L/n)**2/12)]))
            prev=b;local_x=0.;body=f'rib_{i}'
        else:local_x=.009+L*t;body='anchor'
        row=[]
        for side in ([0] if i in [0,n] else [-1,0,1]):
            row.append(len(verts))
            verts.append([local_x,side*hw,.0018*np.sin(np.pi*t)+.003*np.sin(np.pi*t)*abs(side)])
            bodies.append(body)
        rows.append(row)
    for i in range(n):
        a,b=rows[i],rows[i+1]
        if len(a)==1:faces.extend([[a[0],b[0],b[1]],[a[0],b[1],b[2]]])
        elif len(b)==1:faces.extend([[a[0],b[0],a[1]],[a[1],b[0],a[2]]])
        else:
            for j in range(2):faces.extend([[a[j],b[j],a[j+1]],[a[j+1],b[j],b[j+1]]])
    deform=add(r,'deformable')
    flex=add(deform,'flex',name='blade',dim=2,body=' '.join(bodies),vertex=v(verts),element=' '.join(map(str,np.ravel(faces))),radius=.000225,rgba='.22 .39 .08 1')
    add(flex,'contact',internal='true',selfcollide='auto',condim=3,solref='.003 1',solimp='.95 .99 .0001',friction='.45 .003 .001')
    equality=add(r,'equality');add(equality,'flex',flex='blade',solref='.001 1',solimp='.95 .99 .0001')
    probe=add(world,'body',name='probe');add(probe,'geom',name='probe_surface',type='sphere',size=.009,mass=.025,rgba='.91 .54 .12 1',contype=2,conaffinity=1)
    for i in range(3):
        add(probe,'joint',name=f'probe_{i}',type='slide',axis=v(np.eye(3)[i]),damping=.2)
        add(act,'position',joint=f'probe_{i}',kp=35,kv=.8,forcerange='-.3 .3')
    ET.indent(r);ET.ElementTree(r).write(output/'scene.xml',encoding='unicode')
    return mujoco.MjModel.from_xml_path(str(output/'scene.xml'))

def command(t):
    a=np.array([.009+L*.65,.011,.181]);b=np.array([a[0],a[1],.119])
    if t<1:return a
    if t<2:u=t-1;return a+(b-a)*(u*u*(3-2*u))
    if t<2.4:return b
    if t<3.4:u=t-2.4;return b+(a-b)*(u*u*(3-2*u))
    return a

def run(output=OUT,control=False,dt=.00025):
    m=build(output,dt);d=mujoco.MjData(m);pa=[m.joint(f'probe_{i}').qposadr[0] for i in range(3)];pg=m.geom('probe_surface').id
    if control:m.geom_contype[pg]=m.geom_conaffinity[pg]=0
    d.qpos[pa]=command(0);d.ctrl[:]=command(0);mujoco.mj_forward(m,d)
    initial=[float(c.dist) for c in d.contact]
    rest_edges=d.flexedge_length.copy();qs=[];ts=[];vs=[];forces=[];contact_steps=0;maxpen=0.;edgepeak=0.;forcepeak=0.;begin=time.monotonic()
    for k in range(round(4.8/dt)):
        d.ctrl[:]=command(d.time);mujoco.mj_step(m,d);force=0.;touch=False
        for ci,c in enumerate(d.contact):
            if pg in c.geom and 0 in c.flex:
                f=np.zeros(6);mujoco.mj_contactForce(m,d,ci,f);force+=abs(f[0]);touch=True;maxpen=max(maxpen,-c.dist*1000)
        contact_steps+=touch;forcepeak=max(forcepeak,force)
        edgepeak=max(edgepeak,float(np.max(abs(d.flexedge_length/rest_edges-1))))
        if k%round(.02/dt)==0:qs.append(d.qpos.copy());ts.append(float(d.time));vs.append(d.flexvert_xpos.copy());forces.append(force)
        if any(w.number for w in d.warning):break
    out=output/('control' if control else 'contact');out.mkdir(exist_ok=True)
    report={'complete':bool(abs(d.time-4.8)<2*dt and not any(w.number for w in d.warning)),'control':control,'seconds':float(d.time),'elapsed_wall_s':time.monotonic()-begin,'timestep_s':dt,'warnings':[int(w.number) for w in d.warning],
            'initial_contacts':initial,'target_touched':bool(contact_steps),'contact_duration_s':contact_steps*dt,'max_probe_penetration_mm':maxpen,'peak_probe_normal_force_n':forcepeak,'max_relative_edge_length_change':edgepeak,
            'surface':'one shared-vertex contact/render surface supported by articulated ribs with near-inextensible edge constraints; no panel seams',
            'criteria':{'maximum_edge_change':.02,'maximum_probe_penetration_mm':1.,'initial_contacts':0,'complete_without_warnings':True},
            'individual_gate_pass':bool(abs(d.time-4.8)<2*dt and not any(w.number for w in d.warning) and not initial and maxpen<1. and edgepeak<.02 and (not contact_steps if control else contact_steps>0)),
            'limitations':['Reduced bending law; no calibrated membrane stiffness, twist, veins, turgor, damage or cutting.','Uniform axial strip mass, fixed first-quarter clamp; not the crown attachment.','Force-limited scripted probe, not a learned policy.','Not integrated into whole-plant model or old rigid-mesh replay exporter.']}
    (out/'result.json').write_text(json.dumps(report,indent=2));np.savez_compressed(out/'rollout.npz',qpos=qs,t=ts,vertices=vs,force=forces)
    print(json.dumps(report),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=OUT);p.add_argument('--control',action='store_true');p.add_argument('--dt',type=float,default=.00025);a=p.parse_args();run(a.output,a.control,a.dt)
