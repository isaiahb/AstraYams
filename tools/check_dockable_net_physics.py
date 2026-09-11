"""Local V16 retention experiment: free tool + servo-driven rotary finger.

Socket contact uses explicit box walls matching the CAD flat datums. Fillets,
original arm, textile and docking trajectory are outside this isolated bench.
No weld, no tool pose reset after initialisation; low-friction challenge + open
jaw ablation prove that contact/form closure, not a hidden attachment, holds it.
"""
import json,math,hashlib,xml.etree.ElementTree as E
from pathlib import Path
import numpy as np,mujoco as mj,trimesh

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runs/tower-lift-v16/tool-study';PIVOT=np.array([-.1416,.0188,.0692])

def cad_hashes():
    return {n:hashlib.sha256((OUT/'cad'/n).read_bytes()).hexdigest() for n in ['fixed_finger.stl','moving_finger.stl','net_frame.stl','mesh_keeper.stl','net_textile.stl','parking_fork.stl']}

def vec(v):return ' '.join(f'{x:.9g}' for x in np.asarray(v).ravel())
def add(p,t,**kw):return E.SubElement(p,t,{k:str(v) for k,v in kw.items()})
def box(parent,name,low,high,pivot=None):
    low=np.array(low,dtype=float)*.001;high=np.array(high,dtype=float)*.001
    pos=(low+high)/2-(np.array(pivot) if pivot is not None else 0)
    return add(parent,'geom',name=name,type='box',pos=vec(pos),size=vec((high-low)/2),rgba='.65 .74 .68 1')
def pad(parent,name,upper=False):
    p=PIVOT if upper else None;z0,z1=(57,65) if upper else (35,43);split=60.15 if upper else 39.85
    zfloor=(split,z1) if upper else (z0,split);zwall=(z0,split) if upper else (split,z1)
    box(parent,name+'_floor',[-88,-9,zfloor[0]],[-58,9,zfloor[1]],p)
    for n,x0,x1,y0,y1 in [('back',-88,-80.15,-9,9),('front',-65.85,-58,-9,9),('left',-80.15,-65.85,-9,-5.15),('right',-80.15,-65.85,5.15,9)]:box(parent,name+'_'+n,[x0,y0,zwall[0]],[x1,y1,zwall[1]],p)

def build(dt,friction):
    r=E.Element('mujoco',{'model':'V16 keyed-net local retention bench'})
    add(r,'compiler',angle='radian',inertiafromgeom='false')
    add(r,'option',timestep=dt,gravity='0 0 -9.81',integrator='implicitfast',iterations=100,tolerance='1e-10')
    default=add(r,'default');add(default,'geom',friction=f'{friction} .0001 .00001',condim='1' if friction==0 else '3',solref='.003 1',solimp='.95 .99 .001',density=0)
    w=add(r,'worldbody');add(w,'geom',type='plane',size='1 1 .1',pos='0 0 -.25',rgba='.75 .8 .7 1')
    fixed=add(w,'body',name='fixed');pad(fixed,'fixed_pad')
    upper=add(w,'body',name='moving_finger',pos=vec(PIVOT));add(upper,'joint',name='jaw',type='hinge',axis='0 -1 0',range='-.04 1.2',damping='.06',armature='.00003')
    # CAD-density inertia is a material assumption, not a measured printed part.
    g=trimesh.load(OUT/'cad/moving_finger.stl');g.apply_scale(.001);g.density=1100;I=g.moment_inertia
    add(upper,'inertial',pos=vec(g.center_mass-PIVOT),mass=g.mass,fullinertia=vec([I[0,0],I[1,1],I[2,2],I[0,1],I[0,2],I[1,2]]));pad(upper,'moving_pad',True)
    tool=add(w,'body',name='net');add(tool,'freejoint',name='free_net')
    geos=[]
    for name in ['net_frame','mesh_keeper','net_textile']:
        g=trimesh.load(OUT/f'cad/{name}.stl');g.apply_scale(.001);geos.append(g)
    g=trimesh.util.concatenate(geos);g.density=1100;I=g.moment_inertia
    add(tool,'inertial',pos=vec(g.center_mass),mass=g.mass,fullinertia=vec([I[0,0],I[1,1],I[2,2],I[0,1],I[0,2],I[1,2]]))
    box(tool,'lug',[-83,-6,43],[-63,6,57]);box(tool,'bottom_key',[-80,-5,40],[-66,5,43]);box(tool,'top_key',[-80,-5,57],[-66,5,60])
    add(tool,'geom',name='neck',type='capsule',fromto='-.053 0 .050 -.038 0 .003',size='.003',rgba='.12 .48 .42 1')
    for k in range(24):
        a,b=np.array([k,k+1])*2*np.pi/24
        add(tool,'geom',name=f'rim_{k}',type='capsule',fromto=vec([.0405*np.cos(a),.0405*np.sin(a),.003,.0405*np.cos(b),.0405*np.sin(b),.003]),size='.0025',rgba='.12 .48 .42 1')
    act=add(r,'actuator');add(act,'position',name='jaw_motor',joint='jaw',kp='60',kv='.3',forcerange='-.35 .35',ctrlrange='-.04 1.2')
    E.indent(r);return E.tostring(r,encoding='unicode'),float(g.mass)

def run(dt,friction,open_jaw=False):
    xml,mass=build(dt,friction);m=mj.MjModel.from_xml_string(xml);d=mj.MjData(m);mjid=m.body('net').id;jid=m.joint('jaw').id
    key=np.array([-.073,0,.05]);records=[];peak=0;maxkey=0;peakangle=0;initial_key=key.copy();positions=[];cforce=np.zeros(6)
    # 0.5 s settling, then +/- 1 N in each horizontal direction (tool CoM),
    # finally upward pull. Ordinary gravity acts through CAD-derived CoM.
    forces=[(0,0,0),(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,0)]
    duration=3.5
    for k in range(round(duration/dt)):
        t=k*dt;phase=min(int(t/.5),len(forces)-1);d.ctrl[0]=.6 if open_jaw and t>.5 else -.004
        d.xfrc_applied[mjid,:3]=forces[phase]
        mj.mj_step(m,d)
        R=d.xmat[mjid].reshape(3,3);kp=d.xpos[mjid]+R@key;err=float(np.linalg.norm(kp-initial_key));maxkey=max(maxkey,err)
        angle=float(np.degrees(np.arccos(np.clip((np.trace(R)-1)/2,-1,1))));peakangle=max(peakangle,angle)
        for contact in range(d.ncon):
            mj.mj_contactForce(m,d,contact,cforce);peak=max(peak,float(np.linalg.norm(cforce[:3])))
        if k%max(1,round(.01/dt))==0 or err>.05:records.append(dict(t=float(t),key_error_mm=err*1000,rotation_deg=angle,force_N=forces[phase],tool_position=d.xpos[mjid].tolist(),tool_quaternion=d.xquat[mjid][[1,2,3,0]].tolist(),jaw_angle=float(d.qpos[m.jnt_qposadr[jid]])))
        if err>.05:break  # Detached: terminate before continued force accelerates the free tool.
    result=dict(dt_s=dt,friction=friction,open_jaw_ablation=open_jaw,mass_kg=mass,max_key_shift_mm=maxkey*1000,max_tool_rotation_deg=peakangle,peak_contact_force_N=peak,finite=bool(np.isfinite(d.qpos).all()),warnings=int(sum(x.number for x in d.warning)),final_key_shift_mm=records[-1]['key_error_mm'])
    return result,records,xml

def main():
    tests=[];out=OUT/'retention-bench';out.mkdir(exist_ok=True)
    for label,dt,mu,opened in [('low-friction',.00025,.05,False),('half-timestep',.000125,.05,False),('zero-friction',.00025,0,False),('open-jaw-control',.00025,.05,True)]:
        result,frames,xml=run(dt,mu,opened);result['label']=label;tests.append(result)
        (out/(label+'.json')).write_text(json.dumps(dict(result=result,frames=frames),separators=(',',':')))
        (out/(label+'.xml')).write_text(xml)
        print(label,json.dumps(result),flush=True)
    summary=dict(cad_sha256=cad_hashes(),scope='Isolated contact retention bench, analytic flat-wall socket collision proxy, fixed wrist. Not full-arm docking or mesh/fruit dynamics. All forces act through MuJoCo; tool is a free body.',applied_force_N=1,servo_torque_limit_Nm=.35,tests=tests)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
if __name__=='__main__':main()
