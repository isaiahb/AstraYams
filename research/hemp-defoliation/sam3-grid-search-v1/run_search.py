"""RunPod-only SAM3 grid sweep. Foreground proxies are NOT organ ground truth."""
import os,platform
if platform.system()!='Linux' or not os.environ.get('RUNPOD_POD_ID'):
 raise SystemExit('Remote RunPod execution only; no ML imports on Mac')
import time,json,math,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import torch
from sam3.model_builder import build_sam3_image_model
from sam3.model.sam3_image_processor import Sam3Processor
root=Path('/workspace/sam3-comparison');out=root/os.environ.get('SEARCH_OUT','grid-search');out.mkdir(exist_ok=True)
start=time.monotonic();deadline=start+int(os.environ.get('SEARCH_SECONDS','3900'))
input_path=root/os.environ.get('SEARCH_INPUT','input.png');im=Image.open(input_path).convert('RGB');a=np.asarray(im).astype(float);h,w=a.shape[:2]
im.save(out/'input.png')
# Reference has green organs, a near-black background, a white frame and tag.
# Ignore border and bottom support, not dark plant areas inside the evaluation ROI.
roi=np.zeros((h,w),bool);roi[3:int(h*.94),3:w-3]=True
bg=np.median(np.concatenate([a[5:30,5:40].reshape(-1,3),a[5:30,-40:-5].reshape(-1,3)]),axis=0)
g=a[:,:,1];r=a[:,:,0];b=a[:,:,2]
core=roi&(g-bg[1]>30)&(g-r>12)&(g-b>20)
fg=roi&(g-bg[1]>12)&(g-r>4)&(g-b>8)
# Uncertain edge band is excluded from definite-background leakage.
permissive=roi&(g-bg[1]>6)&(g-r>1)&(g-b>3)
background=roi&~permissive
np.savez_compressed(out/'foreground-proxies.npz',core=core,foreground=fg,permissive=permissive,roi=roi)
proxy=np.zeros((h,w,3),np.uint8);proxy[permissive]=[110,100,35];proxy[fg]=[75,135,50];proxy[core]=[115,245,80];proxy[~roi]=[65,65,65]
Image.fromarray(proxy).save(out/'foreground-proxy.png')
meta={'input_sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),'image_size':[w,h],'background_rgb':bg.tolist(),'foreground_proxy_pixels':int(fg.sum()),'core_pixels':int(core.sum()),'excluded':'3px image border; bottom 6% stand. White tag excluded by green dominance.','proxy_not_ground_truth':True,'overlap':.3,'grids_requested':[int(n) for n in os.environ.get('SEARCH_GRIDS','1,3,5,10,20,25,50,100').split(',')],'thresholds':[.5,.25,.1],'tile_skip':'No permissive foreground pixels; score only retained tiles. Skipped background tiles are not tested for false positives.','results':[]}
(out/'protocol.json').write_text(json.dumps(meta,indent=2))
assert torch.cuda.is_available();torch.set_num_threads(2);torch.manual_seed(71)
engine=Sam3Processor(build_sam3_image_model(checkpoint_path=str(root/'sam3.pt'),load_from_HF=False,device='cuda'),device='cuda',confidence_threshold=.1)
def windows(n):
 if n==1:return [(0,0,w,h)]
 tw=math.ceil(w/(n-(n-1)*.3));th=math.ceil(h/(n-(n-1)*.3))
 return [(round(i*(w-tw)/(n-1)),round(j*(h-th)/(n-1)),round(i*(w-tw)/(n-1))+tw,round(j*(h-th)/(n-1))+th) for j in range(n) for i in range(n)]
def metrics(score,t):
 m=(score>=t)&roi;tp=int((m&fg).sum());pred=int(m.sum());fp=int((m&background).sum())
 return {'threshold':t,'foreground_coverage':tp/max(1,int(fg.sum())),'core_coverage':int((m&core).sum())/max(1,int(core.sum())),'proxy_precision':tp/max(1,pred),'proxy_iou':tp/max(1,int((m|fg).sum())),'definite_background_pixels':fp,'background_fraction_of_prediction':fp/max(1,pred),'predicted_pixels':pred}
def visual(score,t,path):
 m=score>=t;z=(a*.28).astype('uint8');z[fg&~m]=[240,65,85];z[fg&m]=[60,205,140];z[background&m]=[70,145,255]
 Image.fromarray(z).save(path)
def sweep(n,prompt):
 dest=out/(prompt.replace(' ','-')+'-'+str(n));dest.mkdir(exist_ok=True)
 if (dest/'result.json').exists():return json.loads((dest/'result.json').read_text())
 tiles=windows(n);scoremap=np.zeros((h,w),np.float32);edge_map=np.zeros((h,w),np.float32)
 count=0;edges=0;processed=0;skipped=0;t0=time.monotonic();trace=[];cutoff=False
 for ti,(x0,y0,x1,y1) in enumerate(tiles):
  if time.monotonic()>deadline:cutoff=True;break
  if not permissive[y0:y1,x0:x1].any():skipped+=1;continue
  crop=im.crop((x0,y0,x1,y1))
  with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
   state=engine.set_image(crop);res=engine.set_text_prompt(state=state,prompt=prompt)
   masks=res['masks'].detach().cpu().numpy().reshape(-1,crop.height,crop.width)>.5
   scores=res['scores'].detach().float().cpu().numpy().reshape(-1)
  edgeflags=[]
  for m,s in zip(masks,scores):
   if not m.any():edgeflags.append(False);continue
   edge=bool((x0>0 and m[:,:2].any())or(x1<w and m[:,-2:].any())or(y0>0 and m[:2].any())or(y1<h and m[-2:].any()))
   edgeflags.append(edge);count+=1;edges+=int(edge)
   patch=scoremap[y0:y1,x0:x1];np.maximum(patch,m*s,out=patch)
   if not edge:
    patch=edge_map[y0:y1,x0:x1];np.maximum(patch,m*s,out=patch)
  # Keep lossless crop-local proposals; no full-image N x H x W allocation.
  if len(masks):
   np.savez_compressed(dest/f'tile-{ti}.npz',masks=np.packbits(masks.reshape(len(masks),-1),axis=1),shape=np.array(masks.shape),scores=scores,box=np.array([x0,y0,x1,y1]),edge=np.array(edgeflags))
  trace.append({'tile':ti,'box':[x0,y0,x1,y1],'proposals':len(scores)})
  processed+=1;del state,res
  if processed%100==0:print(json.dumps({'grid':n,'prompt':prompt,'processed':processed,'total_tiles':len(tiles),'seconds':round(time.monotonic()-t0,1)}),flush=True)
 np.savez_compressed(dest/'scores.npz',all=scoremap,complete=edge_map)
 row={'grid':n,'prompt':prompt,'crop_size':[tiles[0][2],tiles[0][3]],'total_tiles':len(tiles),'processed':processed,'skipped_empty':skipped,'complete_run':not cutoff,'proposals':count,'edge_proposals':edges,'seconds':time.monotonic()-t0,'all_mask_metrics':[metrics(scoremap,t) for t in [.5,.25,.1]],'complete_mask_metrics':[metrics(edge_map,t) for t in [.5,.25,.1]]}
 for t in [.5,.25,.1]:visual(scoremap,t,dest/f'coverage-{t}.png')
 (dest/'result.json').write_text(json.dumps(row,indent=2));(dest/'tiles.json').write_text(json.dumps(trace))
 meta['results'].append(row);(out/'report.json').write_text(json.dumps(meta,indent=2));print(json.dumps(row),flush=True)
 return row
rows=[]
for n in meta['grids_requested']:
 if time.monotonic()>deadline-120:break
 rows.append(sweep(n,'leaf'))
# Grid scale chosen from proxy IoU, not maximum area alone. Multi-scale semantics
# use two best scales <=10 to retain recognizable organ context.
valid=[v for v in rows if v['complete_run'] and v['grid']<=10]
best=sorted(valid,key=lambda q:q['all_mask_metrics'][0]['proxy_iou'],reverse=True)[:2]
for row in best:
 for prompt in ['stem','flower','leaflet']:
  if time.monotonic()>deadline-30:break
  sweep(row['grid'],prompt)
meta['elapsed_seconds']=time.monotonic()-start;meta['device']=torch.cuda.get_device_name(0);meta['pod_id']=os.environ['RUNPOD_POD_ID']
meta['selected_semantic_grids']=[r['grid'] for r in best]
(out/'report.json').write_text(json.dumps(meta,indent=2))
print('SEARCH_COMPLETE',flush=True)
