"""Engineered noncontact transport-speed experiment; frozen learned controllers.

Only arm commands during verified free transport are scaled. Contact phases,
PPO seating correction, gripper commands, PD gains and task limits are unchanged.
Velocity/torque telemetry is sampled after each50Hzcontrol step. URDF limits are
placeholders, not validated hardware ratings. No new training or promotion.
"""
import argparse,hashlib,json,time,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np,torch,mujoco
from stable_baselines3 import PPO
from astrafactory.machine_tending import MachineTendingEnv,active_contacts
from astrafactory.machine_tending_policy import StructuredServo
from train_machine_seating_ppo import SeatingWorkflow,observe

PHASES={'move_output','move_vise','travel_raw'}
URDF=Path('assets/robots/yam/v1/yam.urdf')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def below(model,body,root):
 while body:
  if body==root:return True
  body=int(model.body_parentid[body])
 return body==root

def free_transport(e,phase):
 if phase not in PHASES:return False
 # Carry phases require suspended bilateral grasp and no fixture support.
 carry=phase in ('move_output','move_vise');f=active_contacts(e)
 if carry and not (f[0]>.1 and f[1]>.1 and f[2]<.01 and e.data.site_xpos[e.task.pid,2]>.10):return False
 root=int(e.model.jnt_bodyid[e.model.joint('joint1').id]);fingers=[e.model.body(n).id for n in ('tip_left','tip_right')]
 for i,c in enumerate(e.data.contact):
  b=[int(e.model.geom_bodyid[g]) for g in c.geom]
  robot=[below(e.model,x,root) for x in b]
  if not any(robot):continue
  allowed=False
  if carry and robot[0]!=robot[1]:
   rb=b[0] if robot[0] else b[1];other=b[1] if robot[0] else b[0]
   allowed=any(below(e.model,rb,finger) for finger in fingers) and below(e.model,other,e.task.peg_body)
  if allowed:continue
  force=np.zeros(6);mujoco.mj_contactForce(e.model,e.data,i,force)
  if np.linalg.norm(force[:3])>.01:return False
 return True

def run(seed,factor,models,policy,out):
 start=time.perf_counter();e=MachineTendingEnv();e.reset(seed=seed);w=SeatingWorkflow(models)
 rows=[];actions=[];positions=[];phase_durations={};scaled=0;error=None;peak_speed=np.zeros(6);peak_torque=np.zeros(6);peak_control=np.zeros(6)
 bounds=e.model.actuator_ctrlrange[e.aids[:6]].copy();dt=e.model.opt.timestep*e.frame_skip
 try:
  for _ in range(e.horizon):
   phase_before=w.phase;w.residual=np.zeros(3) if w.phase!='seat_raw' else policy.predict(observe(e),deterministic=True)[0]
   before=e.data.qpos.copy();original=w.act(e);assert np.array_equal(before,e.data.qpos)
   # Do not scale a transition step: its target may still belong to prior phase.
   allowed=phase_before==w.phase and free_transport(e,w.phase)
   action=original.copy()
   if allowed:action[:6]=np.clip(action[:6]*factor,-1,1)
   changed=bool(np.any(action!=original));scaled+=int(changed)
   assert action[6]==original[6]
   if not allowed:assert np.array_equal(action,original)
   _,_,done,trunc,info=e.step(action);speed=np.abs(e.data.qvel[e.vadr[:6]]);torque=np.abs(e.data.qfrc_actuator[e.vadr[:6]]);control=np.abs(e.data.ctrl[e.aids[:6]])
   peak_speed=np.maximum(peak_speed,speed);peak_torque=np.maximum(peak_torque,torque);peak_control=np.maximum(peak_control,control)
   phase_durations[w.phase]=phase_durations.get(w.phase,0.)+dt
   rows.append({'phase':w.phase,'scaled':changed,'scale_eligible':allowed,'original_action':original.tolist(),'arm_speed_rad_s':speed.tolist(),'arm_actuator_torque_nm':torque.tolist(),'arm_control_nm':control.tolist(),**info});actions.append(action);positions.append(e.data.qpos.copy())
   if done or trunc:break
 except Exception as exc:error=repr(exc)
 final=rows[-1] if rows else {};result={'seed':seed,'factor':factor,'success':bool(final.get('is_success') and error is None),'exception':error,'duration_s':float(e.data.time),'wall_seconds':time.perf_counter()-start,'steps':len(rows),'scaled_control_steps':scaled,'phase_durations_s':phase_durations,'max_abs_arm_speed_rad_s':peak_speed.tolist(),'max_abs_arm_actuator_torque_nm':peak_torque.tolist(),'max_abs_arm_control_nm':peak_control.tolist(),'actuator_control_bounds':bounds.tolist(),'max_summed_contact_force_n':float(e.episode_peak_force),'final':final,'handoffs':w.history}
 label=f'factor-{factor:g}-seed-{seed}';np.savez_compressed(out/f'{label}.npz',actions=np.array(actions),qpos=np.array(positions));(out/f'{label}.json').write_text(json.dumps({'result':result,'trace':rows}))
 e.close();print(json.dumps({k:result[k] for k in ['seed','factor','success','duration_s','max_summed_contact_force_n','scaled_control_steps','exception']}),flush=True);return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=Path('runs/machine-speed-v1'));a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(2)
 servo=Path('runs/machine-tending-structured-v2/policy.pt');ppo=Path('runs/machine-seating-ppo-v1/policy.zip');weights=torch.load(servo,weights_only=True);models={k:StructuredServo() for k in weights}
 for k,m in models.items():m.load_state_dict(weights[k]);m.eval()
 policy=PPO.load(ppo,device='cpu');limits={j.attrib['name']:dict(j.find('limit').attrib) for j in ET.parse(URDF).getroot().findall('joint') if j.find('limit') is not None}
 sources=[Path(__file__),Path('src/astrafactory/machine_tending.py'),Path('src/astrafactory/machine_tending_policy.py'),Path('tools/train_machine_seating_ppo.py'),Path('tasks/yam_machine_tending/task.json'),Path('tasks/yam_machine_tending/scene.xml'),servo,ppo,URDF]
 proposal={'scope':'Engineered speed scaling, not new policytraining or hardwarevalidation','seeds':[59000,59003],'split':'existing development cases, not untouchedholdout','factors':[1.,1.5,2.],'scaled_phases':sorted(PHASES),'scaling':'Only arm7delta indices0:6 multiplied andclipped[-1,1] whenfree transport guard passes; jawunchanged; contactphasesunchanged','source_sha256':{str(s):sha(s) for s in sources},'urdf_joint_limits':limits,'telemetry':'50Hz post-control-step sampled velocity andactual actuator generalizedforce, plus control commands; not a substep velocitymaximum','hardware_limit_status':'URDF effort/velocity values1 are placeholders; simulator arm torque ±10Nm is not a validated YAMhardware rating','promotion':'No promotion if reliabilityorforce is worse; anypassing result remains engineeringdevelopment only'}
 (a.out/'proposal.json').write_text(json.dumps(proposal,indent=2));results=[]
 for factor in proposal['factors']:
  for seed in proposal['seeds']:results.append(run(seed,factor,models,policy,a.out))
 comparisons=[]
 for r in results:
  base=next(b for b in results if b['factor']==1 and b['seed']==r['seed'])
  velocities=np.array([float(limits[f'joint{i}']['velocity']) for i in range(1,7)])
  comparisons.append({'factor':r['factor'],'seed':r['seed'],'success':r['success'],'duration_s':r['duration_s'],'seconds_saved':base['duration_s']-r['duration_s'],'percent_faster_cycle':100*(base['duration_s']-r['duration_s'])/base['duration_s'],'force_increase_n':r['max_summed_contact_force_n']-base['max_summed_contact_force_n'],'sampled_arm_velocity_within_placeholder_urdf':bool(np.all(np.array(r['max_abs_arm_speed_rad_s'])<=velocities)),'no_reliability_or_force_regression_on_case':bool(r['success']>=base['success'] and r['max_summed_contact_force_n']<=base['max_summed_contact_force_n']+1e-6)})
 report={'proposal':proposal,'results':results,'comparisons':comparisons,'promoted':False,'frozen_sources_unchanged':all(sha(p)==h for p,h in proposal['source_sha256'].items())}
 (a.out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(comparisons),flush=True)
if __name__=='__main__':main()
