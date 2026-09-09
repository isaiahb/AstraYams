"""Controlled physical probe trials; reports incidental as well as intended contacts."""
from pathlib import Path
import argparse,json,time
import numpy as np,mujoco
P=Path(__file__).resolve().parents[1]/'assets/workcells/strawberry-specimen'
def run(kind='rest',control=False):
 m=mujoco.MjModel.from_xml_path(str(P/'scene.xml'));d=mujoco.MjData(m);out=P/(kind+('-control' if control else ''));out.mkdir(exist_ok=True)
 pa=np.array([m.joint(f'probe_{i}').qposadr[0] for i in range(3)]);va=np.array([m.joint(f'probe_{i}').dofadr[0] for i in range(3)]);ai=np.array([m.actuator(f'probe_{i}').id for i in range(3)]);pg=m.geom('probe_surface').id
 d.qpos[pa]=[.5,-.5,.5];d.ctrl[ai]=d.qpos[pa]
 if kind!='rest':
  z=np.load(P/'rest/rollout.npz');d.qpos[:]=z['qpos'][-1];d.qvel[:]=0
 if kind=='rest':m.geom_contype[pg]=m.geom_conaffinity[pg]=0
 mujoco.mj_forward(m,d)
 target={'leaf':'leaf_left_1_w14_-1','stalk':'peduncle_5_surface','neighbor':'berry_secondary_a'}.get(kind);direction=None
 if target:
  gid=m.geom(target).id;origin=d.geom_xpos[gid].copy()
  if kind=='leaf':direction=-d.xmat[m.geom_bodyid[gid]].reshape(3,3)[:,2]
  elif kind=='stalk':direction=np.array([1.,0.,0.])
  else:
   direction=d.geom_xpos[m.geom('berry_secondary_b').id]-origin;direction/=np.linalg.norm(direction)
  start=origin-direction*.045;end=origin+direction*(.012 if kind=='leaf' else .035)
  if kind=='neighbor':
   # Search only probe approach directions; keep plant state and collision filters.
   toward=direction.copy();candidates=[]
   for theta in np.linspace(0,2*np.pi,24,endpoint=False):
    dr=np.array([np.cos(theta),np.sin(theta),.15]);dr/=np.linalg.norm(dr)
    if np.dot(dr,toward)<.25:continue
    proposed=origin-dr*.055;d.qpos[pa]=proposed;mujoco.mj_forward(m,d)
    touching=any(pg in c.geom for c in d.contact)
    if not touching:candidates.append((np.dot(dr,toward),dr.copy()))
   if not candidates:raise RuntimeError('No collision-free probe start for neighboring fruit test')
   direction=max(candidates,key=lambda x:x[0])[1];start=origin-direction*.055;end=origin+direction*.028
  d.qpos[pa]=start;d.qvel[va]=0;d.ctrl[ai]=start;mujoco.mj_forward(m,d)
  # Select the identical collision-aware approach before disabling control contacts.
 if control:m.geom_contype[pg]=m.geom_conaffinity[pg]=0;mujoco.mj_forward(m,d)
 # Initialization clearance is reported, not silently ignored.
 init=[{'a':m.geom(c.geom[0]).name,'b':m.geom(c.geom[1]).name,'penetration_mm':max(0.,-c.dist*1000)} for c in d.contact if pg in c.geom]
 stats={};allstats={};q=[];ts=[];positions=[];dur=10 if kind=='rest' else 4;peak=0.;warnings=[];t0=time.time();rim_steps=0;neighbor_steps=0
 for k in range(round(dur/m.opt.timestep)):
  t=float(d.time)
  if target:
   if t<.4:cmd=start
   elif t<1.5:u=(t-.4)/1.1;cmd=start+(end-start)*(u*u*(3-2*u))
   elif t<1.8:cmd=end
   elif t<2.9:u=(t-1.8)/1.1;cmd=end+(start-end)*(u*u*(3-2*u))
   else:cmd=start
   d.ctrl[ai]=cmd
  mujoco.mj_step(m,d)
  touched_rim=False;touched_neighbor=False
  for i,c in enumerate(d.contact):
   a,b=[m.geom(int(g)).name for g in c.geom];f=np.zeros(6);mujoco.mj_contactForce(m,d,i,f)
   if ('trough_rim' in (a,b) or 'trough_front' in (a,b)) and ('peduncle' in a+b or 'secondary' in a+b):touched_rim=True
   if a.startswith('berry_') and b.startswith('berry_'):touched_neighbor=True
   if c.dist<-.001:
    key=' | '.join(sorted([a,b]));allstats[key]=max(allstats.get(key,0.),float(-c.dist)*1000)
   if pg in c.geom:
    other=b if int(c.geom[0])==pg else a;s=stats.setdefault(other,dict(contact_points=0,peak_force_n=0.,impulse_ns=0.,max_penetration_mm=0.));s['contact_points']+=1;s['peak_force_n']=max(s['peak_force_n'],float(abs(f[0])));s['impulse_ns']+=float(abs(f[0]))*m.opt.timestep;s['max_penetration_mm']=max(s['max_penetration_mm'],float(-c.dist)*1000)
  rim_steps+=touched_rim;neighbor_steps+=touched_neighbor
  if k%40==0:q.append(d.qpos.copy());ts.append(float(d.time));positions.append(d.geom_xpos.copy())
  if any(w.number for w in d.warning) or not np.all(np.isfinite(d.qpos)):break
 report=dict(kind=kind,control=control,seconds=float(d.time),elapsed_wall_s=time.time()-t0,valid_run=bool(not any(w.number for w in d.warning) and abs(d.time-dur)<.005),warnings=[int(w.number) for w in d.warning],initial_probe_contacts=init,probe_start_m=start.tolist() if target else None,probe_end_m=end.tolist() if target else None,target=target,target_touched=target in stats if target else None,probe_contacts=stats,truss_trough_contact_duration_s=rim_steps*m.opt.timestep,berry_berry_contact_duration_s=neighbor_steps*m.opt.timestep,penetrations_over_1mm=allstats,scope='Force-limited probe diagnostic, not a learned policy or calibrated biological response. Reset before each trial; no plant edits during simulation.')
 if kind=='rest':
  a=np.array(positions);report['final_second_max_geom_coordinate_span_mm']=float(np.ptp(a[np.array(ts)>dur-1],axis=0).max()*1000)
 np.savez_compressed(out/'rollout.npz',qpos=q,t=ts,geom_positions=positions);(out/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--kind',choices=['rest','leaf','stalk','neighbor'],default='rest');p.add_argument('--control',action='store_true');a=p.parse_args();run(a.kind,a.control)
