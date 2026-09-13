"""Geometry/software checks only. These do not validate living-plant mechanics."""
import json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[2]/'runs/hemp-photo-fit-v1'
manifest=json.loads((OUT/'manifest.json').read_text())
checks=[]
for variant in manifest['variants']:
    model=json.loads((OUT/(variant['id']+'.json')).read_text())
    parts=model['parts'];ids={p['id'] for p in parts}
    assert len(ids)==len(parts), 'Duplicate organ mesh IDs'
    axes={a['id']:a for a in model['axes']}
    attachments=[];triangles=0;minimum_area=float('inf')
    for a in axes.values():
        if a['parent']:
            attachments.append(np.linalg.norm(np.array(a['nodes'][0])-axes[a['parent']]['nodes'][a['node']]))
    for l in model['leaves']:
        attachments.append(np.linalg.norm(np.array(l['at'])-axes[l['axis']]['nodes'][l['node']]))
    for p in parts:
        assert p['parent'] is None or p['parent'] in ids,(p['id'],'unresolved parent')
        xyz=np.array(p['positions']).reshape(-1,3);ix=np.array(p['indices']).reshape(-1,3)
        assert np.isfinite(xyz).all(), 'Nonfinite geometry'
        assert len(ix)>0 and ix.min()>=0 and ix.max()<len(xyz), 'Invalid triangle index'
        area=np.linalg.norm(np.cross(xyz[ix[:,1]]-xyz[ix[:,0]],xyz[ix[:,2]]-xyz[ix[:,0]]),axis=1)/2
        assert area.min()>0, 'Degenerate triangle'
        minimum_area=min(minimum_area,float(area.min()));triangles+=len(ix)
    assert max(attachments)<1e-9, 'Disconnected organ origin'
    checks.append(dict(variant=variant['id'],parts=len(parts),triangles=triangles,
       max_attachment_error_m=float(max(attachments)),min_triangle_area_m2=minimum_area,
       finite=True,unique_ids=True,parent_references_resolve=True,nondegenerate=True))
report={'passed':True,'scope':'Software and topology consistency, not empirical botanical or mechanical validation.',
        'unchecked':['Self-contact/interpenetration','Branch stiffness and fresh mass','Depth accuracy','Cultivar generalization'],
        'variants':checks}
for path in [HERE/'evidence/geometry-checks.json',OUT/'geometry-checks.json']:
    path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
