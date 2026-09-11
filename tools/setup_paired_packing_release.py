"""Reuse a preserved isolated release start, mapping states by joint names."""
import argparse,json
from pathlib import Path
import mujoco as mj
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def main(source,bench):
    old=mj.MjModel.from_xml_path(str(source/'scene.xml'));m=mj.MjModel.from_xml_path(str(bench/'scene.xml'));d=mj.MjData(m)
    z=np.load(source/'release-initial.npz')
    for j in range(old.njnt):
        k=mj.mj_name2id(m,mj.mjtObj.mjOBJ_JOINT,old.joint(j).name)
        if k<0:continue
        count={0:7,1:4,2:1,3:1}[int(old.jnt_type[j])]
        d.qpos[m.jnt_qposadr[k]:m.jnt_qposadr[k]+count]=z['qpos'][old.jnt_qposadr[j]:old.jnt_qposadr[j]+count]
    for a in range(old.nu):d.ctrl[m.actuator(old.actuator(a).name).id]=z['ctrl'][a]
    np.savez_compressed(bench/'release-initial.npz',qpos=d.qpos,ctrl=d.ctrl)
    plan=json.loads((source/'release-plan.json').read_text());build=json.loads((bench/'build.json').read_text())
    for w in plan['waypoints']:
        if w['time_s'] in [3,5,6]:w['right']=build['low_access_joint_pose']
    plan['scope']='Isolated 580 mm net-rim release, initialized near the pack; no transport or learned-policy claim. Paired rollers and passive spring gate.'
    plan['initialization_source']=str(source)
    (bench/'release-plan.json').write_text(json.dumps(plan,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-bench',type=Path,default=ROOT/'runs/tower-lift-v9/gate-bench');p.add_argument('--bench',type=Path,required=True);a=p.parse_args();main(a.source_bench.resolve(),a.bench.resolve())
