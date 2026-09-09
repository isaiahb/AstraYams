"""Render a camera-matched review from actual saved before/after plant states."""
from pathlib import Path
import json,hashlib
import numpy as np,mujoco,imageio.v2 as imageio
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'assets/workcells/strawberry-specimen'
PATHS={'Before':BASE/'checkpoints/v4-before-leaf-study','After':BASE/'basal-study/v7'}
OUT=BASE/'basal-study'
FONT=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',20)
SMALL=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',15)

def main():
    models={label:mujoco.MjModel.from_xml_path(str(p/'scene.xml')) for label,p in PATHS.items()}
    ds={label:mujoco.MjData(m) for label,m in models.items()}
    renderers={label:mujoco.Renderer(m,580,700) for label,m in models.items()}
    cam=mujoco.MjvCamera();cam.lookat[:]=[0,.052,.312];cam.distance=.25;cam.azimuth=125;cam.elevation=-28
    def frame(label,q,t,phase):
        d=ds[label];m=models[label];d.qpos[:]=q;mujoco.mj_forward(m,d);r=renderers[label];r.update_scene(d,cam)
        im=Image.fromarray(r.render());draw=ImageDraw.Draw(im);draw.rectangle((0,0,700,84),fill='#17251d')
        draw.text((18,12),label+' · '+('old crown attachment' if label=='Before' else 'supported, tapered stalk base'),font=FONT,fill='white')
        draw.text((18,42),f'{phase} · t = {t:.2f} s · mechanics uncalibrated',font=SMALL,fill='#d5dfcd')
        j=m.joint('petiole_left_0_bend');a=j.qposadr[0];angle=float(2*np.arccos(np.clip(abs(q[a]),0,1))*180/np.pi)
        draw.text((18,63),f'Left stalk base rotation: {angle:.1f}°',font=SMALL,fill='#d5dfcd')
        return np.array(im)
    rest={label:np.load(p/'rest/rollout.npz') for label,p in PATHS.items()}
    contact={label:np.load(p/'basal/rollout.npz') for label,p in PATHS.items()}
    still=np.concatenate([frame(label,z['qpos'][-1],z['t'][-1],'Gravity-settled') for label,z in rest.items()],axis=1)
    Image.fromarray(still).save(OUT/'crown-before-after.png')
    with imageio.get_writer(OUT/'crown-before-after.mp4',fps=25,codec='libx264',quality=8,macro_block_size=2) as writer:
        for _ in range(30):writer.append_data(still)
        for sec in np.arange(0,min(z['t'][-1] for z in contact.values()),1/25):
            panels=[]
            for label,z in contact.items():
                i=int(np.argmin(abs(z['t']-sec)))
                panels.append(frame(label,z['qpos'][i],z['t'][i],'Physical probe contact'))
            last=np.concatenate(panels,axis=1);writer.append_data(last)
        # Hold the actual end state; do not jump back to an earlier plant pose.
        for _ in range(20):writer.append_data(last)
    evidence={}
    for label,p in PATHS.items():
        m=models[label];q=rest[label]['qpos'][-1];angles={}
        for name in ['petiole_left','petiole_front','peduncle']:
            j=m.joint(name+'_0_bend');a=j.qposadr[0]
            angles[name]={'rotation_deg':float(2*np.arccos(np.clip(abs(q[a]),0,1))*180/np.pi),'base_stiffness_nm_per_rad':float(m.jnt_stiffness[j.id])}
        evidence[label]={'model_sha256':hashlib.sha256((p/'scene.xml').read_bytes()).hexdigest(),'root_joint_rotations_at_rest':angles,'rest':json.loads((p/'rest/result.json').read_text()),'basal_contact':json.loads((p/'basal/result.json').read_text()),'basal_control':json.loads((p/'basal-control/result.json').read_text())}
    evidence['interpretation']='Root angles are relative to each model’s unloaded joint orientation, not absolute emergence angles. Both the growth curve and cross section changed. No real-plant stiffness measurement is claimed. Probe trajectories share timing, direction and relative stroke; they are centered on each settled target, so absolute positions differ.'
    evidence['scope']='The old desktop app and original whole-plant artifact remain untouched. This is a separately inspectable simulation candidate.'
    (OUT/'comparison-results.json').write_text(json.dumps(evidence,indent=2))
    for r in renderers.values():r.close()
    print(OUT/'crown-before-after.mp4')

if __name__=='__main__':main()
