"""Whole hemp plant anatomy mesh and attachment graph. Static, uncalibrated.

Uses published leaflet edge measurements, with inferred hidden basal outlines.
No common membrane connects overlapping leaflets. Dimensions/3D poses assumed.
"""
from pathlib import Path
import json, hashlib, shutil
from collections import Counter
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / 'runs/hemp-whole-plant-v1'
C = json.loads((HERE / 'specimen.json').read_text())
R = np.random.default_rng(C['seed'])
Z = np.array([0., 0., 1.])
GROUPS = {}
ORGANS = []
COLORS = {'stem':[.34,.40,.15], 'branch':[.38,.47,.19],
          'petiole':[.41,.43,.20], 'leaf':[.21,.40,.12],
          'small_leaf':[.31,.46,.17], 'vein':[.41,.53,.22],
          'stipule':[.37,.52,.18], 'flower_axis':[.38,.48,.20],
          'bract':[.40,.51,.22], 'stigma':[.79,.73,.53],
          'root':[.62,.51,.34], 'pot':[.23,.28,.27], 'substrate':[.18,.13,.09]}


def unit(v):
    v = np.array(v, dtype=float)
    return v / max(np.linalg.norm(v), 1e-12)


def frame(direction):
    a = unit(direction)
    b = unit(np.cross(a, Z if abs(a[2]) < .94 else [0,1,0]))
    return a, b, unit(np.cross(a,b))


def organ(kind, parent, at, **kw):
    id_ = f'{kind}-{len(ORGANS):04d}'
    ORGANS.append({'id':id_, 'kind':kind, 'parent':parent,
                   'attachment':np.array(at).round(7).tolist(), **kw})
    return id_


def mesh(kind, id_, verts, faces, tone=1.):
    verts = np.asarray(verts); faces = np.asarray(faces, dtype=int)
    if len(faces) == 0: return
    g = GROUPS.setdefault(kind, {'vertices':[], 'faces':[], 'colors':[], 'organs':[]})
    start, offset = len(g['faces']), len(g['vertices'])
    g['vertices'].extend(verts.round(7).tolist())
    g['faces'].extend((faces + offset).tolist())
    col = np.clip(np.array(COLORS[kind])*tone, 0, 1).tolist()
    g['colors'].extend([col] * len(verts))
    g['organs'].append({'first_face':start,'end_face':len(g['faces']),'id':id_})


def tube(points, radii, kind, id_, sides=8):
    pts = np.asarray(points); rr = np.broadcast_to(radii, (len(pts),))
    v=[]; f=[]
    for i,p in enumerate(pts):
        tangent = pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]
        _, b, n = frame(tangent)
        for angle in np.linspace(0, 2*np.pi, sides, endpoint=False):
            v.append(p + rr[i]*(b*np.cos(angle)+n*np.sin(angle)))
    for i in range(len(pts)-1):
        for j in range(sides):
            a=i*sides+j; b=i*sides+(j+1)%sides
            f.extend([[a,b,b+sides],[a,b+sides,a+sides]])
    for j in range(1,sides-1):
        f.extend([[0,j+1,j],[(len(pts)-1)*sides,(len(pts)-1)*sides+j,(len(pts)-1)*sides+j+1]])
    mesh(kind,id_,v,f)


def path_at(points,t):
    x=t*(len(points)-1); lo=min(int(x),len(points)-2)
    return points[lo]*(1-(x-lo))+points[lo+1]*(x-lo)


def load_leaflet_profiles():
    base=HERE.parent/'reference-data'
    raw=np.loadtxt(base/'out_FUT75_2_12_4a_7.txt')
    lm=np.loadtxt(base/'land_FUT75_2_12_4a_7.txt')
    indices=[int(np.argmin(np.linalg.norm(raw-p,axis=1))) for p in lm]
    profiles=[]
    for i in range(7):
        a,b,tip=indices[2*i],indices[2*i+1],indices[14+i]
        ids=np.arange(a,b+1 if b>=a else b+len(raw)+1)%len(raw)
        assert tip in ids
        k=int(np.where(ids==tip)[0][0]); contour=raw[ids]
        direction=unit(lm[14+i]-lm[-1]); normal=np.array([-direction[1],direction[0]])
        scale=np.linalg.norm(lm[14+i]-lm[-1])
        xy=np.column_stack([(contour-lm[-1])@direction,(contour-lm[-1])@normal])/scale
        left=[]
        for edge in [xy[:k+1],xy[k:]]:
            edge=np.vstack([[0,0],edge,[1,0]])
            edge=edge[np.argsort(edge[:,0])]
            t=np.linspace(0,1,81)
            left.append(np.interp(t,edge[:,0],edge[:,1]))
        low=np.minimum(*left);high=np.maximum(*left)
        profiles.append((low,high))
    return profiles


PROFILES = load_leaflet_profiles()


def blade(origin, direction, length, kind, parent, profile=3, width_scale=1., curl=0., twist=0., name='leaflet'):
    id_=organ(name,parent,origin,length_m=float(length),shape_source='Futura75 visible leaflet edges; hidden base inferred' if kind=='leaf' else 'parametric reduced blade',pose_status='assumed')
    a,b,n=frame(direction)
    # Keep adaxial normal generally upward, while permitting leaf-specific roll.
    if n[2]<0: b=-b;n=-n
    b2=b*np.cos(twist)+n*np.sin(twist);n2=n*np.cos(twist)-b*np.sin(twist);b,n=b2,n2
    low,high=PROFILES[profile]
    if kind in ['stipule','small_leaf']:
        ts=np.linspace(0,1,81)
        width=.11*np.sin(np.pi*ts)**.8*(1-.28*ts)
        teeth=1-.12*(.5+.5*np.cos(ts*2*np.pi*19))
        low=-width*teeth;high=width*teeth
    ns, nc = (48,5) if kind=='leaf' else ((24,5) if kind=='small_leaf' else (8,3))
    verts=[origin];faces=[]
    def center(t):
        return origin+a*(length*t)+n*(curl*length*t*t)
    for i in range(1,ns):
        t=i/ns
        for j,v in enumerate(np.linspace(-1,1,nc)):
            ix=round(t*80)
            side=(low[ix]*(1-v)/2+high[ix]*(1+v)/2)*length*width_scale
            fold=.18*abs(side)*(1-.3*t)
            ripple=length*.003*np.sin(5*np.pi*t+v)*abs(v)
            verts.append(center(t)+b*side+n*(fold+ripple))
    tip_index=len(verts);verts.append(center(1))
    for j in range(nc-1): faces.append([0,1+j,2+j])
    for i in range(ns-2):
        for j in range(nc-1):
            x=1+i*nc+j;faces.extend([[x,x+nc,x+nc+1],[x,x+nc+1,x+1]])
    start=1+(ns-2)*nc
    for j in range(nc-1): faces.append([start+j,tip_index,start+j+1])
    mesh(kind,id_,verts,faces,tone=R.uniform(.88,1.15))
    if kind in ['leaf','small_leaf']:
        ps=[center(t)+n*.00012 for t in np.linspace(0,1,17)]
        tube(ps,np.linspace(length*.007,length*.0008,17),'vein',id_,5)
        if kind=='leaf':
            for t in np.linspace(.18,.86,7):
                ix=int(t*80)
                for side in [low[ix],high[ix]]:
                    p=center(t)+n*.00013
                    end=center(min(1,t+.095))+b*side*length*width_scale*.87+n*abs(side)*length*.18
                    tube([p,(p+end)/2+n*length*.002,end],[length*.0018,length*.0012,length*.0003],'vein',id_,4)
    return id_


def fan(at, angle, size, parent, count=7, elevation=.05, role='fan_leaf'):
    radial=np.array([np.cos(angle),np.sin(angle),0.])
    plen=float(R.uniform(.034,.065)*size/.135)
    tip=at+radial*plen+Z*(plen*.12)
    id_=organ('petiole',parent,at,end=tip.tolist(),leaflet_count=count)
    path=[at,at+radial*plen*.45+Z*(plen*.2),tip]
    tube(path,[plen*.025,plen*.021,plen*.012],'petiole',id_,7)
    indices={7:[0,1,2,3,4,5,6],5:[1,2,3,4,5],3:[2,3,4],1:[3]}[count]
    angles={7:np.array([-88,-58,-29,0,28,60,91]),5:np.array([-62,-30,0,32,64]),3:np.array([-37,0,38]),1:np.array([0])}[count]
    lengths={7:[.36,.64,.87,1.,.86,.62,.34],5:[.60,.87,1.,.85,.60],3:[.72,1.,.71],1:[1.]}[count]
    for i,ang,rel in zip(indices,angles,lengths):
        phi=angle+np.radians(ang)+R.normal(0,.015)
        direction=unit([np.cos(phi),np.sin(phi),elevation+R.normal(0,.06)])
        blade(tip,direction,size*rel*R.uniform(.93,1.06),'leaf' if role=='fan_leaf' else 'small_leaf',id_,i,
              width_scale=R.uniform(.91,1.12),curl=R.uniform(-.15,-.025),twist=R.uniform(-.13,.13))
    return id_


def flower_bract(at,direction,length,parent):
    id_=organ('floral_unit',parent,at,representation='simplified enclosing bract and paired stigmas; no internal carpel or trichome microstructure')
    a,b,n=frame(direction);v=[];f=[];sides=7;rings=7
    for t in np.linspace(0,1,rings):
        rad=length*(.025+.28*np.sin(np.pi*t)**.85)*(1-.3*t)
        for ph in np.linspace(0,2*np.pi,sides,endpoint=False):
            v.append(at+a*t*length+(b*np.cos(ph)+n*np.sin(ph))*rad)
    for i in range(rings-1):
        for j in range(sides):
            x=i*sides+j;y=i*sides+(j+1)%sides
            f.extend([[x,y,y+sides],[x,y+sides,x+sides]])
    mesh('bract',id_,v,f,R.uniform(.87,1.15))
    for s in [-1,1]:
        p=at+a*length*.9+b*s*length*.035
        end=p+a*length*.6+b*s*length*.28+n*length*.1
        tube([p,p+a*length*.37+b*s*length*.13,end],[.00012,.00009,.000035],'stigma',id_,4)


def inflorescence(at, direction, length, parent):
    id_=organ('inflorescence_axis',parent,at,length_m=float(length),representation='condensed branchlets with reduced leaves and bract-enclosed floral units')
    a,b,n=frame(direction)
    spine=np.array([at+a*length*t+b*length*.045*np.sin(np.pi*t) for t in np.linspace(0,1,9)])
    tube(spine,np.linspace(.0018,.00055,len(spine)),'flower_axis',id_,7)
    for j,t in enumerate(np.linspace(.045,.975,17)):
        ph=j*2.399+R.uniform(-.17,.17)
        outward=b*np.cos(ph)+n*np.sin(ph)
        p=path_at(spine,t)
        extent=length*.10*np.sin(np.pi*t)**.55*R.uniform(.85,1.15)
        end=p+outward*extent+a*extent*.32
        sub=organ('floral_branchlet',id_,p,end=end.tolist())
        tube([p,end],[.00065,.00025],'flower_axis',sub,6)
        _, fb, fn=frame(end-p)
        for k in range(4):
            fpos=p+(end-p)*(.18+.21*k)
            # Paired compact neighboring floral units around the short axis.
            # This is an external envelope approximation, not meristem dynamics.
            for side_index in range(2):
                phi=side_index*np.pi+k*1.1
                side=unit(fb*np.cos(phi)+fn*np.sin(phi)+unit(end-p)*.6)
                flower_bract(fpos,side,R.uniform(.0055,.0085),sub)
        if j%4==0:
            blade(p,unit(outward+a*.1),length*R.uniform(.32,.59)*(1-.50*t),'small_leaf',id_,width_scale=.8,curl=-.08)
    flower_bract(spine[-1],a,.006,id_)
    return id_


def make_branch(at, angle, length, radius, parent, order=1):
    radial=np.array([np.cos(angle),np.sin(angle),0.]);tang=np.array([-np.sin(angle),np.cos(angle),0.])
    ts=np.linspace(0,1,17)
    pts=np.array([at+radial*length*(.80*t-.15*t*t)+Z*length*(.36*t+.42*t*t)+tang*.035*length*np.sin(np.pi*t) for t in ts])
    id_=organ('branch',parent,at,order=order,centerline=pts.round(7).tolist(),basal_radius_m=float(radius))
    tube(pts,np.linspace(radius,.001 if order==1 else .00065,17),'branch',id_,9)
    count=5 if order==1 else 3
    for j,t in enumerate(np.linspace(.20,.80,count)):
        p=path_at(pts,t);node=organ('node',id_,p,order=order)
        phi=angle+(-1 if j%2 else 1)*R.uniform(.65,1.35)
        size=C['fan_leaf_central_length_m']*(.95 if order==1 else .58)*(1-.25*t)*R.uniform(.85,1.10)
        fan(p,phi,size,node,7 if j<2 and order==1 else (5 if order==1 else 3),elevation=R.uniform(-.1,.25))
        # Branches originate above the leaf stalk in its axil.
        if order==1 and j in [1,3] and length>.23:
            make_branch(p,phi,length*(.30-.08*t),radius*.40,node,2)
        for s in [-1,1]:
            blade(p,unit(radial*.35+Z+s*tang*.22),.009,'stipule',node,name='stipule')
    inflorescence(pts[-1],unit(pts[-1]-pts[-3]),R.uniform(.065,.10) if order==1 else R.uniform(.035,.055),id_)
    return id_


def build():
    base=organ('root_collar',None,[0,0,0],representation='unmeasured stem-to-root transition')
    tube([[0,0,-.05],[0,0,0]],[.005,C['main_basal_radius_m']],'stem',base,12)
    # Adventitious roots, not an invented taproot for an unspecified clone.
    for i in range(13):
        ph=i*2.399;radial=np.array([np.cos(ph),np.sin(ph),0.])
        start=Z*R.uniform(-.045,-.01)
        dist=R.uniform(.07,.105);depth=R.uniform(.12,.19)
        pts=np.array([start+radial*dist*np.sin(t*np.pi*.48)-Z*depth*t for t in np.linspace(0,1,14)])
        id_=organ('root',base,start,root_hypothesis=C['root_hypothesis'],centerline=pts.round(7).tolist())
        tube(pts,np.linspace(.0028,.0003,len(pts)),'root',id_,7)
        for t in [.3,.5,.7,.9]:
            p=path_at(pts,t);ang=ph+R.uniform(-1.3,1.3)
            end=p+np.array([np.cos(ang)*.025,np.sin(ang)*.025,-.026])
            child=organ('lateral_root',id_,p)
            tube([p,(p+end)/2+Z*.006,end],[.0007,.0004,.00006],'root',child,5)
    n=C['main_nodes'];heights=np.linspace(.07,C['above_substrate_height_m'],n+1)
    heights[1:-1]+=R.uniform(-.012,.012,n-1)
    pts=np.array([[.012*np.sin(z*3),.010*np.sin(z*5),z] for z in np.r_[0,heights]])
    stem=organ('main_stem',base,[0,0,0],centerline=pts.round(7).tolist(),basal_radius_m=C['main_basal_radius_m'])
    tube(pts,np.linspace(C['main_basal_radius_m'],.0015,len(pts)),'stem',stem,12)
    for i,p in enumerate(pts[2:-1]):
        z=p[2]; node=organ('node',stem,p,rank=i+1,phyllotaxis='opposite pair' if i<C['basal_paired_nodes'] else 'alternate')
        angle=i*np.pi/2 if i<C['basal_paired_nodes'] else (i-C['basal_paired_nodes'])*2.399+.4
        for ph in ([angle,angle+np.pi] if i<C['basal_paired_nodes'] else [angle]):
            fan(p,ph,C['fan_leaf_central_length_m']*(1-.45*(z/C['above_substrate_height_m'])**1.7)*R.uniform(.90,1.08),node,
                count=7 if z<.72 else (5 if z<.9 else 3),elevation=.08)
            for s in [-1,1]:
                blade(p,unit([np.cos(ph+s*.3)*.4,np.sin(ph+s*.3)*.4,1]),.014,'stipule',node,name='stipule')
                if z>.40:
                    radial=np.array([np.cos(ph),np.sin(ph),0.])
                    tang=np.array([-np.sin(ph),np.cos(ph),0.])
                    basal_radius=C['main_basal_radius_m']*(1-z/C['above_substrate_height_m'])+.0015
                    flower_bract(p+radial*basal_radius+tang*s*.002,
                                 unit(radial*.7+tang*s*.35+Z),.006,node)
            if i<10:
                length=C['branch_max_length_m']*(.83+.28*np.sin(np.pi*z))*(1-z*.65)*R.uniform(.88,1.10)
                make_branch(p,ph,length,C['main_basal_radius_m']*.47*(1-z*.45),node)
    inflorescence(pts[-1],Z,.12,stem)
    # Pot is a contextual mesh with real opening; roots are independently visible.
    potid=organ('container',None,[0,0,-C['pot_depth_m']],representation='assumed nursery pot; no manufacturer dimensions')
    r=C['pot_radius_m'];d=C['pot_depth_m'];v=[];f=[];nr=72
    rings=[(r*.76,-d),(r,-.014),(r+.003,-.008),(r+.003,.004),(r-.003,.004),(r-.003,-.008),(r*.76-.003,-d+.006)]
    for rr,zz in rings:
        v.extend([[rr*np.cos(ph),rr*np.sin(ph),zz] for ph in np.linspace(0,2*np.pi,nr,endpoint=False)])
    for i in range(len(rings)-1):
        for j in range(nr):
            a=i*nr+j;b=i*nr+(j+1)%nr;f.extend([[a,b,b+nr],[a,b+nr,a+nr]])
    mesh('pot',potid,v,f)
    soilid=organ('substrate',None,[0,0,-.016],representation='support context only')
    v=[[0,0,-.016]]+[[r*.96*np.cos(ph),r*.96*np.sin(ph),-.016] for ph in np.linspace(0,2*np.pi,nr,endpoint=False)]
    f=[[0,j+1,(j+1)%nr+1] for j in range(nr)]
    mesh('substrate',soilid,v,f)


def save():
    OUT.mkdir(parents=True,exist_ok=True)
    ids={o['id'] for o in ORGANS}
    assert len(ids)==len(ORGANS)
    lookup={o['id']:o for o in ORGANS}
    for o in ORGANS:
        if o['parent'] is not None: assert o['parent'] in ids
        seen=set();p=o
        while p['parent']:
            assert p['id'] not in seen;seen.add(p['id']);p=lookup[p['parent']]
    scene=trimesh.Scene();bounds=[];triangles=0
    for kind,g in GROUPS.items():
        v=np.array(g['vertices']);f=np.array(g['faces']);assert np.isfinite(v).all()
        assert f.min()>=0 and f.max()<len(v)
        area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)/2
        assert (area>0).all(), f'{kind}: degenerate triangles'
        triangles+=len(f)
        model=trimesh.Trimesh(vertices=v,faces=f,vertex_colors=np.round(np.array(g['colors'])*255).astype(np.uint8),process=False)
        scene.add_geometry(model,geom_name=kind,node_name=kind)
        bounds.append([v.min(0),v.max(0)])
    (OUT/'plant.glb').write_bytes(scene.export(file_type='glb'))
    (OUT/'plant.json').write_text(json.dumps({'config':C,'groups':GROUPS,'organs':ORGANS},separators=(',',':')))
    (OUT/'review-data.json').write_text(json.dumps({'config':C,'organs':ORGANS,
        'groups':{kind:{'organs':g['organs'],'triangles':len(g['faces'])} for kind,g in GROUPS.items()}},separators=(',',':')))
    (OUT/'anatomy-graph.json').write_text(json.dumps({'specimen':C,'organs':ORGANS},indent=2))
    counts=dict(Counter(o['kind'] for o in ORGANS))
    report={'status':'static anatomy candidate','organ_counts':counts,'triangles':triangles,
            'graph_is_acyclic':True,'all_parent_ids_resolve':True,'finite_nondegenerate_meshes':True,
            'bounds_m':[np.min(np.array(bounds)[:,0],axis=0).tolist(),np.max(np.array(bounds)[:,1],axis=0).tolist()],
            'independent_leaflet_surfaces':True,'physical_contact_validated':False,
            'partner_specimen_matched':False,'material_properties_measured':False,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'config_sha256':hashlib.sha256((HERE/'specimen.json').read_bytes()).hexdigest()}
    (OUT/'report.json').write_text(json.dumps(report,indent=2))
    shutil.copy2(HERE/'review.html',OUT/'index.html')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    build();save()
