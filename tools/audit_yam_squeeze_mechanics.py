"""Independently replay the actuator integration and inspect every physics step.

Unlike the training score (50 Hz), this audit samples squeeze at 500 Hz. The
recorded qpos must match at every action boundary, guarding duplicated-loop drift.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np,mujoco
from astrafactory.contact_curriculum import CurriculumEnv
from astrafactory.grip_regulation import TASK
from astrafactory.squeeze_skill import squeeze_load
from astrafactory.skill_randomization import SkillRandomization


def audit(run,row):
    e=CurriculumEnv(TASK);sample=row.get('domain_randomization')
    if sample:SkillRandomization(e,sample['profile'],'stress').reset(seed=row['seed'],domain_seed=sample['domain_seed'])
    else:e.reset(seed=row['seed'])
    saved=np.load(run/f"chain-{row['seed']}.npz");m,d=e.model,e.data
    peak=0.;minimum=0.;max_error=0.;max_speed=np.zeros(7);max_effort=np.zeros(7);n=0
    for action,reference in zip(saved['actions'],saved['qpos']):
        e.target=np.clip(e.target+np.clip(action,-1,1)*e.scales,e.limits[:,0],e.limits[:,1])
        for _ in range(e.frame_skip):
            control=e.kp*(e.target-d.qpos[e.qadr])-e.kd*d.qvel[e.vadr]+d.qfrc_bias[e.vadr]
            bounds=m.actuator_ctrlrange[e.aids];d.ctrl[e.aids]=np.clip(control,bounds[:,0],bounds[:,1])
            mujoco.mj_step(m,d);load=float(squeeze_load(e).sum());n+=1
            peak=max(peak,load);minimum=min(minimum,load)
            max_speed=np.maximum(max_speed,np.abs(d.qvel[e.vadr]));max_effort=np.maximum(max_effort,np.abs(d.actuator_force[e.aids]))
        max_error=max(max_error,float(np.max(abs(d.qpos-reference))))
    limits=np.max(abs(m.actuator_ctrlrange[e.aids]),axis=1)
    result=dict(seed=row['seed'],samples=n,sample_hz=1/m.opt.timestep,max_qpos_error=max_error,
                max_axial_squeeze_n=peak,min_axial_squeeze_n=minimum,max_joint_speed_rad_s_and_jaw_m_s=max_speed.tolist(),
                max_actuator_effort_nm_and_jaw_n=max_effort.tolist(),effort_limits_respected=bool(np.all(max_effort<=limits+1e-9)),
                passed=bool(max_error<1e-8 and peak<=8 and np.all(max_effort<=limits+1e-9)))
    e.close();return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args()
    report=json.loads((a.run/'report.json').read_text());stress=json.loads((a.run/'stress/report.json').read_text())
    rows=[audit(a.run,r) for r in report['continuous_chains']]
    rows += [audit(a.run/'stress/ppo',r) for r in stress['methods']['ppo']['trials']]
    out=dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),trials=rows,passed=all(r['passed'] for r in rows),
             limitation='Tests modeled motor bounds and simulated forces, not actual YAM hardware limits, sensor calibration or sim-to-real fidelity.')
    (a.run/'mechanics-audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(dict(passed=out['passed'],trials=len(rows),peak_squeeze_n=max(r['max_axial_squeeze_n'] for r in rows))),flush=True)
    assert out['passed']

if __name__=='__main__':main()
