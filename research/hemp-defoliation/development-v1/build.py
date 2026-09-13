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
OUT = ROOT / 'runs/hemp-development-v1'
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
    rng = np.random.default_rng(seed)
    vigor = float(rng.uniform(.90,1.10))
    axes, leaves = [], []
    def axis(id_,parent,parent_node,born,count,phi,spread,bend,vigor_local,order):
        lengths = rng.lognormal(0,.10,count)
        # Upper internodes shorten in this morphology hypothesis; retained in the ledger.
        if order > 0: lengths *= 1-.48*np.linspace(0,1,count)**3
        lengths *= (A['main_internode_m'] if order==0 else A['primary_internode_m']*(.62 if order==2 else 1.))*vigor_local
        # Correlated growth rate at specimen / shoot level; small local variation.
        interval = (3.8 if order==0 else (3.6 if order==1 else 4.8))/vigor_local
        birth = [float(born+interval*j) for j in range(count)]
        mature_radius = (.0065 if order==0 else (.0033 if order==1 else .00165))*vigor_local
        item = {'id':id_,'parent':parent,'parent_node':parent_node,'born':float(born),'order':order,
                'births':birth,'lengths':lengths.tolist(),'phi':float(phi),'spread':float(spread),
                'bend':float(bend),'radius':mature_radius,'vigor':vigor_local,
                'wiggle_phase':float(rng.uniform(0,6.28))}
        axes.append(item)
        for j in range(count):
            # Basal opposite pairs, later alternating leaves. An assumed pattern
            # for this architecture, not universal across stages or propagation.
            angles = [phi+j*math.pi/2,phi+j*math.pi/2+math.pi] if order==0 and j<3 else [phi+j*2.399+float(rng.normal(0,.12))]
            for side,angle in enumerate(angles):
                relative = .93-.18*(j/max(count-1,1))**2
                leaflen = A['leaf_length_m']*vigor_local*relative*(.75 if order==2 else 1.)*float(rng.uniform(.89,1.10))
                leaflet_count = 3 if j==0 and order==0 else (5 if j>count-3 else 7)
                leaves.append({'id':f'{id_}/leaf-{j}-{side}','axis':id_,'node':j+1,
                    'born':birth[j]+2,'length':leaflen,'phi':float(angle),
                    'roll':float(rng.uniform(-.30,.30)),'droop':float(rng.uniform(.03,.23)),
                    'leaflets':leaflet_count,'tone':float(rng.uniform(.86,1.13)),
                    'lifetime_steps':float(rng.uniform(83,110))})
        return item
    main = axis('main',None,0,0,A['main_nodes'],.3,0,0,vigor,0)
    for i in range(int(rng.integers(A['primary_shoot_count']-1,A['primary_shoot_count']+2))):
        rank = 1+i//2
        phi = rank*math.pi/2+(i%2)*math.pi+float(rng.uniform(-.20,.20))
        local = vigor*float(rng.uniform(.82,1.16))
        born = main['births'][rank-1]+12+float(rng.uniform(0,4))
        count = int(rng.integers(*[A['primary_nodes_range'][0],A['primary_nodes_range'][1]+1]))
        shoot = axis(f'shoot-{i}', 'main',rank,born,count,phi,float(rng.uniform(.74,1.12)),float(rng.uniform(-.14,.14)),local,1)
        for k in [3,5,7]:
            if rng.random() < .16: continue
            childphi = phi+(-1 if k==3 else 1)*float(rng.uniform(.58,1.22))
            axis(f'shoot-{i}/lateral-{k}',shoot['id'],k,
                 shoot['births'][k-1]+13+float(rng.uniform(0,5)),A['secondary_node_count'],
                 childphi,float(rng.uniform(.45,.85)),float(rng.uniform(-.1,.1)),local*.86,2)
    return {'seed':seed,'vigor':vigor,'axes':axes,'leaves':leaves}


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
            spread = ax['spread']*(1-.66*f)
            ph = ax['phi']+ax['bend']*f+.025*math.sin(j*1.7+ax['wiggle_phase'])
            direction = unit([spread*math.cos(ph),spread*math.sin(ph),1.])
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
                             'flower_scale':float(smooth((t-ax['births'][-1]-18)/30)) if ax['order'] else 0}
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
        leafarea=sum(PROFILE_AREAS[i]*(length*r)**2 for i,r in zip(inds,rel))
        active=s>.001 and not removed
        if active:
            area+=leafarea;mass_leaf+=leafarea*A['leaf_area_mass_kg_m2'];live+=1
        at=axis_state[leaf['axis']]['points'][leaf['node']]
        leaf_state.append({'id':leaf['id'],'at':at,'scale':s,'age':age,'senescence':senescence,
                           'removed':removed,'active':active,'area_m2':float(leafarea),
                           'mass_kg':float(leafarea*A['leaf_area_mass_kg_m2'])})
    p=np.concatenate([v['points'] for v in axis_state.values()])
    return {'step':t,'axes':list(axis_state.values()),'leaves':leaf_state,
            'metrics':{'active_leaves':live,'leaf_area_m2':float(area),'leaf_mass_kg':float(mass_leaf),
                       'stem_mass_kg':float(sum(a['mass_kg'] for a in axis_state.values())),
                       'axis_height_m':float(p[:,2].max()),'axis_width_m':float(np.ptp(p[:,0]))}}


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
    return {'seed':spec['seed'],'axes':len(spec['axes']),'leaf_organs':len(spec['leaves']),
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
            'data_bytes':(OUT/'development.json').stat().st_size}
    (OUT/'audit.json').write_text(json.dumps(report,indent=2))
    (HERE/'evidence').mkdir(exist_ok=True)
    (HERE/'evidence/audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
