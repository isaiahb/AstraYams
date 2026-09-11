"""Export recorded packing contact tests; viewer does not synthesize motion."""
from pathlib import Path
import argparse,json,shutil
import mujoco as mj
import numpy as np
import render_strawberry_specimen as exporter
ROOT=Path(__file__).resolve().parents[1];BENCH=ROOT/'runs/tower-lift-v9/gate-bench'

def main(cases):
    exporter.P=BENCH;exporter.export(cases)
    m=mj.MjModel.from_xml_path(str(BENCH/'scene.xml'))
    for case in cases:
        folder=BENCH/case;z=np.load(folder/'rollout.npz');p=json.loads((folder/'replay.json').read_text());tr=json.loads((folder/'trace.json').read_text())
        p['case_name']=case
        p.update(scope='Scripted finite-torque contact commissioning. Free tool, passive hinge and deformable net. No PPO or calibrated fruit-damage claim.',edges=m.flex_elem.reshape(-1,2).tolist(),result=json.loads((folder/'result.json').read_text()))
        for f,i in zip(p['frames'],range(0,len(z['t']),2)):
            f['net']=z['flex_vertices'][i].round(7).tolist();f['metrics']=tr[i]
        for o in p['objects']:
            if o['body'] in ['pack_clamshell','pack_lid']:o['opacity']=.25
        (folder/'replay.json').write_text(json.dumps(p,separators=(',',':')))
    (BENCH/'cases.json').write_text(json.dumps(cases))
    shutil.copy2(ROOT/'tools/templates/packing-gate-review.html',BENCH/'index.html')
    (BENCH.parent/'index.html').write_text('''<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=gate-bench/index.html"><a href="gate-bench/index.html">Open V9 contact commissioning</a>''')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('cases',nargs='+');a=p.parse_args();main(a.cases)
