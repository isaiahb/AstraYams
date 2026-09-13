"""Deterministic organ-history model, preserving parentage across developmental snapshots.

No calendar growth rates, physiological calibration, whole-plant mechanical
equilibrium, robot contact, or pruning optimization are claimed.
"""
from pathlib import Path
import hashlib
import json
import math
import shutil
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / 'runs/hemp-development-v2'
C = json.loads((HERE / 'config.json').read_text())
A = C['architecture']


def smooth(x):
    x = np.clip(x, 0., 1.)
    return x*x*(3-2*x)


def unit(x):
    x = np.array(x, dtype=float)
    return x / max(np.linalg.norm(x), 1e-12)


def profiles():
    """Reuse the existing attributed Futura75 coordinate measurements."""
    d = HERE.parent / 'reference-data'
    raw = np.loadtxt(d/'out_FUT75_2_12_4a_7.txt')
    lm = np.loadtxt(d/'land_FUT75_2_12_4a_7.txt')
    indices = [int(np.argmin(np.linalg.norm(raw-p, axis=1))) for p in lm]
    result = []
    for i in range(7):
        a,b,tip = indices[2*i],indices[2*i+1],indices[14+i]
        ids = np.arange(a,b+1 if b>=a else b+len(raw)+1)%len(raw)
        k = int(np.where(ids==tip)[0][0])
        direction = unit(lm[14+i]-lm[-1])
        normal = np.array([-direction[1],direction[0]])
        scale = np.linalg.norm(lm[14+i]-lm[-1])
        xy = np.column_stack([(raw[ids]-lm[-1])@direction,(raw[ids]-lm[-1])@normal])/scale
        edges = []
        for edge in [xy[:k+1],xy[k:]]:
            edge = np.vstack([[0,0],edge,[1,0]])
            edge = edge[np.argsort(edge[:,0])]
            edges.append(np.interp(np.linspace(0,1,81),edge[:,0],edge[:,1]))
        lo,hi = np.minimum(*edges),np.maximum(*edges)
        result.append({'low':lo.tolist(),'high':hi.tolist()})
    return result


def make_specimen(seed):
    ref=json.loads((HERE/'reference.json').read_text())
    rng=np.random.default_rng(seed)
    scale=ref['scale']['working_axis_height_m']/(827-75)
    axes=[];leaves=[];lookup={}
    for trace in ref['axes']:
        pts=np.array(trace['xy'],float)
        depth=trace['depth']*(1 if seed==17 else rng.uniform(.55,1.45))
        xyz=np.column_stack([(pts[:,0]-330)*scale,
                             depth*np.sin(np.linspace(0,np.pi/2,len(pts))),
                             (827-pts[:,1])*scale])
        order=0 if trace['parent'] is None else 1
        if order:
            parent=lookup[trace['parent']]
            xyz[:,1]+=parent['final_points'][trace['node']][1]
            born=parent['births'][trace['node']-1]+9
        else: born=0
        delta=np.diff(xyz,axis=0);lengths=np.linalg.norm(delta,axis=1)
        births=[float(born+(2.8 if order==0 else 3.5)*j) for j in range(len(lengths))]
        radius=.0035 if order==0 else .0015*(1-.40*trace['node']/17)
        item={'id':trace['id'],'parent':trace['parent'],'parent_node':trace['node'],
              'born':born,'order':order,'births':births,'lengths':lengths.tolist(),
              'directions':(delta/lengths[:,None]).tolist(),'radius':radius,
              'final_points':xyz.tolist(),'confidence':trace['confidence']}
        axes.append(item);lookup[item['id']]=item
        count=len(lengths)
        for j in range(count):
            # Leaves and laterals share explicit nodes; no floating foliage clusters.
            fraction=j/max(1,count-1)
            size=(.125 if order==0 else .095)*(1-.57*fraction**1.7)*rng.uniform(.82,1.18)
            phi=(0 if j%2 else np.pi)+rng.normal(0,.38) if order==0 else np.arctan2(delta[j,1],delta[j,0])+(-1 if j%2 else 1)*rng.uniform(.3,1.15)
            # Distinct developmental rank, not a universal node threshold.
            nleaf=7 if fraction<.5 else 5 if fraction<.78 else 3
            leaves.append({'id':f"{item['id']}/leaf-{j}",'axis':item['id'],'node':j+1,
                'born':births[j]+2,'length':float(size),'phi':float(phi),
                'roll':float(rng.uniform(-.70,.65)),
                'droop':float(rng.uniform(.06,.19)),
                'pitch':float(np.clip(rng.normal(-.30,.34),-.85,.38)+.1*fraction),
                'width_factor':float(rng.uniform(.83,1.19)),
                'asymmetry':float(rng.uniform(-.14,.14)),
                'petiole_ratio':float(rng.uniform(.35,.70)),
                'leaflets':nleaf,'tone':float(rng.uniform(.88,1.08)),
                'lifetime_steps':float(rng.uniform(105,130))})
    return {'seed':seed,'vigor':1.,'axes':axes,'leaves':leaves,
            'status':'photo-constrained projected axes; unknown depths and procedural foliage'}


def snapshot(spec,t,removals=(),event=False):
    axis_state = {}; leaf_state = []
    for ax in spec['axes']:
        origin = np.zeros(3) if ax['parent'] is None else np.array(axis_state[ax['parent']]['points'][ax['parent_node']])
        points = [origin];radii = []
        for j,(birth,length) in enumerate(zip(ax['births'],ax['lengths'])):
            age = max(0,t-birth)
            expansion = float(smooth(age/A['internode_expansion_steps']))
            # Evolving intrinsic orientation is a hypothesis about development,
            # not an elastic gravity-deflection result.
            f = j/max(1,len(ax['births'])-1)
            direction = np.array(ax['directions'][j])
            points.append(points[-1]+direction*length*expansion)
            rad = (.00015+ax['radius']*(1-math.exp(-age/24))*(1-.65*f))*math.sqrt(expansion)
            radii.append(float(rad))
        mass = 0.; lengths_now = np.linalg.norm(np.diff(points,axis=0),axis=1)
        for j,(L,r) in enumerate(zip(lengths_now,radii)):
            r1=radii[min(j+1,len(radii)-1)]
            mass += math.pi*(r*r+r*r1+r1*r1)/3*L*A['fresh_stem_density_kg_m3']
        age = max(0,t-ax['born'])
        # Export a prior, not a calibrated age->modulus curve.
        E = A['illustrative_stem_E_Pa']*(.35+.65*smooth(age/65))
        axis_state[ax['id']]={'id':ax['id'],'points':np.array(points).round(7).tolist(),'radii':radii,
                             'age':age,'mass_kg':float(mass),'E_Pa':float(E),
                             'EI_Nm2':[float(E*math.pi*r**4/4) for r in radii],
                             'flower_scale':float(smooth((t-ax['births'][-1]-18)/30)) }
    area=mass_leaf=0.;live=0
    for leaf in spec['leaves']:
        age = max(0,t-leaf['born'])
        s = float(smooth(age/A['leaf_expansion_steps']))
        removed = event and t>=C['event']['at_step'] and leaf['id'] in removals
        senescence = float(smooth((age-leaf['lifetime_steps']+18)/18))
        length = leaf['length']*s
        # Geometry-based area computed from the same measured outline profiles.
        rel = {7:[.36,.64,.87,1,.86,.62,.34],5:[.60,.87,1,.85,.60],3:[.72,1,.71]}[leaf['leaflets']]
        inds = {7:list(range(7)),5:[1,2,3,4,5],3:[2,3,4]}[leaf['leaflets']]
        leafarea=sum(float(np.trapezoid(np.array(P[i]['high'])*(1+leaf.get('asymmetry',0))-np.array(P[i]['low'])*(1-leaf.get('asymmetry',0)),np.linspace(0,1,81)))*(length*r)**2*leaf.get('width_factor',1) for i,r in zip(inds,rel))
        active=s>.001 and not removed
        if active:
            area+=leafarea;mass_leaf+=leafarea*A['leaf_area_mass_kg_m2'];live+=1
        at=axis_state[leaf['axis']]['points'][leaf['node']]
        leaf_state.append({'id':leaf['id'],'at':at,'scale':s,'age':age,'senescence':senescence,
                           'removed':removed,'active':active,'area_m2':float(leafarea),
                           'mass_kg':float(leafarea*A['leaf_area_mass_kg_m2'])})
    p=np.concatenate([v['points'] for v in axis_state.values()])
    main=np.array(axis_state['main']['points'])
    grown=np.linalg.norm(np.diff(main,axis=0),axis=1)
    grown=grown[grown>1e-6]
    first_branch=min(a['parent_node'] for a in spec['axes'] if a['parent']=='main')
    return {'step':t,'axes':list(axis_state.values()),'leaves':leaf_state,
            'metrics':{'active_leaves':live,'leaf_area_m2':float(area),'leaf_mass_kg':float(mass_leaf),
                       'stem_mass_kg':float(sum(a['mass_kg'] for a in axis_state.values())),
                       'axis_height_m':float(p[:,2].max()),'axis_width_m':float(np.ptp(p[:,0])),
                       'axis_depth_m':float(np.ptp(p[:,1])),
                       'trunk_to_first_branch_m':float(main[first_branch,2]),
                       'mean_main_internode_m':float(grown.mean()) if len(grown) else 0}}


def audit(spec,states,removed):
    lookup={a['id']:a for a in spec['axes']};leaflookup={l['id']:l for l in spec['leaves']}
    errs=[];nonfinite=0;birtherrors=0
    for s in states:
        sm={a['id']:a for a in s['axes']}
        for a in s['axes']:
            p=np.array(a['points']);nonfinite+=int(not np.isfinite(p).all())
            desc=lookup[a['id']]
            if desc['parent']:
                q=sm[desc['parent']]['points'][desc['parent_node']]
                errs.append(float(np.linalg.norm(p[0]-q)))
                parent=lookup[desc['parent']]
                birtherrors+=int(desc['born']<parent['births'][desc['parent_node']-1])
            for j,birth in enumerate(desc['births']):
                if s['step']<=birth:assert np.linalg.norm(p[j+1]-p[j])<2e-7
        for l in s['leaves']:
            desc=leaflookup[l['id']]
            errs.append(float(np.linalg.norm(np.array(l['at'])-sm[desc['axis']]['points'][desc['node']])))
    before=snapshot(spec,C['event']['at_step'],removed,False)
    after=snapshot(spec,C['event']['at_step'],removed,True)
    assert before['axes']==after['axes'], 'Event changed retained axis geometry or material state'
    # Event affects membership, not a new random sample or regrowth from zero.
    changed=[a['id'] for a,b in zip(before['leaves'],after['leaves']) if a['active']!=b['active']]
    assert set(changed)==set(removed)
    assert len({a['id'] for a in spec['axes']})==len(spec['axes'])
    assert len({a['id'] for a in spec['leaves']})==len(spec['leaves'])
    assert not nonfinite and not birtherrors
    assert max(errs,default=0)<3e-7
    final=snapshot(spec,100)
    projected_fit_error=max(float(np.max(np.linalg.norm(np.array(ax['points'])[:,[0,2]]-np.array(lookup[ax['id']]['final_points'])[:,[0,2]],axis=1))) for ax in final['axes'])
    assert projected_fit_error < 1e-6
    return {'projected_trace_roundtrip_error_m':projected_fit_error,'fit_is_independent_validation':False,'seed':spec['seed'],'axes':len(spec['axes']),'leaf_organs':len(spec['leaves']),
            'max_attachment_error_m':max(errs,default=0),'parent_birth_order_valid':True,
            'unborn_internodes_have_zero_length':True,'retained_scaffold_identical_across_event':True,
            'removed_leaf_count':len(removed),'removed_leaf_mass_kg':before['metrics']['leaf_mass_kg']-after['metrics']['leaf_mass_kg'],
            'biological_growth_validated':False,'material_values_measured':False,'whole_plant_equilibrium_solved':False}


P = profiles()
PROFILE_AREAS=[float(np.trapezoid(np.array(x['high'])-x['low'],np.linspace(0,1,81))) for x in P]

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    reports=[];variants=[]
    for seed in C['seeds']:
        spec=make_specimen(seed)
        pre=snapshot(spec,C['event']['at_step'])
        removed=[l['id'] for l in pre['leaves'] if l['active'] and l['at'][2]<.38]
        states=[snapshot(spec,t,removed,False) for t in range(0,101,C['snapshot_stride'])]
        reports.append(audit(spec,states,removed))
        variants.append({'specimen':spec,'removed_ids':removed,'states':states})
    data={'config':C,'profiles':P,'variants':variants}
    (OUT/'development.json').write_text(json.dumps(data,separators=(',',':')))
    for name in ['index.html','viewer.js']:
        shutil.copy2(HERE/name,OUT/name)
    report={'status':'structural and bookkeeping checks only','specimens':reports,
            'config_sha256':hashlib.sha256((HERE/'config.json').read_bytes()).hexdigest(),
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'reference_sha256':hashlib.sha256((HERE/'reference.json').read_bytes()).hexdigest(),
            'viewer_sha256':hashlib.sha256((HERE/'viewer.js').read_bytes()).hexdigest(),
            'data_bytes':(OUT/'development.json').stat().st_size}
    (OUT/'audit.json').write_text(json.dumps(report,indent=2))
    (HERE/'evidence').mkdir(exist_ok=True)
    (HERE/'evidence/audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
