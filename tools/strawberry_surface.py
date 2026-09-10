"""Shared strawberry envelope and appearance in fruit-body coordinates, metres.

enrich() only changes appearance. reshape_physical() explicitly changes the
collision envelope and requires recompilation and a fresh physics rollout.
Neither models flesh deformation or calibrated achene contact.
"""
from pathlib import Path
import hashlib,json
import xml.etree.ElementTree as E
import numpy as np
from scipy.interpolate import PchipInterpolator
import trimesh

RECIPE=dict(version=1,radial_segments=192,axial_segments=160,
            pit_depth_m=.00019,pit_width_sigma_m=.00053,pit_length_sigma_m=.00080,
            achene_half_axes_m=[.00023,.00050,.00014],
            description='Shallow elliptical pits and surface-aligned achenes; visual dimensions are hypotheses.')

COMPACT_STATIONS=np.array([0,.08,.20,.33,.52,.72,.87,.96,.99,1.])
COMPACT_RADII=np.array([.48,.82,.99,1.,.88,.63,.39,.17,.07,0.])

def profile(radius,length,kind='legacy'):
    if kind=='measured_loft':
        r=COMPACT_RADII.copy();r[0]=r[-1]=.05
        return PchipInterpolator(COMPACT_STATIONS,radius*r)
    if kind=='compact_conic':return PchipInterpolator(COMPACT_STATIONS,radius*COMPACT_RADII)
    t=np.linspace(0,1,19)
    r=radius*(.12+np.sin(np.pi*(t*.86+.1))**.8)*(1-.72*t)
    return PchipInterpolator(t,r)

def compact_spec(f):
    # Shape/volume assumptions, not recovered cultivar measurements. Holding the
    # existing mass while specifying density avoids an implausibly dense narrow fruit.
    aspect,flatten={'primary':(.98,.92),'secondary_a':(1.02,.96),'secondary_b':(1.06,.94),'green':(.96,.98)}[f['id']]
    rho=1000.;p=PchipInterpolator(COMPACT_STATIONS,COMPACT_RADII);t=np.linspace(0,1,10001)
    integral=np.trapezoid(p(t)**2,t)
    radius=(f['mass']/rho/(np.pi*2*aspect*flatten*integral))**(1/3)
    result=dict(f,radius=float(radius),length=float(2*radius*aspect),surface_profile='compact_conic',
                flatten_y=flatten,density_assumption_kg_m3=rho,length_width_ratio=aspect)
    result.pop('morphology',None)
    return result

def envelope(f,n=96,rows=80):
    t,a=np.meshgrid(np.linspace(0,1,rows+1),np.arange(n)*2*np.pi/n,indexing='ij');r=profile(f['radius'],f['length'],f.get('surface_profile','legacy'))(t)
    vv=np.c_[(r*np.cos(a)).ravel(),(r*np.sin(a)*f.get('flatten_y',1.)).ravel(),(-.002-f['length']*t).ravel()]
    if 'morphology' in f:
        from strawberry_morphology import warp
        vv=warp(vv,f)
    # Convex hull is the actual rigid collision shape used by MuJoCo.
    return trimesh.convex.convex_hull(vv)

def reshape_physical(root,spec,fruit_specs=None):
    import copy
    updated=copy.deepcopy(spec)
    for branch in updated['truss']:
        if 'fruit' not in branch:continue
        old=branch['fruit'];f=fruit_specs[old['id']] if fruit_specs is not None else compact_spec(old);branch['fruit']=f;geo=envelope(f)
        asset=root.find(f"./asset/mesh[@name='berrymesh_{f['id']}']")
        asset.set('vertex',' '.join(f'{x:.10g}' for x in geo.vertices.ravel()));asset.set('face',' '.join(str(int(x)) for x in geo.faces.ravel()))
        body=root.find(f".//body[@name='fruit_{f['id']}']")
        # Explicit mass remains the same. Recompilation recalculates COM/inertia
        # from the new envelope and the existing calyx mass distribution.
        for g in body.findall('geom'):
            if g.get('name','').startswith('calyx_'):
                scale=f['radius']/old['radius']
                size=np.fromstring(g.get('size'),sep=' ');size[0]*=scale;g.set('size',' '.join(map(str,size)))
                pos=np.fromstring(g.get('pos'),sep=' ');pos[:2]*=scale;g.set('pos',' '.join(map(str,pos)))
    return updated

def make_fruit(f):
    radius,length=f['radius'],f['length'];p=profile(radius,length,f.get('surface_profile','legacy'));dp=p.derivative()
    seed=int.from_bytes(hashlib.sha256(f['id'].encode()).digest()[:4],'little')
    rng=np.random.default_rng(seed);sites=[]
    for row,t in enumerate(np.arange(.10,.93,.0036/length)):
        count=max(5,round(2*np.pi*float(p(t))/.0033))
        for j in range(count):
            tt=float(np.clip(t+rng.uniform(-.10,.10)*.0036/length,.06,.96))
            a=2*np.pi*(j+.5*(row%2)+rng.uniform(-.10,.10))/count
            sites.append([tt,a,float(RECIPE['pit_depth_m']*rng.uniform(.78,1.12))])
    nt,na=RECIPE['axial_segments'],RECIPE['radial_segments']
    tt,aa=np.meshgrid(np.linspace(0,1,nt+1),np.arange(na)*2*np.pi/na,indexing='ij')
    tt=tt.ravel();aa=aa.ravel();rr=p(tt)
    vertices=np.c_[rr*np.cos(aa),rr*np.sin(aa),-.002-length*tt]
    normal=np.c_[np.cos(aa),np.sin(aa),dp(tt)/length];normal/=np.linalg.norm(normal,axis=1)[:,None]
    displacement=np.zeros(len(tt))
    for t,a,depth in sites:
        dtheta=np.arctan2(np.sin(aa-a),np.cos(aa-a))*float(p(t))
        ds=(tt-t)*np.sqrt(length**2+float(dp(t))**2)
        exponent=(dtheta/RECIPE['pit_width_sigma_m'])**2+(ds/RECIPE['pit_length_sigma_m'])**2
        displacement+=depth*np.exp(-.5*exponent)
    vertices-=normal*displacement[:,None]
    faces=[]
    for i in range(nt):
        for j in range(na):
            a=i*na+j;b=i*na+(j+1)%na;c=a+na;d=b+na
            faces.extend([[a,c,b],[b,c,d]])
    top=len(vertices);bottom=top+1
    vertices=np.vstack([vertices,[0,0,-.002],[0,0,-.002-length]])
    for j in range(na):
        faces.extend([[top,j,(j+1)%na],[bottom,nt*na+(j+1)%na,nt*na+j]])
    skin=trimesh.Trimesh(vertices,faces,process=False);trimesh.repair.fix_normals(skin)
    grains=[]
    for t,a,depth in sites:
        n=np.array([np.cos(a),np.sin(a),float(dp(t))/length]);n/=np.linalg.norm(n)
        u=np.array([-np.sin(a),np.cos(a),0]);v=np.cross(n,u)
        centre=np.array([p(t)*np.cos(a),p(t)*np.sin(a),-.002-length*t])-n*(depth-.000055)
        geo=trimesh.creation.icosphere(subdivisions=2)
        geo.vertices*=np.array(RECIPE['achene_half_axes_m'])*rng.uniform(.87,1.10)
        geo.vertices=geo.vertices@np.column_stack([u,v,n]).T+centre
        grains.append(geo)
    sepals=[]
    for j in range(10):
        angle=j*2*np.pi/10+rng.uniform(-.06,.06);long=j%2==0
        L=radius*(.96 if long else .70);W=radius*(.23 if long else .17)
        if 'morphology' in f:
            # Separate unmeasured sepal variation; does not perturb the traced fruit.
            L*=rng.uniform(.82,1.10);W*=rng.uniform(.85,1.13)
        verts=[]
        for i in range(17):
            s=i/16;width=W*np.sin(np.pi*s)**.75
            for k in range(5):
                u=(k-2)/2
                x=radius*.13+L*s;y=width*u
                z=-.0005+.0025*s-.0034*s*s+.00075*u*u*np.sin(np.pi*s)
                verts.append([x*np.cos(angle)-y*np.sin(angle),x*np.sin(angle)+y*np.cos(angle),z])
        # Closed leaflike solid: visible creased faces, not elliptical lumps.
        verts=np.array(verts);n=len(verts);verts=np.vstack([verts,verts-[0,0,.00018]])
        ff=[]
        for i in range(16):
            for k in range(4):
                a=i*5+k;b=a+1;c=a+5;d=c+1
                ff.extend([[a,b,c],[b,d,c],[a+n,c+n,b+n],[b+n,c+n,d+n]])
        boundary=list(range(5))+[i*5+4 for i in range(1,17)]+list(range(83,79,-1))+[i*5 for i in range(15,0,-1)]
        for a,b in zip(boundary,boundary[1:]+boundary[:1]):ff.extend([[a,a+n,b],[b,a+n,b+n]])
        geo=trimesh.Trimesh(verts,ff,process=False);trimesh.repair.fix_normals(geo);sepals.append(geo)
    if 'morphology' in f:
        collar=trimesh.creation.cylinder(radius=min(.16*radius,.0025),height=.0035,sections=32)
        collar.apply_translation([0,0,-.001]);sepals.append(collar)
    result=dict(skin=skin,achenes=trimesh.util.concatenate(grains),calyx=trimesh.util.concatenate(sepals))
    for kind,geo in result.items():
        geo.vertices[:,1]*=f.get('flatten_y',1.)
        if 'morphology' in f and kind!='calyx':
            from strawberry_morphology import warp
            geo.vertices=warp(geo.vertices,f)
            trimesh.repair.fix_normals(geo)
    return result,dict(achene_count=len(sites),maximum_skin_indent_mm=float(displacement.max()*1000),recipe=RECIPE,
                       length_mm=length*1000,maximum_width_mm=radius*2*1000,profile=f.get('surface_profile','legacy'))

def enrich(root,spec,out):
    """Add surface geometry to a full original scene; preserve all physical geoms."""
    out=Path(out);out.mkdir(exist_ok=True,parents=True);assets=root.find('asset');reports={}
    for branch in spec['truss']:
        if 'fruit' not in branch:continue
        f=branch['fruit'];fid=f['id'];body=root.find(f".//body[@name='fruit_{fid}']")
        meshes,report=make_fruit(f);reports[fid]=report
        # Hide only the old fruit appearance. Their mass and collision properties
        # remain untouched, including the 0.05 g calyx and mesh-derived inertia.
        for geom in body.findall('geom'):
            if geom.get('name','').startswith(('berry_','seed_','calyx_')):
                rgba=geom.get('rgba','.5 .5 .5 1').split();rgba[3]='0';geom.set('rgba',' '.join(rgba))
        color={'red':'.63 .035 .019 1','green':'.44 .52 .12 1','turning':'.76 .22 .055 1'}[f['maturity']]
        for kind,geo in meshes.items():
            name=f'fruit_detail_{fid}_{kind}';file=(out/(name+'.stl')).resolve();geo.export(file)
            E.SubElement(assets,'mesh',name=name,file=str(file),inertia='shell')
            E.SubElement(body,'geom',name=name,type='mesh',mesh=name,mass='0',contype='0',conaffinity='0',group='0',
                         rgba=color if kind=='skin' else '.58 .38 .105 1' if kind=='achenes' else '.16 .31 .055 1')
    return reports
