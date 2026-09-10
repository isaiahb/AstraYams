"""Replay a recorded physical command sequence and identify deepest net contact."""
from pathlib import Path
import argparse,json,numpy as np,mujoco
from astrafactory.harvest_basket import HarvestBasketEnv

def run(source,dt,out):
 e=HarvestBasketEnv(task_dir=source/'task');e.reset(seed=61001);z=np.load(source/'episode-61001.npz');m,d=e.model,e.data;m.opt.timestep=dt;e.skip=round(.02/dt);d.qpos[:]=z['qpos'][0];d.qvel[:]=z['qvel'][0];d.eq_active[:]=z['eq_active'][0];e.severed=True;e.work=e.threshold;e.jaw_target=-.0028;e.cut_time=0.;e.target=z['catch_targets'][0].copy();e.cut_target=z['cut_targets'][0].copy()
 a,b=sorted([m.body('secondary_b_5').id,e.branch]);m.exclude_signature[m.exclude_signature==(a<<16)+b]=0;m.exclude_signature[:]=np.sort(m.exclude_signature);mujoco.mj_forward(m,d);e.grip=e.grasp();e.previous_goal=e.geometry()[0].copy();peak={'depth_m':0.};original=e.after_physics_step
 def inspect():
  original()
  for i in np.flatnonzero(np.any(d.contact.flex==e.net,axis=1)&np.any(d.contact.geom==e.fruitgeom,axis=1)):
   c=d.contact[i]
   if -c.dist>peak['depth_m']:
    force=np.zeros(6);mujoco.mj_contactForce(m,d,int(i),force);peak.update(depth_m=float(-c.dist),time_s=float(d.time-.3),force=force.tolist(),geom_names=[m.geom(g).name if g>=0 else 'flex' for g in c.geom],flex_element=c.elem.tolist(),efc_address=int(c.efc_address),position=c.pos.tolist(),normal=c.frame[:3].tolist());np.savez_compressed(out.with_suffix('.npz'),qpos=d.qpos,qvel=d.qvel,eq_active=d.eq_active)
 e.after_physics_step=inspect
 for i in range(min(30,len(z['qpos'])-1)):
  e.target=z['catch_targets'][i+1].copy();e.cut_target=z['cut_targets'][i+1].copy();info=e.advance()
 result=dict(dt=dt,peak=peak,info=info);out.write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--dt',type=float,default=.00025);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.source,a.dt,a.out)
