"""RunPod-only native mask export and scale-agreement diagnostics."""
import os,platform
if platform.system()!='Linux' or not os.environ.get('RUNPOD_POD_ID'):raise SystemExit('RunPod only')
import json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
root=Path('/workspace/sam3-comparison/point-loop');out=root/'selected';out.mkdir(exist_ok=True)
def masks(round_id,target,condition):
    z=np.load(root/f'round-{round_id}'/f'{target}-{condition}-raw.npz');shape=tuple(z['shape'])
    return np.unpackbits(z['masks'],axis=1)[:,:shape[1]*shape[2]].reshape(shape).astype(bool)
rows=[];labels=np.zeros((444,381),dtype='uint16')
for index,target in enumerate(['exposed','overlap','dense'],1):
    a=masks(1,target,'crop-1x')[0];b=masks(1,target,'crop-4x')[0]
    assert not np.any(labels[a]),'Selected masks overlap; resolve identity before exporting'
    labels[a]=index;Image.fromarray(a.astype('uint8')*255).save(out/f'{target}-mask.png')
    rows.append({'target':target,'selected':{'round':1,'condition':'crop-1x','candidate':0},'status':'provisional assistant-reviewed visible leaflet','native_pixels':int(a.sum()),'4x_pixels':int(b.sum()),'native_vs_4x_mask_agreement_iou_NOT_accuracy':int((a&b).sum())/max(1,int((a|b).sum())),'mask_disagreement_pixels':int((a^b).sum())})
Image.fromarray(labels).save(out/'instance-labels.png')
rgb=np.asarray(Image.open('/workspace/sam3-comparison/input.png').convert('RGB')).copy()
colors=[[252,204,68],[65,224,165],[253,101,169]]
for i,c in enumerate(colors,1):rgb[labels==i]=c
Image.fromarray(rgb).save(out/'source-overlay.png')
(out/'labels.json').write_text(json.dumps({'background_id_0':'unknown/unannotated, not negative background','visible_only':True,'class':'leaflet','parent_leaf_id':None,'trainable':False,'independent_validation':False,'native_image_size':[381,444],'instances':rows},indent=2))
(out/'scale-comparison.json').write_text(json.dumps(rows,indent=2))
files=sorted(p for p in root.rglob('*') if p.is_file() and p.name!='SHA256SUMS')
(root/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(root))+'\n' for p in files))
print(json.dumps(rows,indent=2))
