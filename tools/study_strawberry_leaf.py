"""Isolated leaflet experiment, separate from the whole-plant baseline and UI.

Compare the original segmented surface with a shared-vertex elastic shell.
Both use the same stored silhouette, nominal mass, clamp span and probe path.
Material values are hypotheses, not measurements of a living strawberry leaf.
"""
from pathlib import Path
import argparse,copy,hashlib,json,time
import xml.etree.ElementTree as ET
import numpy as np
import mujoco

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'assets/workcells/strawberry-specimen'
OUT=BASE/'leaf-study'
NAME='leaf_left_1'
SPEC=json.loads((ROOT/'tasks/strawberry_specimen/reference-graph.json').read_text())
L=next(l['length'] for l in SPEC['leaves'] if l['id']=='left')
W=L/SPEC['leaflet_profile']['length_to_width']
PROFILE=np.array(SPEC['leaflet_profile']['normalized_halfwidth_stations'])
Z=.14

def vec(a):return ' '.join(f'{float(x):.9g}' for x in np.ravel(a))
def add(p,t,**kw):return ET.SubElement(p,t,{k:str(v) for k,v in kw.items()})
def halfwidth(t):
    # Same 20-station outline as the existing specimen, including its teeth.
    i=np.rint(np.asarray(t)*20).astype(int)
    return np.maximum(W*.5*np.interp(t,PROFILE[:,0],PROFILE[:,1])*np.where(i%2,1.,.90),.0005)

def build(mode,dt):
    out=OUT/mode;out.mkdir(parents=True,exist_ok=True)
    r=ET.Element('mujoco',model='isolated_leaf_'+mode)
    add(r,'compiler',angle='radian',autolimits='true')
    add(r,'option',timestep=dt,integrator='implicitfast',iterations=100,gravity='0 0 -9.81',cone='elliptic')
    visual=add(r,'visual');add(visual,'global',offwidth=960,offheight=700)
    add(visual,'headlight',diffuse='.6 .6 .6',ambient='.4 .4 .4',specular='.05 .05 .05')
    defaults=add(r,'default');add(defaults,'geom',condim=3,solref='.003 1',solimp='.95 .99 .0001',friction='.45 .003 .001')
    asset=add(r,'asset');world=add(r,'worldbody');act=add(r,'actuator')
    add(world,'light',pos='0 -.1 .5',dir='0 .2 -1',diffuse='.8 .8 .75')
    add(world,'geom',name='bench',type='plane',size='.3 .3 .01',rgba='.9 .91 .87 1')
    add(world,'geom',name='clamp',type='box',pos=vec([.009+L*.125,0,Z-.008]),size=vec([L*.125+.003,.026,.007]),rgba='.46 .53 .48 1',contype=0,conaffinity=0)
    add(world,'geom',name='clamp_post',type='cylinder',pos=vec([.009+L*.125,0,(Z-.015)/2]),size=vec([.013,(Z-.015)/2]),rgba='.58 .64 .58 1',contype=0,conaffinity=0)
    anchor=add(world,'body',name='anchor',pos=vec([0,0,Z]))
    if mode=='segmented':
        original=ET.parse(BASE/'scene.xml').getroot()
        for mesh in original.find('asset').findall('mesh'):
            if mesh.get('name','').startswith(NAME+'_w'):asset.append(copy.deepcopy(mesh))
        leaf=copy.deepcopy(original.find(".//body[@name='"+NAME+"_root']"))
        leaf.set('euler','0 0 0');leaf.set('pos','0 0 0')
        panel=leaf.find(".//body[@name='"+NAME+"_panel0']")
        panel.remove(panel.find('joint'))  # Clamp first quarter in both models.
        anchor.append(leaf)
    else:
        points=[];faces=[];ny=7
        for i in range(21):
            t=i/20
            for j in range(ny):
                s=j/(ny-1)*2-1
                points.append([.009+L*t,float(halfwidth(t))*s,.0018*np.sin(np.pi*t)+.003*np.sin(np.pi*t)*abs(s)])
        for i in range(20):
            for j in range(ny-1):
                a=i*ny+j;b=(i+1)*ny+j;c=a+1;d=b+1
                faces.extend([[a,b,c],[c,b,d]])
        flex=add(anchor,'flexcomp',name='blade',type='direct',dim=2,point=vec(points),element=' '.join(map(str,np.ravel(faces))),mass='.0008',radius='.000225',rgba='.22 .39 .08 1')
        add(flex,'pin',id=' '.join(map(str,range(6*ny))))
        add(flex,'edge',equality='true',damping='.001',solref='.003 1')
        add(flex,'elasticity',young='8e7',poisson='.3',thickness='.00045',elastic2d='bend',damping='.003')
        add(flex,'contact',selfcollide='auto',internal='true',condim=3,solref='.003 1',solimp='.95 .99 .0001',friction='.45 .003 .001')
    probe=add(world,'body',name='probe')
    add(probe,'geom',name='probe_surface',type='sphere',size='.009',mass='.025',rgba='.91 .54 .12 1',contype=2,conaffinity=1)
    for i in range(3):
        add(probe,'joint',name=f'probe_{i}',type='slide',axis=vec(np.eye(3)[i]),damping='.2')
        add(act,'position',name=f'probe_{i}',joint=f'probe_{i}',kp=35,kv='.8',forcerange='-.3 .3')
    ET.indent(r);ET.ElementTree(r).write(out/'scene.xml',encoding='unicode')
    m=mujoco.MjModel.from_xml_path(str(out/'scene.xml'))
    ledger=dict(mode=mode,scope='Isolated clamped leaflet. Scripted probe; no robot, no real-plant calibration.',leaf_length_m=L,leaf_width_m=W,nominal_blade_mass_kg=.0008,
                clamp_fraction=.25,timestep_s=dt,simulator=mujoco.__version__,source_model_sha256=hashlib.sha256((BASE/'scene.xml').read_bytes()).hexdigest(),
                sources=['tasks/strawberry_specimen/reference-graph.json','https://mujoco.readthedocs.io/en/stable/XMLreference.html#flex-elasticity'],
                limitations=['Same outline and nominal mass; constitutive law and nodal mass distribution differ.',
                             'First quarter clamped for this isolated test; not the plant attachment boundary.',
                             'Uniform-node flex mass, isotropic equivalent material, no explicit veins or turgor.',
                             '80 MPa is an assumed effective modulus, not a strawberry tissue measurement.'],
                criteria={'full_episode_no_warnings':True,'intended_contact':True,'control_zero_contact':True,'initial_overlap':False,'peak_probe_penetration_mm_max':1.,'max_edge_extension_fraction':.02})
    (out/'setup.json').write_text(json.dumps(ledger,indent=2))
    return m

def command(t):
    start=np.array([.009+L*.65,.011,.181]);end=np.array([start[0],start[1],.119])
    if t<1.:return start
    if t<2.:u=t-1;return start+(end-start)*(u*u*(3-2*u))
    if t<2.4:return end
    if t<3.4:u=t-2.4;return end+(start-end)*(u*u*(3-2*u))
    return start

def seam_gap(m,d):
    gaps=[]
    for k in range(1,4):
        t=k/4;z=.0018*np.sin(np.pi*t)
        ids=[m.body(f'{NAME}_panel{k-1}').id,m.body(f'{NAME}_panel{k}').id]
        for side in [-1,0,1]:
            yz=[float(halfwidth(t))*side,z+.003*np.sin(np.pi*t)*abs(side)]
            p=d.xpos[ids[0]]+d.xmat[ids[0]].reshape(3,3)@np.array([L/4,*yz])
            q=d.xpos[ids[1]]+d.xmat[ids[1]].reshape(3,3)@np.array([0,*yz])
            gaps.append(np.linalg.norm(p-q))
    return max(gaps)*1000

def run(mode,control=False,dt=.00025):
    m=build(mode,dt);d=mujoco.MjData(m)
    out=OUT/mode/('control' if control else 'contact');out.mkdir(exist_ok=True)
    pa=np.array([m.joint(f'probe_{i}').qposadr[0] for i in range(3)])
    pg=m.geom('probe_surface').id
    if control:m.geom_contype[pg]=m.geom_conaffinity[pg]=0
    d.qpos[pa]=command(0);d.ctrl[:]=command(0);mujoco.mj_forward(m,d)
    initial=[i for i,c in enumerate(d.contact) if pg in c.geom]
    q=[];ts=[];vertices=[];forces=[];gaps=[];positions=[];contact_steps=0;maxpen=0.;forcepeak=0.;edgepeak=0.;t0=time.monotonic()
    for k in range(round(4.8/dt)):
        d.ctrl[:]=command(d.time);mujoco.mj_step(m,d)
        force=0.;touch=False
        for i,c in enumerate(d.contact):
            if pg not in c.geom:continue
            hit=(mode=='shell' and 0 in c.flex) or (mode=='segmented' and any(g>=0 and m.geom(int(g)).name.startswith(NAME+'_w') for g in c.geom))
            if not hit:continue
            f=np.zeros(6);mujoco.mj_contactForce(m,d,i,f);force+=abs(f[0]);maxpen=max(maxpen,-c.dist*1000);touch=True
        contact_steps+=touch;forcepeak=max(forcepeak,force)
        if mode=='shell':
            edgepeak=max(edgepeak,float(np.max(np.abs(d.flexedge_length/m.flexedge_length0-1))))
        if k%round(.02/dt)==0:
            q.append(d.qpos.copy());ts.append(float(d.time));forces.append(force);positions.append(d.geom_xpos[pg].copy())
            if mode=='shell':vertices.append(d.flexvert_xpos.copy());gaps.append(0.)
            else:gaps.append(seam_gap(m,d))
        if any(w.number for w in d.warning) or not np.all(np.isfinite(d.qpos)):break
    report=dict(mode=mode,control=control,seconds=float(d.time),elapsed_wall_s=time.monotonic()-t0,
                complete=bool(abs(d.time-4.8)<dt*2 and not any(w.number for w in d.warning)),warnings=[int(w.number) for w in d.warning],
                initial_probe_contacts=len(initial),target_touched=bool(contact_steps),contact_duration_s=contact_steps*dt,
                peak_sum_probe_normal_force_n=forcepeak,max_probe_penetration_mm=maxpen,
                max_panel_seam_gap_mm=max(gaps) if mode=='segmented' else None,
                shell_max_edge_extension_fraction=edgepeak if mode=='shell' else None,
                surface_continuity='Shared triangle vertices; no independently separating panel edges.' if mode=='shell' else 'Independent rigid panels joined only at hinge axes.',
                scope='Numerical diagnostic only. Both models use the same world-space commanded probe trajectory; material calibration is absent.')
    (out/'result.json').write_text(json.dumps(report,indent=2));np.savez_compressed(out/'rollout.npz',qpos=q,t=ts,force=forces,gap_mm=gaps,probe_positions=positions,vertices=vertices)
    print(json.dumps(report),flush=True)

def render():
    import imageio.v2 as imageio
    from PIL import Image,ImageDraw,ImageFont
    font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',18)
    models={mode:mujoco.MjModel.from_xml_path(str(OUT/mode/'scene.xml')) for mode in ['segmented','shell']}
    data={mode:mujoco.MjData(m) for mode,m in models.items()}
    logs={mode:np.load(OUT/mode/'contact/rollout.npz') for mode in models}
    renderers={mode:mujoco.Renderer(m,560,720) for mode,m in models.items()}
    cam=mujoco.MjvCamera();cam.lookat[:]=[.053,0,.13];cam.distance=.23;cam.azimuth=120;cam.elevation=-35
    for rr in renderers.values():
        rr.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW]=True
    def frame(mode,i):
        d=data[mode];d.qpos[:]=logs[mode]['qpos'][i];mujoco.mj_forward(models[mode],d)
        rr=renderers[mode];rr.update_scene(d,cam)
        im=Image.fromarray(rr.render());draw=ImageDraw.Draw(im);draw.rectangle((0,0,720,75),fill='#17251d')
        draw.text((18,12),'Original segmented surface' if mode=='segmented' else 'Candidate continuous elastic surface',font=font,fill='white')
        draw.text((18,41),f't = {logs[mode]["t"][i]:.2f} s  |  scripted contact test  |  uncalibrated',font=font,fill='#d1d9ca')
        return np.asarray(im)
    count=min(len(z['t']) for z in logs.values())
    with imageio.get_writer(OUT/'comparison.mp4',fps=25,codec='libx264',quality=8,macro_block_size=2) as writer:
        for i in range(0,count,2):
            writer.append_data(np.concatenate([frame(mode,i) for mode in models],axis=1))
    for sec in [.9,1.7,2.3,4.7]:
        i=int(np.argmin(abs(logs['shell']['t']-sec)))
        for mode in models:Image.fromarray(frame(mode,i)).save(OUT/mode/f'phase-{sec}.png')
    for rr in renderers.values():rr.close()
    print('Rendered',OUT/'comparison.mp4')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['segmented','shell'],default='shell');ap.add_argument('--control',action='store_true');ap.add_argument('--dt',type=float,default=.00025);ap.add_argument('--render',action='store_true');a=ap.parse_args()
    render() if a.render else run(a.mode,a.control,a.dt)
