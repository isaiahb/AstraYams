"""Seeded anatomical variation, compiled into contact geometry and mechanics.

Engineering sampling priors, not fitted population statistics. No camera changes
or render-only fruit relocation. Gravity supplies the loaded plant configuration.
"""
from pathlib import Path
import argparse,copy,json,time
import numpy as np,mujoco
from strawberry_morphology import measured_spec
from build_strawberry_specimen import build
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'assets/workcells/strawberry-specimen/surface-study/v4'

def specimen(seed):
 rng=np.random.default_rng(seed);s=json.loads((BASE/'reference-graph.json').read_text());vigor=float(rng.uniform(.86,1.14));spread=float(rng.uniform(.80,1.22));cultivar=int(rng.integers(0,6));count=int(rng.integers(2,8));turn=float(rng.uniform(-.22,.22));R=np.array([[np.cos(turn),-np.sin(turn),0],[np.sin(turn),np.cos(turn),0],[0,0,1]])
 leaves=copy.deepcopy(s['leaves']);nleaf=int(rng.integers(4,9));selected=list(rng.permutation(len(leaves)))[:min(nleaf,len(leaves))]
 while len(selected)<nleaf:selected.append(int(rng.integers(len(leaves))))
 s['leaves']=[];crown=np.array(s['crown_m'])
 for i,j in enumerate(selected):
  leaf=copy.deepcopy(leaves[j]);leaf['id']=f'population_leaf_{i}';angle=turn+float(rng.uniform(-.25,.25));Q=np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]]);scale=np.array([vigor*spread,vigor*spread,vigor])
  leaf['tip']=(crown+Q@((np.array(leaf['tip'])-crown)*scale)).tolist();leaf['length']*=vigor*rng.uniform(.92,1.08);leaf['shaft_radius_m']*=vigor;leaf['yaw']+=angle;leaf['pitch']+=rng.uniform(-.14,.14)
  for key in ['attachment_m','control_points_m']:
   if key in leaf.get('growth',{}):leaf['growth'][key]=(np.asarray(leaf['growth'][key])*scale@Q.T).tolist()
  s['leaves'].append(leaf)
 branches=copy.deepcopy(s['truss']);terminals=[b for b in branches if 'fruit' in b];target=next(b for b in terminals if b['fruit']['id']=='secondary_b');others=[b for b in terminals if b is not target];chosen=[target]+[others[i] for i in rng.permutation(len(others))[:count-1]]
 while len(chosen)<count:
  b=copy.deepcopy(rng.choice(others));i=len(chosen);b['id']=f'extra_stalk_{i}';b['fruit']['id']=f'extra_{i}';b['parent']='peduncle' if rng.random()<.5 else 'secondary';b['unloaded_delta']=[float(rng.uniform(-.09,.085)),float(rng.uniform(-.09,-.035)),float(rng.uniform(-.03,.015))];chosen.append(b)
 chosenids={b['id'] for b in chosen};s['truss']=[b for b in branches if 'fruit' not in b or b['id'] in chosenids]+[b for b in chosen if b['id'].startswith('extra_')]
 for b in s['truss']:
  delta=np.array(b['unloaded_delta']);delta*=np.array([vigor*spread,vigor,vigor])*rng.uniform(.87,1.13);b['unloaded_delta']=(R@delta).tolist();b['radius']*=vigor*rng.uniform(.92,1.08)
  if 'fruit' not in b:continue
  old=b['fruit'];maturity='red' if old['id']=='secondary_b' else str(rng.choice(['red','turning','green'],p=[.45,.25,.30]));mass=float(rng.uniform(*{'red':(.010,.023),'turning':(.005,.014),'green':(.0025,.007)}[maturity]))*vigor**3
  f=measured_spec(dict(id=old['id'],mass=mass,maturity=maturity),f'{cultivar}-0',depth=float(rng.uniform(.82,.98)),depth_bend=float(rng.uniform(-.08,.10)),blend_id=f'{cultivar}-{int(rng.integers(1,3))}',blend_weight=float(rng.uniform(.05,.65)),phase=float(rng.uniform(0,6.28)))
  f['surface_recipe']=4;f['calyx_parameters']=dict(span_scale=float(rng.uniform(.8,1.05)),tip_curl_m=float(rng.uniform(-.0015,.0015)),sepals=int(rng.choice([5,6])));b['fruit']=f
 s['mechanics']['truss_young_pa']*=float(rng.uniform(.85,1.15));s['parameterization']=dict(seed=seed,fruit_count=count,leaf_count=nleaf,cultivar_outline_family=cultivar,vigor=vigor,spread=spread,azimuth_rad=turn,scope=__doc__,split='train' if seed<72000 else 'holdout');s['scope']=__doc__
 return s

def generate(seed,out):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);s=specimen(seed);path=out/'reference-graph.json';path.write_text(json.dumps(s,indent=2)+'\n');build(out,path,detailed_fruit=True)
 m=mujoco.MjModel.from_xml_path(str(out/'scene.xml'));d=mujoco.MjData(m);source=mujoco.MjModel.from_xml_path(str(BASE/'scene.xml'));z=np.load(BASE/'initial-state.npz')
 # Start shared material coordinates from the previous settled specimen, then
 # solve a fresh equilibrium. New organs start from their unloaded state.
 for j in range(m.njnt):
  name=m.joint(j).name;k=mujoco.mj_name2id(source,mujoco.mjtObj.mjOBJ_JOINT,name)
  if k<0:continue
  n={0:7,1:4,2:1,3:1}[int(m.jnt_type[j])];d.qpos[m.jnt_qposadr[j]:m.jnt_qposadr[j]+n]=z['qpos'][source.jnt_qposadr[k]:source.jnt_qposadr[k]+n]
 for i in range(3):d.ctrl[m.actuator(f'probe_{i}').id]=.8;d.qpos[m.joint(f'probe_{i}').qposadr[0]]=.8
 pg=m.geom('probe_surface').id;m.geom_contype[pg]=m.geom_conaffinity[pg]=0
 mujoco.mj_forward(m,d);fruitids=[m.body('fruit_'+b['fruit']['id']).id for b in s['truss'] if 'fruit' in b];prev=d.xpos[fruitids].copy();start=time.time();span=float('inf')
 for i in range(40):
  mujoco.mj_step(m,d,nstep=round(.5/m.opt.timestep));mujoco.mj_forward(m,d);span=float(np.max(np.linalg.norm(d.xpos[fruitids]-prev,axis=1)));prev=d.xpos[fruitids].copy()
  if any(w.number for w in d.warning):raise ValueError(f'Solver warning on population seed {seed}')
  if i>12 and span<.0001 and np.max(abs(d.qvel))<.005:break
 np.savez_compressed(out/'initial-state.npz',qpos=d.qpos,qvel=d.qvel,ctrl=d.ctrl)
 manifest=dict(**s['parameterization'],settled_seconds=float(d.time),last_half_second_fruit_motion_m=span,max_generalized_speed=float(np.max(abs(d.qvel))),quiet=bool(span<.0001 and np.max(abs(d.qvel))<.005),fruit=[dict(id=b['fruit']['id'],maturity=b['fruit']['maturity'],mass_kg=b['fruit']['mass'],position_m=d.xpos[m.body('fruit_'+b['fruit']['id']).id].tolist(),outline=b['fruit']['morphology']['id']) for b in s['truss'] if 'fruit' in b],wall_s=time.time()-start)
 (out/'population.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:v for k,v in manifest.items() if k in ['seed','fruit_count','leaf_count','quiet','wall_s']}),flush=True);return manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--seeds',type=int,nargs='+',default=[71001,71002,71003,72001,72002,72003]);p.add_argument('--out',type=Path,default=Path('runs/harvest-skill-suite/population'));a=p.parse_args();rows=[]
 for seed in a.seeds:rows.append(generate(seed,a.out/str(seed)))
 (a.out/'manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
