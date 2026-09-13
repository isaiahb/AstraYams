"""Remote-only ray-cast visible organ masks; audit SAM proposals against scene IDs."""
from worker import require_remote
require_remote()
import json
from pathlib import Path
import numpy as np
import open3d as o3d
from PIL import Image

ROOT=Path('/workspace/plant-pilot')
camera=json.loads((ROOT/'geometry/manifest.json').read_text())['camera']
W,H=camera['width'],camera['height'];px=camera['m_per_pixel'];rx,ry=camera['root_pixel']
reports=[]
for name,model_name in [('broad-render','fitted'),('narrow-render','shape-constrained')]:
    data=json.loads((ROOT/f'geometry/{model_name}.json').read_text())
    vertices=[];indices=[];owners=[];offset=0;labels=[]
    for i,part in enumerate(data['parts']):
        xyz=np.array(part['positions']).reshape(-1,3);ix=np.array(part['indices']).reshape(-1,3)
        vertices.append(xyz);indices.append(ix+offset);owners.extend([i]*len(ix));offset+=len(xyz)
        pid=part['id'];kind=part['kind']
        blade=pid.split('/midrib')[0] if kind=='vein' else pid if kind=='leaflet' else None
        leaf=blade.split('/blade-')[0] if blade else None
        labels.append({'id':pid,'kind':kind,'leaflet':blade,'leaf':leaf})
    mesh=o3d.t.geometry.TriangleMesh(o3d.core.Tensor(np.concatenate(vertices),dtype=o3d.core.Dtype.Float32),
                                   o3d.core.Tensor(np.concatenate(indices),dtype=o3d.core.Dtype.UInt32))
    scene=o3d.t.geometry.RaycastingScene(nthreads=2);scene.add_triangles(mesh)
    x,y=np.meshgrid(np.arange(W)+.5,np.arange(H)+.5)
    rays=np.stack([(x-rx)*px,np.full_like(x,-4),(ry-y)*px,np.zeros_like(x),np.ones_like(x),np.zeros_like(x)],axis=-1).astype('float32')
    hit=scene.cast_rays(o3d.core.Tensor(rays));tri=hit['primitive_ids'].numpy();valid=np.isfinite(hit['t_hit'].numpy())
    part_ids=np.full((H,W),-1,dtype='int32');part_ids[valid]=np.array(owners)[tri[valid]]
    dest=ROOT/'results/synthetic-audit'/name;dest.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(dest/'visible-parts.npz',part_ids=part_ids,depth=hit['t_hit'].numpy())
    (dest/'part-labels.json').write_text(json.dumps(labels))
    sam=np.load(ROOT/f'results/sam2/{name}/masks-0.npz')['masks']
    row={'image':name,'notice':'Scene-derived visible masks; SAM proposals remain unlabeled. This is a render-domain audit only.','levels':{}}
    for level in ['leaf','leaflet']:
        organ_names=sorted({x[level] for x in labels if x[level]})
        organ_index={x:i for i,x in enumerate(organ_names)}
        lookup=np.array([organ_index.get(x[level],-1) for x in labels]);ids=np.full((H,W),-1,dtype='int32');ids[valid]=lookup[part_ids[valid]]
        rng=np.random.default_rng(71);colors=rng.integers(40,245,(len(organ_names),3),dtype='uint8')
        rgb=np.zeros((H,W,3),dtype='uint8')+18;fg=ids>=0;rgb[fg]=colors[ids[fg]]
        Image.fromarray(rgb).save(dest/(level+'-ids.png'))
        organ_reports=[]
        for k,organ in enumerate(organ_names):
            mask=ids==k;area=int(mask.sum())
            if area<16:continue # fixed visibility gate, reported explicitly
            intersection=(sam&mask).sum(axis=(1,2));union=(sam|mask).sum(axis=(1,2));iou=intersection/np.maximum(union,1)
            best=int(np.argmax(iou)) if len(iou) else None
            organ_reports.append({'id':organ,'visible_pixels':area,'best_proposal':best,'best_iou':float(iou[best]) if best is not None else 0})
        row['levels'][level]={'total_scene_organs':len(organ_names),'visible_at_least_16px':len(organ_reports),
            'fraction_with_any_proposal_iou_ge_05':float(np.mean([x['best_iou']>=.5 for x in organ_reports])) if organ_reports else None,
            'not_one_to_one_matching':True,'organs':organ_reports}
        np.savez_compressed(dest/(level+'-ids.npz'),ids=ids)
    reports.append(row)
(ROOT/'results/synthetic-audit/report.json').write_text(json.dumps(reports,indent=2))
print(json.dumps([{k:v for k,v in r.items() if k!='levels'}|{'levels':{k:{a:b for a,b in v.items() if a!='organs'} for k,v in r['levels'].items()}} for r in reports],indent=2))
