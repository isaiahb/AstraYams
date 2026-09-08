"""RGB+encoder demonstrations; privileged teacher is offline label generation only.

Raw shards contain sensor arrays and expert action labels. Ground truth, phases,
layout/appearance seeds and success metrics live in separate metadata files.
"""
from pathlib import Path
import argparse,json,time,hashlib,os
import numpy as np,torch
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.contact_micro_grasp import MicroGrasp
from astrafactory.contact_downstream_skills import DownstreamSkill
from astrafactory.contact_downstream_skills_v3 import CorrectedInsertSkill
from astrafactory.deployable_observations import FixedCameraRig,reset_visual_episode,CAMERA_SPECS,VISUAL_RESET_PROFILES
from collect_demonstrations import task_hashes

CHECKPOINTS={'grasp':'runs/micro-grasp-v1/policy.pt','align':'runs/downstream-v2-dr/align.npz','insert':'runs/downstream-v3-corrected/linear.npz'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def collect_episode(out,split,seed,appearance_seed):
 start=time.time();e=CurriculumEnv('tasks/yam_contact_curriculum');reset_info=reset_visual_episode(e,seed,'training' if split=='train' else 'development')
 rig=FixedCameraRig(e.model,e.data,e.qadr,e.vadr,seed=appearance_seed,augment=split=='train');skills={'grasp':MicroGrasp(CHECKPOINTS['grasp']),'align':DownstreamSkill(CHECKPOINTS['align'],'align'),'insert':CorrectedInsertSkill(CHECKPOINTS['insert'])};phase='grasp';skills[phase].start(e)
 images=[];image_times=[];indices=[];states=[];commands=[];control_times=[];teacher_trace=[];handoffs=[];pickup_end=-1;info={};error=None
 try:
  for k in range(e.horizon):
   # Capture before calling the label generator or advancing physics.
   sensor=rig.read(e.target,e.previous_action)
   if not image_times or sensor.image_time_s!=image_times[-1]:images.append(sensor.rgb);image_times.append(sensor.image_time_s)
   indices.append(len(images)-1);states.append(sensor.proprio);control_times.append(sensor.sensor_time_s)
   before=e.data.qpos.copy();action=skills[phase].act(e);assert np.array_equal(before,e.data.qpos)
   commands.append(action);_,_,done,trunc,info=e.step(action);teacher_trace.append({'step':e.steps,'phase':phase,**info})
   ready=skills[phase].handoff(e) if phase=='grasp' else skills[phase].handoff(e,info)
   if ready and phase!='insert':
    old=phase;phase='align' if phase=='grasp' else 'insert';handoffs.append({'from':old,'to':phase,'step':e.steps});skills[phase].start(e)
    if old=='grasp':pickup_end=e.steps
   if done or trunc:break
 except Exception as exc:error={'type':type(exc).__name__,'message':str(exc)}
 finally:rig.close();e.close()
 # If a teacher exception occurred after the sensor read, discard only its
 # unmatched sensor entry, never a completed action/outcome.
 n=len(commands);indices=indices[:n];states=states[:n];control_times=control_times[:n]
 image_times=np.asarray(image_times);control_times=np.asarray(control_times);indices=np.asarray(indices,dtype=np.int32)
 assert n>0 and np.all(image_times[indices]<=control_times+1e-10)
 assert np.max(control_times-image_times[indices])<=.0200001
 path=out/split/f'episode-{seed}.npz';path.parent.mkdir(exist_ok=True)
 np.savez_compressed(path,images=np.array(images,dtype=np.uint8),image_time=image_times,image_index=indices,proprio=np.array(states,dtype=np.float32),action=np.array(commands,dtype=np.float32),control_time=control_times,pickup_end_step=np.array(pickup_end,dtype=np.int32))
 meta={'split':split,'seed':seed,'appearance_seed':appearance_seed,'reset':reset_info,'visual_augmentation':rig.visual_sample,'handoffs':handoffs,'pickup_end_step':pickup_end,'final':info,'error':error,'steps':n,'camera_frames':len(images),'wall_seconds':time.time()-start,'bytes':path.stat().st_size,'sha256':sha(path),'sensor_boundary':'rgb and proprio only; pickup_end_step is an offline label-selection annotation, not a runtime feature'}
 (out/'metadata').mkdir(exist_ok=True);(out/'metadata'/f'{split}-{seed}.json').write_text(json.dumps(meta,indent=2));(out/'metadata'/f'{split}-{seed}-teacher-trace.json').write_text(json.dumps(teacher_trace))
 return {'path':str(path),**meta}


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=Path('runs/visual-contact-v1'));p.add_argument('--train-episodes',type=int,default=32);p.add_argument('--development-episodes',type=int,default=8);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(2)
 train=list(range(10000,10000+a.train_episodes));dev=list(range(20000,20000+a.development_episodes));assert len(set(train+dev))==len(train+dev)
 appearance_rng=np.random.default_rng(20260910);appearance_seeds=appearance_rng.integers(0,2**31-1,size=len(train)+len(dev)).tolist();queue=[('train',s) for s in train[:8]]+[('development',s) for s in dev[:2]]+[('train',s) for s in train[8:]]+[('development',s) for s in dev[2:]]
 sources=[__file__,'src/astrafactory/deployable_observations.py','src/astrafactory/sensor_contract.py','src/astrafactory/contact_micro_grasp.py','src/astrafactory/contact_downstream_skills.py','src/astrafactory/contact_downstream_skills_v3.py','src/astrafactory/contact_env.py','src/astrafactory/env.py']
 spec={'dataset_version':'visual-contact-v1','reset_version':'visual-reset-v1','train_seeds':train,'offline_development_seeds':dev,'rollout_development_seeds':list(range(21000,21005)),'reserved_final_seeds':list(range(8000,8100)),'sensor_schema':{'images':'uint8[camera_frames,2,160,160,3] RGB','image_index':'int32[control_steps],latest image available before action','proprio':'float32[control_steps,28]:measuredq7,measuredqd7,commandedtarget7,previousnormalizedaction7;jaw normalizedopening','action':'float32[control_steps,7],original normalized joint-target increments','camera_hz':25,'control_hz':50,'pairing':'image/proprio captured before teacher action k; action then advances10x2ms physics; cached image age0or20ms; no future images','pickup_end_step':'offline-only exclusive end index for learned pickup labels, not a student input'},'camera_specs':CAMERA_SPECS,'layout_profiles':VISUAL_RESET_PROFILES,'appearance_seed_stream':'Independent RNG20260910, separate from layout/reset seeds; no action-conditioned appearance','source_sha256':{s:sha(s) for s in sources},'teacher_checkpoint_sha256':{v:sha(v) for v in CHECKPOINTS.values()},'task_hashes':task_hashes('tasks/yam_contact_curriculum'),'scope':'Simulator RGB+SDK-compatible jointfeedback; no hardware connected/calibrated. Privileged offline teacher only. Same geometry/contact physics and unchanged acceptance.'}
 (a.out/'proposal.json').write_text(json.dumps(spec,indent=2));records=[];start=time.time()
 for (split,seed),appearance_seed in zip(queue,appearance_seeds):
  r=collect_episode(a.out,split,seed,appearance_seed);records.append(r)
  manifest={'specification':spec,'complete':len(records)==len(queue),'episodes':records,'wall_seconds':time.time()-start};tmp=a.out/'manifest.tmp';tmp.write_text(json.dumps(manifest,indent=2));os.replace(tmp,a.out/'manifest.json');print(json.dumps({k:r[k] for k in ['split','seed','steps','camera_frames','pickup_end_step','wall_seconds','bytes','error']}),flush=True)
 print('COMPLETE',len(records),time.time()-start,flush=True)

if __name__=='__main__':main()
