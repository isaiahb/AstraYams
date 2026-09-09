from pathlib import Path
import sys,json,argparse,numpy as np,mujoco
import xml.etree.ElementTree as ET
parser=argparse.ArgumentParser();parser.add_argument("--plant-dir",type=Path,required=True);P=parser.parse_args().plant_dir.resolve();sys.path.insert(0,str(P.parent/'multi-harvest'))
import env_multi as env
import shutil
def build(scale,segments,tag):
 out=P/tag;out.mkdir(exist_ok=True);shutil.copy2(P/"botanical-v8/scene.xml",out/"scene.xml");return out/"scene.xml"

def run(tag,scale=1,segments=5,contact=True,duration=9,timestep=.0005,kind="berry"):
 path=build(scale,segments,tag);tree=ET.parse(path);tree.find('option').set('timestep',str(timestep));tree.write(path,encoding='unicode');old=env.build_scene;env.build_scene=lambda:path
 try:e=env.MultiEnv()
 finally:env.build_scene=old
 e.reset(seed=1);m,d=e.model,e.data;m.opt.timestep=timestep
 if not contact:m.geom_contype[m.geom('probe_surface').id]=0;m.geom_conaffinity[m.geom('probe_surface').id]=0
 ids=[m.body('crop_fruit_'+str(j)).id for j in [2,3,4]]
 def positions():return np.array([d.geom_xpos[m.geom('crop'+str(j)+'_berry_collision').id] for j in [2,3,4]])
 pa=np.array([m.joint('probe_'+str(i)).qposadr[0] for i in range(3)]);ai=[m.actuator('probe_'+str(i)).id for i in range(3)]
 d.qpos[pa]=[.85,.05,.35];d.ctrl[ai]=d.qpos[pa];mujoco.mj_forward(m,d)
 target_name={"berry":"crop2_berry_collision","leaf":"leaf_surface_left_0_1_1","stalk":"leafstalk_left_0_3_surface"}[kind]
 gid=m.geom(target_name).id; samples=[]; contact_stats={}
 rest=np.load(P/'botanical-v8-control/rollout.npz');idx=int(np.argmin(abs(rest['t']-5)));d.qpos[:]=rest['qpos'][idx];d.qvel[:]=0;d.time=5.;d.qpos[pa]=[.85,.05,.35];d.ctrl[ai]=d.qpos[pa];mujoco.mj_forward(m,d)
 records=[];qs=[];ts=[];ps=[];force_peak=0;count=0;penetration=0;allforces=0;target=None
 for k in range(round((duration-5)/m.opt.timestep)):
  t=float(d.time)
  if k==0:
   # Set probe at experiment start only, clear of fruit, following plant settling.
   origin=d.geom_xpos[gid].copy();direction=np.array([0.,0.,-1.]) if kind=="leaf" else np.array([0.,1.,0.]);start=origin-.06*direction;end=origin+.018*direction;d.qpos[pa]=start;d.qvel[[m.joint('probe_'+str(i)).dofadr[0] for i in range(3)]]=0;target=start.copy();mujoco.mj_forward(m,d)
  if target is not None:
   if t<6.2:u=np.clip((t-5)/1.2,0,1);target=start+(end-start)*(u*u*(3-2*u))
   elif t<6.5:target=end
   elif t<7.7:u=np.clip((t-6.5)/1.2,0,1);target=end+(start-end)*(u*u*(3-2*u))
   else:target=start
   d.ctrl[ai]=target
  for side,arm in e.arms.items():
   d.ctrl[arm['act']]=np.clip(180*(arm['target']-d.qpos[arm['q']])-14*d.qvel[arm['v']]+d.qfrc_bias[arm['v']],-10,10);d.ctrl[m.actuator(side+'_grip').id]=25
  mujoco.mj_step(m,d)
  for ci,c in enumerate(d.contact):
   if m.geom('probe_surface').id in c.geom:
    other=int(c.geom[1] if c.geom[0]==m.geom('probe_surface').id else c.geom[0]);name=m.geom(other).name
    if name:
     stat=contact_stats.setdefault(name,{'contact_points':0,'peak_force_n':0.,'impulse_ns':0.,'max_penetration_mm':0.})
     ff=np.zeros(6);mujoco.mj_contactForce(m,d,ci,ff);stat['contact_points']+=1;stat['peak_force_n']=max(stat['peak_force_n'],float(abs(ff[0])));stat['impulse_ns']+=float(abs(ff[0]))*m.opt.timestep;stat['max_penetration_mm']=max(stat['max_penetration_mm'],float(-c.dist)*1000)
     f=np.zeros(6);mujoco.mj_contactForce(m,d,ci,f);force_peak=max(force_peak,float(abs(f[0])));count+=1;penetration=max(penetration,float(-c.dist));allforces+=abs(f[0])*m.opt.timestep
  if k%round(.04/m.opt.timestep)==0:
   samples.append(d.geom_xpos[gid].copy());qs.append(d.qpos.copy());ts.append(d.time);ps.append(positions());records.append({'t':d.time,'probe':d.xpos[m.body('test_probe').id].tolist()})
  if not np.all(np.isfinite(d.qpos)) or any(w.number for w in d.warning):break
 out=P/tag;np.savez_compressed(out/'rollout.npz',qpos=qs,t=ts,fruit=ps,target=samples);(out/'trace.json').write_text(json.dumps(records))
 report={'target_geom':target_name,'target_contact_observed':target_name in contact_stats,'all_probe_contacts':contact_stats,'probe_initialization':'Initialized from frozen control position at 5s, zero velocities; probe reset before trial, then actuated. Matched controls use same initialization.','tag':tag,'seconds':d.time,'fruits':8,'probe_contact_steps':count,'peak_probe_force_n':force_peak,'probe_impulse_ns':allforces,'max_probe_penetration_m':penetration,'finite':bool(np.all(np.isfinite(d.qpos))),'valid_run':bool(abs(d.time-duration)<.01 and not any(w.number for w in d.warning)),'warnings':[int(w.number) for w in d.warning],'stiffness_scale':scale,'segments':segments,'timestep_s':timestep,'contact_enabled':contact,'scope':'Force-limited diagnostic probe. Robot holds pose. No harvest or learned policy claim.'};(out/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True);e.close()
if __name__=='__main__':
 for kind in ['leaf','stalk','berry']:
  for enabled in [False,True]:
   run('audit-'+kind+('-contact' if enabled else '-control'),contact=enabled,kind=kind)
