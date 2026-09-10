"""Opt-in anatomy surface, in metres, on the unchanged morphology envelope.

Topological observations come from botanical references. Dimensions, spacing and
curvatures below are adjustable hypotheses, not an identified growth model.
These meshes are visual only; the shared rigid collision envelope is unchanged.
"""
import hashlib
import numpy as np
import trimesh
from scipy.spatial import cKDTree

RECIPE = dict(version=4, minimum_site_spacing_m=.0027,
    achene_full_axes_m=[.00072,.0013,.00036], pit_depth_m=.00016,
    pit_width_sigma_m=.00056,pit_length_sigma_m=.00083,
    sepals=5,epicalyx_bractlets=5,
    scope='Surface-area-weighted exclusion sampler; dimensions and curvature are priors, not measured cultivar distributions. Calyx is visual, not flexible contact geometry.')

def point(f,t,a):
    from strawberry_surface import profile
    t,a=np.broadcast_arrays(t,a);r=profile(f['radius'],f['length'],f.get('surface_profile','legacy'))(t)
    v=np.c_[r.ravel()*np.cos(a.ravel()),r.ravel()*np.sin(a.ravel())*f.get('flatten_y',1),-.002-f['length']*t.ravel()]
    if 'morphology' in f:
        from strawberry_morphology import warp
        v=warp(v,f)
    return v

def frame(f,t,a):
    t,a=np.broadcast_arrays(t,a);eps=1e-5
    u=point(f,t,a+eps)-point(f,t,a-eps)
    v=point(f,np.minimum(t+eps,1),a)-point(f,np.maximum(t-eps,0),a)
    n=np.cross(v,u);n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-20)
    u/=np.maximum(np.linalg.norm(u,axis=1)[:,None],1e-20)
    v=np.cross(n,u)
    return u,v,n

def sites(f,rng):
    # Candidate probability follows final surface area. Exclusion is in 3D on
    # the convex-ish receptacle, an approximation to geodesic spacing.
    t,a=np.meshgrid(np.linspace(.065,.965,100),np.linspace(0,2*np.pi,192,endpoint=False),indexing='ij')
    t=t.ravel();a=a.ravel();e=1e-4
    dt=(point(f,t+e,a)-point(f,t-e,a))/(2*e)
    da=(point(f,t,a+e)-point(f,t,a-e))/(2*e)
    area=np.linalg.norm(np.cross(dt,da),axis=1)
    chosen=rng.choice(len(t),12000,p=area/area.sum())
    tc=np.clip(t[chosen]+rng.uniform(-.0045,.0045,len(chosen)),.06,.97)
    ac=a[chosen]+rng.uniform(-np.pi/192,np.pi/192,len(chosen))
    xyz=point(f,tc,ac);accepted=[];params=[];spacing=[]
    for tt,aa,p in zip(tc,ac,xyz):
        # Smooth local density modulation, not independent vertex noise.
        d=RECIPE['minimum_site_spacing_m']*(1+.12*np.cos(aa+3*tt)+.06*np.sin(2*aa-tt))
        if accepted:
            distance=np.linalg.norm(np.asarray(accepted)-p,axis=1)
            if np.any(distance < .5*(np.asarray(spacing)+d)):continue
        accepted.append(p);params.append((tt,aa));spacing.append(d)
    return np.asarray(params),np.asarray(accepted)

def leaf(L,W,angle,lift,curl,twist,root,rng):
    ns,nw=33,9;verts=[];colors=[];phase=rng.uniform(0,2*np.pi)
    for s in np.linspace(0,1,ns):
        width=W*(.018+np.sin(np.pi*s)**.82)*(1-.36*s)
        for u in np.linspace(-1,1,nw):
            x=root+L*s;y=width*u+.045*L*np.sin(np.pi*s)*np.sin(phase)
            # Broad midrib crease, gently rolled margins, independent tip curl.
            z=-.0011+lift*s+curl*s*s+.20*W*(abs(u)**1.4)*np.sin(np.pi*s)+twist*u*s
            verts.append([x*np.cos(angle)-y*np.sin(angle),x*np.sin(angle)+y*np.cos(angle),z])
            vein=np.exp(-(u/.085)**2)*.13
            shade=1+vein-.10*abs(u)+.035*np.sin(5*np.pi*s+abs(u)*4)
            colors.append(np.r_[np.array([63,94,30])*shade,255])
    verts=np.asarray(verts);n=len(verts);verts=np.vstack([verts,verts-[0,0,.00015]])
    colors=np.vstack([colors,np.asarray(colors)*[.83,.88,.83,1]])
    faces=[]
    for i in range(ns-1):
        for k in range(nw-1):
            a=i*nw+k;b=a+1;c=a+nw;d=c+1
            faces.extend([[a,b,c],[b,d,c],[a+n,c+n,b+n],[b+n,c+n,d+n]])
    boundary=list(range(nw))+[i*nw+nw-1 for i in range(1,ns)]+list(range(ns*nw-2,(ns-1)*nw-1,-1))+[i*nw for i in range(ns-2,0,-1)]
    for a,b in zip(boundary,boundary[1:]+boundary[:1]):faces.extend([[a,a+n,b],[b,a+n,b+n]])
    g=trimesh.Trimesh(verts,faces,process=False);trimesh.repair.fix_normals(g)
    g.visual.vertex_colors=np.asarray(colors,dtype=np.uint8)
    return g

def calyx(f,rng):
    r=f['radius'];params=f.get('calyx_parameters',{});scale=params.get('span_scale',1.)
    count=params.get('sepals',5);phase=rng.uniform(0,2*np.pi);parts=[];records=[]
    # Two distinct alternating whorls. Counts are configurable because cultivar
    # studies report more than five in some cultivated flowers.
    for whorl in range(2):
        for j in range(count):
            angle=phase+2*np.pi*(j+.5*whorl)/count+rng.uniform(-.10,.10)
            L=r*scale*rng.uniform(.68,.98)*(1 if whorl==0 else .81)
            W=L*rng.uniform(.28,.37)*(1 if whorl==0 else .68)
            lift=L*rng.uniform(.12,.36)
            curl=L*rng.uniform(-.48,-.06)+params.get('tip_curl_m',0)
            twist=W*rng.uniform(-.15,.15)
            parts.append(leaf(L,W,angle,lift,curl,twist,r*.065,rng))
            records.append(dict(whorl='sepal' if whorl==0 else 'epicalyx',length_mm=L*1000,half_width_mm=W*1000,lift_mm=lift*1000,curl_mm=curl*1000))
    # Fused-looking basal tissue, meeting the unchanged pedicel at local origin.
    collar=trimesh.creation.icosphere(subdivisions=3);collar.vertices*= [min(r*.21,.0033)]*2+[.0018];collar.apply_translation([0,0,-.00165]);collar.visual.vertex_colors=[72,105,34,255];parts.append(collar)
    stalk=trimesh.creation.cylinder(radius=.0008,height=.002,sections=24);stalk.apply_translation([0,0,.0001]);stalk.visual.vertex_colors=[71,105,33,255];parts.append(stalk)
    return trimesh.util.concatenate(parts),records

def make_fruit(f):
    seed=int.from_bytes(hashlib.sha256((f['id']+'-anatomy4').encode()).digest()[:4],'little');rng=np.random.default_rng(seed)
    loc,centres=sites(f,rng);su,sv,sn=frame(f,loc[:,0],loc[:,1]);nt,na=160,192
    tt,aa=np.meshgrid(np.linspace(0,1,nt+1),np.arange(na)*2*np.pi/na,indexing='ij');tt=tt.ravel();aa=aa.ravel()
    vertices=point(f,tt,aa);_,_,normal=frame(f,tt,aa);displacement=np.zeros(len(vertices));grains=[];records=[]
    for j,(t,a) in enumerate(loc):
        angle=.15*np.sin(a*2+t*4)+rng.uniform(-.22,.22)
        u=su[j]*np.cos(angle)+sv[j]*np.sin(angle);v=sv[j]*np.cos(angle)-su[j]*np.sin(angle);n=sn[j]
        depth=RECIPE['pit_depth_m']*rng.uniform(.70,1.16);size=rng.uniform(.82,1.14)
        delta=vertices-centres[j];x=delta@u;y=delta@v;z=delta@n
        exponent=(x/(RECIPE['pit_width_sigma_m']*size))**2+(y/(RECIPE['pit_length_sigma_m']*size))**2
        displacement+=depth*np.exp(-.5*exponent)*(abs(z)<.0015)
        grain=trimesh.creation.icosphere(subdivisions=2)
        axes=np.asarray(RECIPE['achene_full_axes_m'])*size/2
        # Slightly tapered ovoid, not a stretched bead from the fruit warp.
        grain.vertices[:,0]*=1-.16*grain.vertices[:,1];grain.vertices*=axes
        grain.vertices=grain.vertices@np.column_stack([u,v,n]).T+centres[j]-n*(depth-.000045)
        gold=np.array([160,125,55])*rng.uniform(.82,1.10);grain.visual.vertex_colors=np.r_[gold,255].astype(np.uint8);grains.append(grain)
        records.append(dict(t=float(t),angle=float(a),centre_m=centres[j].tolist(),axes_mm=(axes*2000).tolist(),pit_depth_mm=depth*1000))
    vertices-=normal*displacement[:,None];faces=[]
    for i in range(nt):
        for j in range(na):
            a=i*na+j;b=i*na+(j+1)%na;c=a+na;d=b+na;faces.extend([[a,c,b],[b,c,d]])
    top=len(vertices);bottom=top+1
    # Match the old cap closure exactly in the macroscopic envelope.
    from strawberry_morphology import warp
    caps=np.array([[0,0,-.002],[0,0,-.002-f['length']]])
    if 'morphology' in f:caps=warp(caps,f)
    vertices=np.vstack([vertices,caps])
    for j in range(na):faces.extend([[top,j,(j+1)%na],[bottom,nt*na+(j+1)%na,nt*na+j]])
    skin=trimesh.Trimesh(vertices,faces,process=False);trimesh.repair.fix_normals(skin)
    # Low-frequency surface colour only. No geometry noise or invented ripeness
    # measurement; these colours are display priors shared by exported GLBs.
    t=np.r_[tt,[0,1]];a=np.r_[aa,[0,0]];variation=1+.05*np.sin(3*a+7*t)+.03*np.cos(7*a-10*t)
    base=np.array({'red':[166,17,10],'turning':[181,72,30],'green':[130,151,61]}[f['maturity']])
    colors=base[None,:]*variation[:,None];skin.visual.vertex_colors=np.c_[np.clip(colors,0,255),np.full(len(t),255)].astype(np.uint8)
    cap,leaf_records=calyx(f,rng);nearest=cKDTree(centres).query(centres,k=2)[0][:,1]*1000
    return dict(skin=skin,achenes=trimesh.util.concatenate(grains),calyx=cap),dict(recipe=RECIPE,achene_count=len(loc),
        nearest_site_distance_mm=dict(min=float(nearest.min()),median=float(np.median(nearest)),max=float(nearest.max())),
        maximum_skin_indent_mm=float(displacement.max()*1000),sites=records,calyx=leaf_records,
        scope='Appearance only. Macro collision envelope, mass, COM, inertia, plant dynamics unchanged. Achene dimensions are not deformed with the fruit. No calibrated bruising or flexible calyx contact.')
