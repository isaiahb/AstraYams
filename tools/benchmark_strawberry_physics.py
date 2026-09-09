"""Measure local simulation cost separately from rendering and Python logging."""
import argparse,json,platform,time
from pathlib import Path
import mujoco,numpy as np
p=argparse.ArgumentParser();p.add_argument('model_dir',type=Path);p.add_argument('--kind',default='rest');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
m=mujoco.MjModel.from_xml_path(str(a.model_dir/'scene.xml'));q=np.load(a.model_dir/a.kind/'rollout.npz')['qpos'][-1];samples=[]
for repeat in range(3):
    d=mujoco.MjData(m);d.qpos[:]=q
    d.ctrl[:]=[d.qpos[m.joint(f'probe_{i}').qposadr[0]] for i in range(3)]
    mujoco.mj_forward(m,d);start=time.perf_counter();mujoco.mj_step(m,d,nstep=round(2/m.opt.timestep));elapsed=time.perf_counter()-start
    samples.append({'wall_s':elapsed,'simulated_s':2.,'simulated_per_wall_s':2/elapsed,'runtime_warnings':[int(w.number) for w in d.warning]})
a.output.write_text(json.dumps({'protocol':'three fresh resets to saved final pose with zero velocity and stationary probe command; headless mj_step; no Python contact logging/rendering','machine':platform.machine(),'mujoco':mujoco.__version__,'model':str(a.model_dir),'timestep_s':float(m.opt.timestep),'nv':m.nv,'ngeom':m.ngeom,'nflex':m.nflex,'samples':samples,'scope':'Local cost measurement, not a biological-accuracy or policy-throughput result.'},indent=2))
print(a.output)
