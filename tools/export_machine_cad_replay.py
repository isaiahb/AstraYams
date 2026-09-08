"""Export measured MuJoCo body poses for interactive CAD playback.

This is deterministic recording conversion, not a physics rerun or learned-policy
execution. Visual CAD remains separate from the frozen collision scene.
"""
import argparse,hashlib,json
from pathlib import Path
import mujoco,numpy as np

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def export(run,seed,mode,manifest):
 source=run/f'{mode}-{seed}.npz';trace_path=run/f'{mode}-{seed}.json';trace=json.loads(trace_path.read_text());record=np.load(source);model=mujoco.MjModel.from_xml_path('tasks/yam_machine_tending/scene.xml');data=mujoco.MjData(model)
 assert record['qpos'].shape[1]==model.nq
 frames=[];indices=range(len(record['qpos']))
 for k in indices:
  data.qpos[:]=record['qpos'][k];mujoco.mj_forward(model,data);bodies={}
  for i in range(model.nbody):
   name=model.body(i).name
   if not name:continue
   q=data.xquat[i];bodies[name]={'position':np.round(data.xpos[i],8).tolist(),'quaternion':np.round(q[[1,2,3,0]],8).tolist()}
  row=trace['trace'][k];frames.append({'time':row['sim_time'],'bodies':bodies,'phase':row['phase'],'machine_command':'CLOSE' if row['vise_target_gap_m']<.02 else 'OPEN','vise_gap_m':row['vise_opening_m'],'is_success':row['is_success']})
 assert all(a['time']<b['time'] for a,b in zip(frames,frames[1:]))
 assets=json.loads(manifest.read_text());objects=[]
 for item in assets['objects']:
  obj=dict(item);rgb=obj['color'];obj['color']=sum(int(round(max(0,min(1,float(v)))*255))<<shift for v,shift in zip(rgb,[16,8,0])) if isinstance(rgb,list) else rgb
  obj['local_position']=obj.pop('position',[0,0,0]);q=obj.pop('quaternion',[1,0,0,0]);obj['local_quaternion']=[q[1],q[2],q[3],q[0]] if assets.get('quaternion_convention')=='wxyz' else q;obj['scale']=[1,1,1];objects.append(obj)
 for obj in objects:
  assert Path(obj['mesh_path']).is_file(),obj
  assert obj['body'] in frames[0]['bodies'],obj['body']
 r={'schema_version':1,'coordinate_system':'right-handed Z-up','units':'metres','label':'recorded_physics','source_sha256':sha(source),'trace_sha256':sha(trace_path),'scene_sha256':sha('tasks/yam_machine_tending/scene.xml'),'cad_manifest_sha256':sha(manifest),'robot_urdf_sha256':sha('assets/robots/yam/v1/yam.urdf'),'outcome':trace['result'],'fps':50,'frames':frames,'objects':objects,'assembly_path':'assets/workcells/machine_tending_cad/machine_tending_assembly.step','camera':{'target':[.19,0,.20],'position':[.85,-.85,.61]},'default_time':65,'scope':'Actual YAM URDF and parametric CAD visual meshes following recorded body world poses. No invented animation. CAD cosmetic features are not additional collision geometry. Scripted powered-vise commands and IK; only seating correction learned by PPO.','source_run':str(run),'seed':seed,'mode':mode}
 out=run/f'{mode}-{seed}-cad-replay.json';out.write_text(json.dumps(r,separators=(',',':')));print(json.dumps({'path':str(out),'frames':len(frames),'objects':len(objects),'duration':frames[-1]['time'],'success':trace['result']['success']}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,default=Path('runs/machine-seating-ppo-v1-holdout'));p.add_argument('--seed',type=int,default=58000);p.add_argument('--manifest',type=Path,default=Path('assets/workcells/machine_tending_cad/manifest.json'));a=p.parse_args()
 for mode in ['baseline','candidate']:export(a.run,a.seed,mode,a.manifest)
