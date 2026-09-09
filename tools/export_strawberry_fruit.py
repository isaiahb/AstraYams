"""Reuse the standalone specimen viewer for orbitable recorded fruit dynamics.

Only generated study assets are written; no desktop/product source is edited.
"""
import json
import re
from pathlib import Path
import numpy as np
import mujoco
import render_strawberry_specimen as export_base

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'assets/workcells/strawberry-specimen/fruit-study'


def main():
    export_base.P=P/'v14';export_base.export()
    source=json.loads((P/'v14/rest/replay.json').read_text())
    m=mujoco.MjModel.from_xml_path(str(P/'release/scene.xml'));d=mujoco.MjData(m)
    original=mujoco.MjModel.from_xml_path(str(P/'v14/scene.xml'))
    # Shared body-local meshes must stay valid when the fruit becomes free.
    for i in range(original.ngeom):
        j=m.geom(original.geom(i).name).id
        if not np.allclose(original.geom_pos[i],m.geom_pos[j],atol=1e-10) or not np.allclose(original.geom_quat[i],m.geom_quat[j],atol=1e-10):
            raise RuntimeError('Body-local geometry changed across release topology')
    for name in ['elastic-release','elastic-control','history-release','history-control']:
        path=P/'release'/name;z=np.load(path/'rollout.npz');frames=[]
        for i in range(0,len(z['t']),4):
            d.qpos[:]=z['qpos'][i];mujoco.mj_forward(m,d)
            bodies={m.body(j).name or 'world':dict(position=d.xpos[j].round(8).tolist(),quaternion=d.xquat[j][[1,2,3,0]].round(8).tolist()) for j in range(m.nbody)}
            frames.append(dict(time=float(z['t'][i]),phase='Attached' if z['attachment_active'][i] else 'Diagnostic attachment release; no blade',bodies=bodies))
        replay=dict(source);replay.update(frames=frames,scope='Recorded finite-body dynamics. Diagnostic calyx release, not cutting. Uncalibrated material hypotheses.');(path/'replay.json').write_text(json.dumps(replay,separators=(',',':')))
    html=(ROOT/'assets/workcells/strawberry-specimen/parametric-study/v13/index.html').read_text()
    html=re.sub(r'<title>.*?</title>','<title>Fruit orientation and unloading study</title>',html)
    html=re.sub(r'<h1>.*?</h1>','<h1>Fruit orientation &amp; unloading</h1>',html)
    html=re.sub(r'<nav aria-label="Physics recordings">.*?</nav>', '<nav aria-label="Physics recordings"><button class="active" data-kind="v14/rest">Corrected fruit orientation</button><button data-kind="release/elastic-release">A · Original rest shape · release</button><button data-kind="release/history-release">B · Rest shape + stiffness · release</button><button data-kind="release/elastic-control">A · Uncut control</button><button data-kind="release/history-control">B · Uncut control</button></nav>',html)
    html=html.replace('Multi-reference morphology hypothesis with age-dependent petiole mechanics.','Fruit material-frame correction and controlled unloading. B changes BOTH truss rest curvature and stiffness before its trial; it is not calibrated growth. Release disables a calyx bond at 1 s; no blade/fracture is modeled.')
    start=html.index("if(kind==='basal')")
    end=html.index('orbit.update();clock=',start)
    html=html[:start]+"orbit.target.set(0,-.04,.15);cam.position.set(.25,-.60,.28);"+html[end:]
    html=html.replace("kind==='rest'","kind==='v14/rest'")
    html=html.replace("document.getElementById('video').href=kind+'/demo.mp4'","document.getElementById('video').href=kind==='v14/rest'?'fruit-orientation-comparison.png':'release-comparison.mp4'")
    start=html.index(' const hits=Object.keys(report.probe_contacts')
    end=html.index("document.getElementById('error').textContent='';",start)
    html=html[:start]+" document.getElementById('status').textContent=kind==='v14/rest'?'Corrected attachment frame · gravity settled · mechanics uncalibrated':'Recorded dynamics · '+(kind.includes('history')?'B: different rest curvature AND stiffness':'A: original rest shape')+' · '+(kind.includes('control')?'uncut control':'diagnostic release at 1 s')+' · no blade simulation';"+html[end:]
    html=html.replace("fetch('reference-graph.json')","fetch('v14/reference-graph.json')").replace("load('rest')","load('v14/rest')")
    html=html.replace('Open video recording','Open review media').replace('Contact evidence','Experiment report')
    html=html.replace('href="specimen-settled.glb"','href="v14/specimen-settled.glb"')
    (P/'index.html').write_text(html)
    if not (P/'reference').exists():(P/'reference').symlink_to('../reference',target_is_directory=True)
    print(P/'index.html')


if __name__=='__main__':main()
