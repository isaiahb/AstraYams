"""Export three explicit CAD articulation poses, never label them physics."""
import json
import shutil
from pathlib import Path
import mujoco
import numpy as np
import render_strawberry_specimen as exporter

ROOT=Path(__file__).resolve().parents[1]

def main():
    out=ROOT/'runs/tower-lift-v5'; folder=out/'so101'
    m=mujoco.MjModel.from_xml_path(str(folder/'scene.xml'))
    initial=np.load(folder/'initial.npz')['qpos']
    poses=[]
    for angle in [14,7,0]:
        q=initial.copy();q[m.joint('left_gripper').qposadr[0]]=np.deg2rad(angle)
        poses.extend([q.copy(),q.copy()])
    layout=folder/'layout';layout.mkdir(exist_ok=True)
    np.savez_compressed(layout/'rollout.npz',qpos=poses,t=[0,0,1,1,2,2])
    exporter.P=folder;exporter.export(['layout'])
    payload=json.loads((layout/'replay.json').read_text())
    payload.update(label='static_CAD_fit_review',scope='CAD fit review · left AEROBERRY grip-cut / right stock SO-101 jaw · no cutting or contact simulation',
                   audit={},training_ready=False)
    for frame,angle in zip(payload['frames'],[14,7,0]):
        frame['phase']=f'CAD pose: {angle} degrees open; forward kinematics only'
    (layout/'replay.json').write_text(json.dumps(payload,separators=(',',':')))
    (folder/'replay.json').write_text(json.dumps(payload,separators=(',',':')))
    shutil.copytree(ROOT/'runs/tower-lift-v4/references',out/'references',dirs_exist_ok=True)
    shutil.copy2(ROOT/'assets/end-effectors/aeroberry-so101-v04/renders/assembly.png',out/'references/tool.png')
    shutil.copy2(ROOT/'tools/templates/aeroberry-mount-review.html',out/'index.html')
    print(out/'index.html')

if __name__=='__main__':main()
