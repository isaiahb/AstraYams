"""V16 docking on a force-limited linear test stage, not a full robot rollout."""
import json,xml.etree.ElementTree as E
from pathlib import Path
import numpy as np,mujoco as mj
from check_dockable_net_physics import build,OUT,add,box,vec,cad_hashes

def run(dt=.00025):
    xml,mass=build(dt,.05);r=E.fromstring(xml);w=r.find('worldbody')
    wrist=add(w,'body',name='test_stage');add(wrist,'joint',name='stage_x',type='slide',axis='1 0 0',range='-.1 .01',damping='2');add(wrist,'joint',name='stage_z',type='slide',axis='0 0 1',range='-.02 .01',damping='2')
    add(wrist,'inertial',pos='0 0 0',mass='.15',diaginertia='.0004 .0004 .0004')
    for name in ['fixed','moving_finger']:
        b=w.find(f"body[@name='{name}']");w.remove(b);wrist.append(b)
    dock=add(w,'body',name='dock')
    # Segmented approximation of the CAD horseshoe ring; rear contact
    # supports the tool's CAD-derived CoM at x=-31.8 mm.
    for k in range(24):
        ang=(k+.5)*2*np.pi/24;x,y=.042*np.cos(ang),.042*np.sin(ang)
        if x<0 and abs(y)<.008:continue
        add(dock,'geom',name='dock_segment_'+str(k),type='box',pos=vec([x,y,-.003]),size='.005 .0054 .003',euler=vec([0,0,ang]),rgba='.25 .4 .35 1')
    a=r.find('actuator')
    for name in ['x','z']:add(a,'position',name='stage_'+name,joint='stage_'+name,kp='1800',kv='22',forcerange='-12 12')
    m=mj.MjModel.from_xml_string(E.tostring(r,encoding='unicode'));d=mj.MjData(m);bid=m.body('net').id;wid=m.body('test_stage').id
    frames=[];force=np.zeros(6);peak=0;maxmove=0
    def blend(t,a,b):
        s=np.clip((t-a)/(b-a),0,1);return s*s*(3-2*s)
    for k in range(round(3.4/dt)):
        t=k*dt;d.ctrl[0]=-.004+.6*blend(t,.45,1.0)
        d.ctrl[1]=-.068*blend(t,1.75,2.8);d.ctrl[2]=-.004*blend(t,1.05,1.6)
        mj.mj_step(m,d);maxmove=max(maxmove,float(np.linalg.norm(d.xpos[bid])))
        for ci in range(d.ncon):
            mj.mj_contactForce(m,d,ci,force);peak=max(peak,float(np.linalg.norm(force[:3])))
        if k%max(1,round(.01/dt))==0:
            frames.append(dict(t=float(t),tool_position=d.xpos[bid].tolist(),tool_quaternion=d.xquat[bid][[1,2,3,0]].tolist(),stage_position=d.xpos[wid].tolist(),jaw_angle=float(d.qpos[m.joint('jaw').qposadr[0]]),key_error_mm=float(np.linalg.norm(d.xpos[bid]))*1000,force_N=[0,0,0]))
    mj.mj_forward(m,d);final_contacts=[]
    for c in d.contact:
        b1,b2=[m.body(m.geom_bodyid[g]).name for g in [c.geom1,c.geom2]]
        if 'net' in [b1,b2]:final_contacts.append([b1,b2])
    report=dict(cad_sha256=cad_hashes(),dt_s=dt,mass_kg=mass,stage_final_m=d.xpos[wid].tolist(),net_final_m=d.xpos[bid].tolist(),max_net_origin_shift_mm=maxmove*1000,peak_contact_N=peak,final_contacts=final_contacts,net_supported_by_dock=any('dock' in c for c in final_contacts),finger_contact_remaining=any('fixed' in c or 'moving_finger' in c for c in final_contacts),warnings=int(sum(x.number for x in d.warning)),scope='Linear-stage fixture supplies the wrist motion through force-limited actuators. Net is a free body; flat-wall socket and rim-capsule proxies. No full-arm reach or textile validation.')
    out=OUT/'retention-bench'
    stem='docking' if dt==.00025 else 'docking-half-timestep'
    (out/(stem+'.json')).write_text(json.dumps(dict(result=report,frames=frames),separators=(',',':')))
    E.indent(r);(out/(stem+'.xml')).write_text(E.tostring(r,encoding='unicode'));print(json.dumps(report),flush=True)
    return report
if __name__=='__main__':
    reports=[run(),run(.000125)];(OUT/'retention-bench/docking-summary.json').write_text(json.dumps(reports,indent=2)+'\n')
