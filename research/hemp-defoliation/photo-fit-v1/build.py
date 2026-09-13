"""Fit a connected projected plant to a sparse photo; do not infer physiology.

Run using City-Farmers-Sim/.venv/bin/python. Source meshes and fitting records
are generated in runs; compact diagnostics are copied to this experiment.
"""
from pathlib import Path
import json, hashlib, shutil, math
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_closing, distance_transform_edt

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=ROOT/'runs/hemp-photo-fit-v1'
OBS=json.loads((HERE/'observations.json').read_text())
PROFILES=json.loads((HERE.parent/'development-v3/reference-data.json').read_text())['profiles']
COHORT=json.loads((HERE.parent/'nominal-cultivars-v1/nominal-models.json').read_text())
CW=next(c for c in COHORT['cultivars'] if c['slug']=='cherry-wine')
SUMMARY=CW['nominal_condition']['summary']
HEIGHT=SUMMARY['height_series'][-1]['height_cm']['median']/100
RADIUS=SUMMARY['metrics']['stem_diameter_max_mm']['distribution']['median']/2000
PX=HEIGHT/(OBS['root_pixel'][1]-OBS['apex_pixel'][1])
W,H=OBS['image_size']; ROOTPX=np.array(OBS['root_pixel'],float)
REFERENCE=Image.open(HERE/OBS['image']).convert('RGB')

def unit(a):
    a=np.array(a,float); return a/max(np.linalg.norm(a),1e-12)

def world(xy,y=0):
    return np.array([(xy[0]-ROOTPX[0])*PX,y,(ROOTPX[1]-xy[1])*PX])

def project(xyz):
    xyz=np.array(xyz);return np.column_stack([xyz[:,0]/PX+ROOTPX[0],ROOTPX[1]-xyz[:,2]/PX])

def curve(points,steps=4):
    # C1 Catmull-Rom interpolation passes through all annotated attachment nodes.
    p=np.array(points);out=[]
    for i in range(len(p)-1):
        a,b,c,d=p[max(0,i-1)],p[i],p[i+1],p[min(len(p)-1,i+2)]
        for t in np.linspace(0,1,steps,endpoint=False):
            out.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t**3))
    return np.array(out+[p[-1]])

def topology(depth=0,seed=71):
    rng=np.random.default_rng(seed);axes=[];lookup={}
    # Alternate depth hypotheses preserve the same projected node graph.
    for i,a in enumerate(OBS['axes']):
        p=np.array([world(x) for x in a['xy']]);n=len(p)
        if a['parent']:
            parent=lookup[a['parent']]
            root=parent['nodes'][a['node']]
            amp=(.055+.085*rng.random())*(1 if i%2 else -1)
            if depth==1:amp=-amp
            if depth==2:amp*=.45 if i%3 else 1.6
            p[:,1]=root[1]+amp*np.sin(np.linspace(0,math.pi/2,n))
            p[0]=root
        r=RADIUS if not a['parent'] else RADIUS*(.34-.011*a['node'])
        ax={**a,'nodes':p,'points':curve(p),'r0':r,'r1':r*.32}
        axes.append(ax);lookup[a['id']]=ax
    # Smaller axillary shoots are an explicit latent topology hypothesis.
    # This adds connected fine foliage rather than inflating individual blades.
    for i,parent in enumerate(list(axes)):
        if parent['parent'] is None:continue
        choices=[len(parent['nodes'])-1]
        if len(parent['nodes'])>=4:choices.insert(0,2)
        for k,node in enumerate(choices):
            origin=parent['nodes'][node]
            previous=parent['nodes'][max(0,node-1)]
            d=unit(origin-previous);side=unit(np.cross([0,1,0],d))
            length=(.035+.036*rng.random())*(1.12-.35*origin[2]/HEIGHT)
            direction=unit(d*.5+np.array([0,0,.6])+side*((-1)**(i+k))*.6)
            points=np.array([origin+length*(direction*t+np.array([0,0,.25])*t*t) for t in np.linspace(0,1,4)])
            item={'id':f"{parent['id']}/secondary-{k}",'parent':parent['id'],'node':node,
                  'confidence':'latent small shoot, not individually traced','nodes':points,
                  'points':curve(points),'r0':parent['r0']*.35,'r1':parent['r0']*.12}
            axes.append(item);lookup[item['id']]=item
    return axes,lookup

def leaves(axes,lookup,seed=71):
    rng=np.random.default_rng(seed);ls=[];used=set()
    for i,l in enumerate(OBS['leaf_landmarks']):
        ax=lookup[l['axis']];at=ax['nodes'][l['node']];junction=world(l['junction'],at[1]-.012)
        direction=world(l['tip'],junction[1])-junction
        ls.append(dict(id=f'leaf-observed-{i}',axis=l['axis'],node=l['node'],at=at,
          junction=junction,direction=unit(direction),length=float(np.linalg.norm(direction)),
          observed=True,n=7 if l['junction'][1]>140 else 5,twist=float(rng.uniform(-.25,.25)),tone=float(rng.uniform(.85,1.1))))
        used.add((l['axis'],l['node']))
    for ax in axes:
        for node,at in enumerate(ax['nodes'][1:],1):
            if (ax['id'],node) in used:continue
            f=node/(len(ax['nodes'])-1)
            # Unobserved organs: one coherent size trend; recorded as hypotheses.
            secondary='/secondary-' in ax['id']
            size=(.045+.043*(1-at[2]/HEIGHT))*(.8+.3*rng.random())*(.58 if secondary else 1)
            angle=rng.uniform(-2.8,2.8)
            d=np.array([math.cos(angle),rng.uniform(-.4,.4),math.sin(angle)])
            d=unit(d)
            junction=at+d*size*.5
            ls.append(dict(id=f"leaf-assumed-{ax['id']}-{node}",axis=ax['id'],node=node,
              at=at,junction=junction,direction=d,length=size,observed=False,
              n=3 if secondary and f>.6 else 5 if secondary or f>.8 else 7,
              twist=float(rng.uniform(-.7,.7)),tone=float(rng.uniform(.8,1.15))))
    return ls

def blades(leaf,params):
    # Connected palmate leaves; Futura75 measured margin profiles are a transfer.
    length=leaf['length']*(1 if leaf['observed'] else params['leaf_scale'])
    n=leaf['n'];ids=list(range(7)) if n==7 else list(range(1,6)) if n==5 else [2,3,4]
    angles=np.radians([-85,-56,-27,0,28,58,86] if n==7 else [-60,-30,0,30,60] if n==5 else [-38,0,38])
    rel=[.34,.61,.85,1,.84,.6,.33] if n==7 else [.6,.85,1,.85,.59] if n==5 else [.7,1,.7]
    direct=leaf['direction'];side=unit(np.cross([0,-1,0],direct));normal=unit(np.cross(direct,side))
    # Twist affects 3D and foreshortening, rather than acting as image texture.
    lateral=side*math.cos(leaf['twist'])+normal*math.sin(leaf['twist'])
    nr=unit(np.cross(direct,lateral));out=[]
    for k,idx in enumerate(ids):
        angle=angles[k];d=direct*math.cos(angle)+lateral*math.sin(angle);b=unit(np.cross(nr,d))
        L=length*rel[k];p=PROFILES[idx];t=np.linspace(0,1,41)
        low=np.interp(t,np.linspace(0,1,81),p['low']);high=np.interp(t,np.linspace(0,1,81),p['high'])
        baseline=leaf['junction']+t[:,None]*d*L+nr[None,:]*L*(params['cup']*np.sin(np.pi*t))[:,None]
        width=params['width']*(1+.06*math.sin(idx+leaf['node']))
        lo=baseline+low[:,None]*L*width*b
        hi=baseline+high[:,None]*L*width*b
        # The extracted profiles can both lie on one side of the nominal axis.
        # A straight central vertex strip then folds outside the outline.
        # Use its medial curve instead (a geometric approximation to a midrib).
        centers=(lo+hi)*.5
        out.append(dict(id=f"{leaf['id']}/blade-{k}",lo=lo,hi=hi,center=centers,
                        outline=np.concatenate([lo,hi[::-1]]),L=L))
    return out

def foliage_polygons(ls,params):
    polys=[]
    for l in ls:
        for b in blades(l,params):polys.append(project(b['outline']))
    return polys

def photo_mask(threshold=42):
    a=np.array(REFERENCE,float);r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
    mask=(g>threshold)&(g>r*1.06)&(g>b*1.18)
    mask[:25]=False;mask[425:]=False;mask[:,:25]=False;mask[:,355:]=False
    return mask

def draw_mask(axes,ls,params,half=False):
    sc=.5 if half else 1.;im=Image.new('L',(round(W*sc),round(H*sc)))
    draw=ImageDraw.Draw(im)
    for ax in axes:
        pts=project(ax['points'])*sc
        draw.line([tuple(p) for p in pts],fill=255,width=max(1,round(ax['r0']*2/PX*sc)))
    for l in ls:
        pts=project([l['at'],l['junction']])*sc
        draw.line([tuple(p) for p in pts],fill=255,width=1)
    for poly in foliage_polygons(ls,params):draw.polygon([tuple(x*sc) for x in poly],fill=255)
    return np.array(im)>0

def score(mask,target):
    # Raw leaf IoU and coarse occupancy expose separate coverage failure modes.
    iou=np.logical_and(mask,target).sum()/max(1,np.logical_or(mask,target).sum())
    a=binary_closing(mask,iterations=3);b=binary_closing(target,iterations=3)
    coarse=np.logical_and(a,b).sum()/max(1,np.logical_or(a,b).sum())
    bands=np.mean(np.abs(np.array([x.mean() for x in np.array_split(mask,12)])-
                          np.array([x.mean() for x in np.array_split(target,12)])))
    return {'raw_iou':float(iou),'coarse_iou':float(coarse),'band_occupancy_mae':float(bands),
            'loss':float(.45*(1-iou)+.45*(1-coarse)+.1*bands)}

def fit(axes,ls,target):
    params={'leaf_scale':.8,'width':.8,'cup':.1};history=[]
    grids={'leaf_scale':np.linspace(.9,1.65,7),'width':np.linspace(.65,1.05,6),'cup':np.linspace(-.08,.28,5)}
    initial=params.copy();initial_score=score(draw_mask(axes,ls,params),target)
    for epoch in range(2):
        for key,values in grids.items():
            tests=[]
            for v in values:
                p={**params,key:float(v)};s=score(draw_mask(axes,ls,p),target);tests.append((s['loss'],p,s))
            _,params,s=min(tests,key=lambda x:x[0]);history.append(dict(epoch=epoch,parameter=key,params=params.copy(),metrics=s))
    return initial,params,initial_score,history

class Mesh:
    def __init__(self):self.parts=[]
    def add(self,name,kind,positions,indices,color,parent=None):
        positions=np.round(positions,7);indices=np.array(indices).reshape(-1,3)
        areas=np.linalg.norm(np.cross(positions[indices[:,1]]-positions[indices[:,0]],positions[indices[:,2]]-positions[indices[:,0]]),axis=1)
        indices=indices[areas>1e-14]
        self.parts.append(dict(id=name,kind=kind,parent=parent,positions=positions.reshape(-1).tolist(),indices=indices.reshape(-1).tolist(),color=color))
    def tube(self,name,kind,points,r0,r1,color,parent=None,sides=6):
        p=np.array(points);rings=[]
        previous=None
        for i,pos in enumerate(p):
            d=unit(p[min(i+1,len(p)-1)]-p[max(i-1,0)])
            b=unit(np.cross(d,[0,1,0] if abs(d[1])<.9 else [1,0,0]));n=unit(np.cross(d,b))
            if previous is not None and b@previous<0:b=-b;n=-n
            previous=b;r=r0+(r1-r0)*i/(len(p)-1)
            rings.extend([pos+r*(b*math.cos(j*2*math.pi/sides)+n*math.sin(j*2*math.pi/sides)) for j in range(sides)])
        ids=[]
        for i in range(len(p)-1):
            for j in range(sides):
                a=i*sides+j;b=i*sides+(j+1)%sides;c=b+sides;d=a+sides
                ids.extend([[a,b,c],[a,c,d]])
        self.add(name,kind,np.array(rings),ids,color,parent)

def build_mesh(axes,ls,params):
    mesh=Mesh()
    for ax in axes:mesh.tube(ax['id'],'axis',ax['points'],ax['r0'],ax['r1'],'#708044',ax['parent'])
    for l in ls:
        midpoint=(l['at']+l['junction'])/2+np.array([0,.003,0])
        mesh.tube(l['id']+'/petiole','petiole',[l['at'],midpoint,l['junction']],.00065,.00035,'#7f9655',l['axis'])
        for b in blades(l,params):
            vertices=np.stack([b['lo'],b['center'],b['hi']],axis=1).reshape(-1,3);ids=[]
            for i in range(40):
                for j in range(2):a=i*3+j;ids.extend([[a,a+3,a+4],[a,a+4,a+1]])
            c=np.clip(np.array([61,111,37])*l['tone'],0,255).astype(int)
            color='#'+''.join(f'{v:02x}' for v in c)
            mesh.add(b['id'],'leaflet',vertices,ids,color,l['id']+'/petiole')
            mesh.tube(b['id']+'/midrib','vein',b['center'][::4],b['L']*.0035,b['L']*.0003,'#81944c',b['id'],4)
    return mesh.parts

def json_write(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def main():
    OUT.mkdir(parents=True,exist_ok=True);(HERE/'evidence').mkdir(exist_ok=True)
    shutil.copy2(HERE/OBS['image'],OUT/'reference.jpg')
    target=photo_mask()
    axes,lookup=topology();ls=leaves(axes,lookup)
    initial,params,initial_score,history=fit(axes,ls,target)
    print('Initial / fitted',initial_score,history[-1]['metrics'],flush=True)
    annotation=REFERENCE.copy();d=ImageDraw.Draw(annotation)
    for a in OBS['axes']:
        d.line([tuple(p) for p in a['xy']],fill='#ffbb68' if 'hidden' not in a['confidence'] else '#cc7bec',width=2)
        for x,y in a['xy']:d.ellipse([x-2,y-2,x+2,y+2],fill='#ffe0a8')
    for l in OBS['leaf_landmarks']:
        d.line([tuple(l['junction']),tuple(l['tip'])],fill='#80f3ed',width=1)
    annotation.save(OUT/'annotations.png')
    variants=[]
    shape_params={**params,'width':.65,'cup':.06}
    for name,depth,p in [('initial',0,initial),('fitted',0,params),('shape-constrained',0,shape_params),('depth-b',1,shape_params),('depth-c',2,shape_params)]:
        ax,lk=topology(depth);ll=leaves(ax,lk);parts=build_mesh(ax,ll,p)
        json_write(OUT/f'{name}.json',{'name':name,'parts':parts,'axes':[dict(id=a['id'],parent=a['parent'],node=a['node'],nodes=a['nodes'].tolist(),r0=a['r0'],r1=a['r1']) for a in ax],
          'leaves':[dict(id=l['id'],axis=l['axis'],node=l['node'],at=l['at'].tolist(),junction=l['junction'].tolist(),observed=l['observed']) for l in ll],
          'parameters':p,'status':'Connected geometric hypothesis; no contact or growth solver.'})
        mask=draw_mask(ax,ll,p,False);Image.fromarray(mask).save(OUT/f'{name}-mask.png')
        rgb=np.zeros((H,W,3),np.uint8)+np.array([18,23,18],np.uint8)
        rgb[target&mask]=[201,219,184];rgb[target&~mask]=[244,175,64];rgb[~target&mask]=[164,95,224]
        Image.fromarray(rgb).save(OUT/f'{name}-difference.png')
        variants.append({'id':name,'metrics':score(mask,target),'axis_count':len(ax),'leaf_count':len(ll),'part_count':len(parts),
          'mask_sensitivity':[{'green_threshold':t,**score(mask,photo_mask(t))} for t in [30,42,60]],
          'selection':'visual hypothesis, not fitted leaf width' if name!='fitted' and name!='initial' else 'image fit'})
    # This is an annotation consistency check, never independent geometry accuracy.
    errors=[]
    for a in axes:
        if a['parent']:errors.append(float(np.linalg.norm(a['nodes'][0]-lookup[a['parent']]['nodes'][a['node']])))
    manifest={'source':OBS['source'],'source_url':OBS['source_url'],'source_hash':hashlib.sha256((HERE/OBS['image']).read_bytes()).hexdigest(),
       'scale':{'cohort_median_height_m':HEIGHT,'cohort_median_radius_m':RADIUS,'m_per_pixel':PX,'actual_photo_scale_known':False},
       'camera':{'width':W,'height':H,'root_pixel':ROOTPX.tolist(),'m_per_pixel':PX},
       'segmentation':'Green-dominant pixels inside fixed ROI; excludes white support/pot; no semantic ground truth.',
       'initial_parameters':initial,'fitted_parameters':params,'shape_parameters':shape_params,'fitting_history':history,'variants':variants,
       'metric_protocol':'All fitting and reporting at native 381x444 pixels; binary closing 3 iterations. Earlier half-resolution fitting history is archived and not directly comparable.',
       'scope':{'independent_validation':False,'cultivar_geometry_distribution_fitted':False,'whole_plant_physics':False,'fresh_mass_measured':False},
       'checks':{'max_attachment_error_m':max(errors),'persistent_part_ids':True,'annotation_axes':len(axes),'observed_leaf_landmarks':len(OBS['leaf_landmarks'])},
       'sources':[OBS['source_url'],'../nominal-cultivars-v1/nominal-models.json','../reference-data/provenance.json'],
       'limits':['Single low-resolution image is ambiguous in depth and topology.','Cohort median scale is not the individual photo scale.','Futura75 margins are transferred to Cherry Wine; not cultivar-matched.','Unobserved leaves and all depth hypotheses are synthetic assumptions.','Image fitting cannot establish stiffness, contact, growth or cutting behavior.']}
    json_write(OUT/'manifest.json',manifest)
    for f in ['annotations.png','initial-difference.png','fitted-difference.png','manifest.json']:
        shutil.copy2(OUT/f,HERE/'evidence'/f)
    for f in ['index.html','viewer.js']:shutil.copy2(HERE/f,OUT/f)
    print('Built',OUT,flush=True)

if __name__=='__main__':main()
