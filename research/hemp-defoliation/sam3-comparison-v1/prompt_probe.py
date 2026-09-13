"""Remote diagnostic, kept separate from the frozen comparison. No GT claims."""
from worker import require_remote
require_remote()
from pathlib import Path
import json,time
import numpy as np
import torch
from PIL import Image,ImageDraw
from sam3.model_builder import build_sam3_image_model
from sam3.model.sam3_image_processor import Sam3Processor
root=Path('/workspace/sam3-comparison');out=root/'results/prompt-probe';out.mkdir(exist_ok=True)
torch.set_num_threads(2);torch.manual_seed(71)
model=build_sam3_image_model(checkpoint_path=str(root/'sam3.pt'),load_from_HF=False,device='cuda')
engine=Sam3Processor(model,device='cuda',confidence_threshold=.5)
rows=[]
def run(name,im,prompt=None,box=None,threshold=.5):
 engine.confidence_threshold=threshold;start=time.monotonic()
 with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
  state=engine.set_image(im)
  if prompt is not None:result=engine.set_text_prompt(state=state,prompt=prompt)
  if box is not None:
   x0,y0,x1,y1=box;w,h=im.size
   result=engine.add_geometric_prompt(box=[(x0+x1)/(2*w),(y0+y1)/(2*h),(x1-x0)/w,(y1-y0)/h],label=True,state=state)
  masks=result['masks'].detach().cpu().numpy().reshape(-1,im.height,im.width).astype(bool)
  scores=result['scores'].detach().float().cpu().numpy().reshape(-1)
 dest=out/name;dest.mkdir(exist_ok=True);rgb=np.asarray(im).astype(float);rng=np.random.default_rng(71)
 for m in masks:rgb[m]=.5*rgb[m]+.5*rng.integers(35,240,3)
 overlay=Image.fromarray(rgb.astype('uint8'))
 if box:ImageDraw.Draw(overlay).rectangle(box,outline='white',width=1)
 overlay.save(dest/'overlay.png');im.save(dest/'input.png');np.savez_compressed(dest/'masks.npz',masks=masks)
 row={'name':name,'prompt':prompt,'example_box_xyxy':box,'threshold':threshold,'proposals':len(masks),'scores':scores.tolist(),'seconds':time.monotonic()-start}
 rows.append(row);print(name,len(masks),flush=True)
for image in ['reference','broad-render','narrow-render']:
 im=Image.open(root/f'results/sam3/{image}/input.png').convert('RGB')
 for prompt in ['plant leaf','green leaf','leaves','narrow leaf','leaf blade']:
  run(image+'-'+prompt.replace(' ','-'),im,prompt=prompt)
 # Lower threshold is an explicit exploratory diagnostic, never baseline replacement.
 run(image+'-leaf-low-confidence',im,prompt='leaf',threshold=.1)
ref=Image.open(root/'results/sam3/reference/input.png').convert('RGB')
# Manually selected visible compound-leaf region; not a ground-truth annotation.
box=[76,130,132,167]
run('reference-example-only',ref,box=box)
run('reference-leaf-plus-example',ref,prompt='leaf',box=box)
for tag,crop in [('upper',[55,20,325,225]),('middle',[55,125,350,335]),('lower',[50,230,345,430])]:
 im=ref.crop(crop);run('reference-crop-'+tag,im,prompt='leaf');rows[-1]['crop_xyxy']=crop
(out/'report.json').write_text(json.dumps({'status':'exploratory, no holdout or real organ labels','results':rows},indent=2))
