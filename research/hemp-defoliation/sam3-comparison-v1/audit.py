"""Remote-only comparison against frozen visible geometry; no biology claims."""
from worker import require_remote
require_remote()
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
root=Path('/workspace/sam3-comparison');out=root/'results'
report=json.loads((out/'sam3/report.json').read_text());rows=[];panels=[]
for name in ['reference','broad-render','narrow-render']:
 p=out/'sam3'/name;pred=json.loads((p/'predictions.json').read_text());row={'image':name,'groups':[]}
 for i,g in enumerate(pred['groups']):
  row['groups'].append({'prompt':g['prompt'],'proposals':g['proposal_count'],'union_fraction':g['union_fraction']})
 if name!='reference':
  row['audit']={}
  for level,gidx in [('leaf',0),('leaflet',1)]:
   ids=np.load(root/f'baseline/synthetic-audit/{name}/{level}-ids.npz')['ids']
   organs=[v for v in np.unique(ids) if v>=0 and (ids==v).sum()>=16]
   row['audit'][level]={}
   for tag,path in [('sam2_default',root/f'baseline/sam2/{name}/masks-0.npz'),('sam2_recall',root/f'baseline/sam2-recall/{name}/masks-0.npz'),('sam3_text',p/f'masks-{gidx}.npz')]:
    masks=np.load(path)['masks'];scores=[]
    for v in organs:
     gt=ids==v;intersection=(masks & gt).sum(axis=(1,2));union=(masks | gt).sum(axis=(1,2))
     iou=intersection/np.maximum(1,union);scores.append(float(iou.max()) if len(iou) else 0)
    row['audit'][level][tag]={'visible_organs_ge16px':len(scores),'organs_with_any_mask_iou_ge05':sum(s>=.5 for s in scores),'median_best_iou':float(np.median(scores))}
 ims=[('Input',p/'input.png'),('SAM2 recall',root/f'baseline/sam2-recall/{name}/foliage-candidates.png'),('SAM3: leaf',p/'overlay-0.png'),('SAM3: leaflet',p/'overlay-1.png')]
 board=Image.new('RGB',(381*4,489),'#eff1e8');draw=ImageDraw.Draw(board)
 for j,(title,path) in enumerate(ims):
  board.paste(Image.open(path),(j*381,45));draw.text((j*381+8,9),name+' / '+title,fill='#20382b')
 panels.append(board);rows.append(row)
summary={'model':report['model'],'precision':report['precision'],'image_results':rows,'notice':'Best-overlap synthetic coverage only; not real-photo accuracy or one-to-one AP. SAM2 and SAM3 prompt interfaces differ.'}
(out/'summary.json').write_text(json.dumps(summary,indent=2))
board=Image.new('RGB',(1524,489*3))
for i,panel in enumerate(panels):board.paste(panel,(0,489*i))
board.save(out/'comparison.png')
print(json.dumps(summary,indent=2))
