"""Remote-only visual audit of completed SAM3 search outputs."""
import os,platform
if platform.system()!='Linux' or not os.environ.get('RUNPOD_POD_ID'):raise SystemExit('RunPod only')
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
root=Path('/workspace/sam3-comparison')
for folder in os.environ.get('POSTPROCESS_FOLDERS','grid-search,resolution-low,resolution-native').split(','):
 p=root/folder
 if not (p/'report.json').exists():continue
 report=json.loads((p/'report.json').read_text());im=Image.open(p/'input.png').convert('RGB');rgb=np.asarray(im);h,w=rgb.shape[:2]
 fg=np.load(p/'foreground-proxies.npz')['foreground'];scores={};semantic_rows=[]
 Image.fromarray((fg*255).astype('uint8')).save(p/'foreground-mask.png')
 rgba=np.dstack([rgb,(fg*255).astype('uint8')]);Image.fromarray(rgba).save(p/'plant-cutout.png')
 for organ,prompts in {'leaf':['leaf','leaflet'],'stem':['stem'],'flower':['flower']}.items():
  score=np.zeros((h,w),np.float32)
  for row in report['results']:
   if row['prompt'] not in prompts or row['grid'] not in report.get('selected_semantic_grids',[]):continue
   q=np.load(p/(row['prompt']+'-'+str(row['grid']))/'scores.npz')['all'];np.maximum(score,q,out=score)
  scores[organ]=score
 stack=np.stack(list(scores.values()));names=list(scores)
 for t in [.5,.25,.1]:
  active=stack>=t;count=active.sum(axis=0);label=np.argmax(stack,axis=0)+1;label[count==0]=0;label[count>1]=4
  label[~fg]=0
  colors=np.array([[247,190,53],[66,191,122],[54,172,233],[230,98,170],[164,100,231]],np.uint8)
  z=(rgb*.35).astype('uint8');z[fg]=colors[label[fg]]
  Image.fromarray(z).save(p/f'organs-{t}.png')
  row={'threshold':t,'leaf_only':int(((label==1)&fg).sum()),'stem_only':int(((label==2)&fg).sum()),'flower_only':int(((label==3)&fg).sum()),'conflicting_labels':int(((label==4)&fg).sum()),'unclassified':int(((label==0)&fg).sum()),'foreground':int(fg.sum())};semantic_rows.append(row)
  export=label.astype('uint8');export[fg&(label==0)]=5
  np.savez_compressed(p/f'proposed-organ-labels-{t}.npz',labels=export)
  Image.fromarray(export).save(p/f'proposed-organ-labels-{t}.png')
 (p/'semantic-audit.json').write_text(json.dumps({'label_ids':{'0':'background','1':'leaf tissue','2':'stem','3':'flower','4':'conflicting','5':'unclassified plant'},'notice':'Unverified text-prompt proposals. Colors clipped to foreground proxy for display only. Raw leakage scores remain un-clipped. Leaf and leaflet combined only as semantic tissue, never instance counts. Conflicts are not resolved by pretending confidence scores are calibrated between prompts.','results':semantic_rows},indent=2))
 # Contact sheet for inspection; native pixels remain available separately.
 panes=[('Reference',p/'input.png'),('Foreground estimate',p/'foreground-proxy.png'),('Proposed organs at 0.25',p/'organs-0.25.png')]
 canvas=Image.new('RGB',(1200,700),'#eff1e9');draw=ImageDraw.Draw(canvas)
 for i,(label,path) in enumerate(panes):
  img=Image.open(path).convert('RGB');img.thumbnail((390,650));canvas.paste(img,(i*400,40));draw.text((i*400+5,10),label,fill='#17372d')
 canvas.save(p/'overview.png')
print('POSTPROCESS_COMPLETE')
