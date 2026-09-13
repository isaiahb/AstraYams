"""Remote-only overlapping SAM3 tiling experiment; no real-photo ground truth."""
import os,platform
if platform.system()!='Linux' or not os.environ.get('RUNPOD_POD_ID'):
 raise SystemExit('REFUSED: RunPod Linux only; no model imports on Mac.')
import json,time,math,hashlib
from pathlib import Path
import numpy as np
import torch
from PIL import Image,ImageDraw
from scipy.optimize import linear_sum_assignment
from sam3.model_builder import build_sam3_image_model
from sam3.model.sam3_image_processor import Sam3Processor
root=Path('/workspace/sam3-comparison');out=root/'results/tiles-v1';out.mkdir(exist_ok=True)
assert torch.cuda.is_available()
torch.set_num_threads(2);torch.manual_seed(71)
engine=Sam3Processor(build_sam3_image_model(checkpoint_path=str(root/'sam3.pt'),load_from_HF=False,device='cuda'),device='cuda',confidence_threshold=.1)
def windows(w,h,n):
 if n==1:return [(0,0,w,h)]
 # 30% adjacent overlap. Last tile ends at the original image edge.
 tw=math.ceil(w/(n-(n-1)*.3));th=math.ceil(h/(n-(n-1)*.3))
 return [(round(i*(w-tw)/(n-1)),round(j*(h-th)/(n-1)),round(i*(w-tw)/(n-1))+tw,round(j*(h-th)/(n-1))+th) for j in range(n) for i in range(n)]
def dedup(items):
 # Prefer complete masks, then confidence. Suppress IoU duplicates, never union
 # masks merely because they overlap (neighboring leaves can legitimately overlap).
 ordered=sorted(items,key=lambda q:(q['edge'], -q['score']));kept=[]
 for q in ordered:
  if any((q['mask']&k['mask']).sum()/max(1,(q['mask']|k['mask']).sum())>=.5 for k in kept):continue
  kept.append(q)
 return kept
def evaluate(items,ids):
 organs=[int(v) for v in np.unique(ids) if v>=0 and (ids==v).sum()>=16]
 a=np.zeros((len(items),len(organs)))
 for i,q in enumerate(items):
  for j,v in enumerate(organs):
   gt=ids==v;a[i,j]=(q['mask']&gt).sum()/max(1,(q['mask']|gt).sum())
 matches=0
 if a.size:
  ii,jj=linear_sum_assignment(-((a>=.5).astype(float)+.001*a));matches=int((a[ii,jj]>=.5).sum())
 return {'visible_whole_leaves_ge16px':len(organs),'predictions':len(items),'one_to_one_matches_iou05':matches,'precision':matches/max(1,len(items)),'recall':matches/max(1,len(organs))}
def overlay(im,items):
 rgb=np.asarray(im).astype(float).copy();rng=np.random.default_rng(71)
 for q in items:rgb[q['mask']]=.5*rgb[q['mask']]+.5*rng.integers(35,240,3)
 return Image.fromarray(rgb.astype('uint8'))
rows=[];panels=[]
for name in ['reference','broad-render','narrow-render']:
 im=Image.open(root/f'results/sam3/{name}/input.png').convert('RGB');w,h=im.size
 base=out/name;base.mkdir(exist_ok=True);im.save(base/'input.png')
 ids=None if name=='reference' else np.load(root/f'baseline/synthetic-audit/{name}/leaf-ids.npz')['ids']
 for n in [1,2,3]:
  start=time.monotonic();items=[];tiles=windows(w,h,n);dest=base/f'grid-{n}';dest.mkdir(exist_ok=True)
  guide=im.copy();d=ImageDraw.Draw(guide)
  for ti,(x0,y0,x1,y1) in enumerate(tiles):
   crop=im.crop((x0,y0,x1,y1));crop.save(dest/f'tile-{ti}.png');d.rectangle((x0,y0,x1-1,y1-1),outline='#ffdd33',width=1)
   with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
    state=engine.set_image(crop);r=engine.set_text_prompt(state=state,prompt='leaf')
    masks=r['masks'].detach().cpu().numpy().reshape(-1,crop.height,crop.width)>.5
    scores=r['scores'].detach().float().cpu().numpy().reshape(-1)
   for m,score in zip(masks,scores):
    if not m.any():continue
    edge=bool((x0>0 and m[:,:2].any()) or (x1<w and m[:,-2:].any()) or (y0>0 and m[:2].any()) or (y1<h and m[-2:].any()))
    full=np.zeros((h,w),bool);full[y0:y1,x0:x1]=m
    items.append({'mask':full,'score':float(score),'edge':edge,'tile':ti})
   del state,r
  guide.save(dest/'tile-layout.png')
  np.savez_compressed(dest/'raw-masks.npz',masks=np.stack([q['mask'] for q in items]) if items else np.zeros((0,h,w),bool))
  metadata=[{k:v for k,v in q.items() if k!='mask'} for q in items]
  (dest/'raw-metadata.json').write_text(json.dumps({'tiles_xyxy':tiles,'proposals':metadata},indent=2))
  for threshold in [.5,.1]:
   selected=[q for q in items if q['score']>=threshold];all_merged=dedup(selected);complete=dedup([q for q in selected if not q['edge']])
   tag='standard' if threshold==.5 else 'low-confidence'
   overlay(im,all_merged).save(dest/f'{tag}-all.png');overlay(im,complete).save(dest/f'{tag}-complete.png')
   np.savez_compressed(dest/f'{tag}-complete.npz',masks=np.stack([q['mask'] for q in complete]) if complete else np.zeros((0,h,w),bool))
   row={'image':name,'grid':n,'tiles':len(tiles),'threshold':threshold,'raw':len(selected),'edge_fragments':sum(q['edge'] for q in selected),'deduplicated_all':len(all_merged),'deduplicated_complete':len(complete),'seconds_grid_both_thresholds':time.monotonic()-start}
   if ids is not None:row['complete_audit']=evaluate(complete,ids);row['all_audit']=evaluate(all_merged,ids)
   rows.append(row);print(json.dumps(row),flush=True)
 # Panels compare full vs tiled with the same display and no filtering hidden.
 for threshold,tag in [(.5,'standard'),(.1,'low-confidence')]:
  board=Image.new('RGB',(w*4,h+44),'#eef1e8');draw=ImageDraw.Draw(board)
  for i,(label,path) in enumerate([('Input',base/'input.png')]+[(f'{n}x{n} / complete masks',base/f'grid-{n}/{tag}-complete.png') for n in [1,2,3]]):
   board.paste(Image.open(path),(i*w,44));draw.text((i*w+7,7),name+' / '+label,fill='#18352c');draw.text((i*w+7,23),f'confidence >= {threshold}',fill='#18352c')
  board.save(base/f'{tag}-comparison.png')
report={'model':'facebook/sam3','prompt':'leaf','overlap':.3,'grids':[1,2,3],'thresholds':[.5,.1],'duplicate_mask_iou':.5,'edge_margin_px':2,'real_photo_ground_truth':False,'notice':'Counts are proposals, not measured leaf counts. Exact synthetic whole-leaf scoring uses one-to-one IoU >=0.5 matching. Crop-edge fragments kept separately. Low confidence is diagnostic. Cropping cannot recover absent pixels.','results':rows}
(out/'report.json').write_text(json.dumps(report,indent=2))
