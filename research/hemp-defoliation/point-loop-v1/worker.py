"""RunPod-only interactive segmentation experiment and raster review exports."""
import os, platform
if platform.system() != 'Linux' or not os.environ.get('RUNPOD_POD_ID'):
    raise SystemExit('RunPod only: no raster processing or ML on the Mac')
import json, time, hashlib, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import torch
from sam3.model_builder import build_sam3_image_model
from sam3.model.sam3_image_processor import Sam3Processor

root=Path('/workspace/sam3-comparison')
plan=json.loads(Path(sys.argv[1]).read_text())
out=root/'point-loop'/('round-'+str(plan['round'])); out.mkdir(parents=True,exist_ok=True)
input_path=root/'input.png'
assert hashlib.sha256(input_path.read_bytes()).hexdigest()==plan['input_sha256']
im=Image.open(input_path).convert('RGB'); w,h=im.size
assert [w,h]==plan['image_size']
rgb=np.asarray(im)
if not torch.cuda.is_available(): raise SystemExit('CUDA required')
model=build_sam3_image_model(checkpoint_path=str(root/'sam3.pt'),load_from_HF=False,device='cuda',enable_inst_interactivity=True)
processor=Sam3Processor(model,device='cuda')
torch.manual_seed(71)
report={'plan':plan,'gpu':torch.cuda.get_device_name(0),'sam3_revision':subprocess.check_output(['git','-C','/workspace/sam3','rev-parse','HEAD'],text=True).strip(),'runs':[]}

def panel(mask,target,title,points=True):
    x0,y0,x1,y1=target['crop']; crop=im.crop(target['crop']).resize((408,408),Image.Resampling.NEAREST)
    a=np.asarray(crop).copy()
    if mask is not None:
        m=Image.fromarray(mask[y0:y1,x0:x1]).resize((408,408),Image.Resampling.NEAREST)
        mm=np.asarray(m).astype(bool)
        edge=mm.copy(); edge[1:-1,1:-1] &= ~(mm[2:,1:-1]&mm[:-2,1:-1]&mm[1:-1,2:]&mm[1:-1,:-2])
        a[mm]=(a[mm]*.65+np.array([40,220,160])*.35).astype('uint8'); a[edge]=[255,75,190]
    tile=Image.new('RGB',(408,446),'#edf0e5');tile.paste(Image.fromarray(a),(0,38));d=ImageDraw.Draw(tile);d.text((8,10),title,fill='#17382b')
    if points:
        for (x,y),label in zip(target['points'],target['labels']):
            px=(x-x0)*408/(x1-x0);py=38+(y-y0)*408/(y1-y0)
            c='#ffe239' if label else '#ff4545';d.ellipse((px-4,py-4,px+4,py+4),fill=c,outline='black')
    return tile

t0=time.monotonic()
with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
    for target in plan['targets']:
        panel(None,target,'Original pixels and prompts').save(out/(target['id']+'-original.png'))
        # Grid only on the remote worker, with source-image coordinate labels.
        crop=im.crop(target['crop']).resize((612,612),Image.Resampling.NEAREST);d=ImageDraw.Draw(crop)
        x0,y0,x1,y1=target['crop']
        for x in range((x0//5+1)*5,x1,5):
            px=(x-x0)*612/(x1-x0);d.line((px,0,px,612),fill='#777777',width=1);d.text((px+1,2),str(x),fill='white')
        for y in range((y0//5+1)*5,y1,5):
            py=(y-y0)*612/(y1-y0);d.line((0,py,612,py),fill='#777777',width=1);d.text((2,py+1),str(y),fill='white')
        crop.save(out/(target['id']+'-coordinates.png'))
        for condition in plan['conditions']:
            mode,scale_text=condition.split('-');scale=int(scale_text[0]);box=[0,0,w,h] if mode=='full' else target['crop']
            bx,by,ex,ey=box; bw,bh=ex-bx,ey-by
            image=im.crop(box)
            if scale!=1: image=image.resize((bw*scale,bh*scale),Image.Resampling.BICUBIC)
            state=processor.set_image(image)
            coords=(np.asarray(target['points'],dtype=np.float32)-[bx,by])*scale
            ts=time.monotonic()
            masks,scores,logits=model.predict_inst(state,point_coords=coords,point_labels=np.asarray(target['labels'],dtype=np.int32),multimask_output=True)
            def array(x):return x.detach().float().cpu().numpy() if torch.is_tensor(x) else np.asarray(x)
            masks=array(masks).astype(bool);scores=array(scores);logits=array(logits)
            global_masks=[];candidates=[]
            slug=target['id']+'-'+condition
            board=Image.new('RGB',(408*4,446));board.paste(panel(None,target,'Original pixels'),(0,0))
            for i,m in enumerate(masks):
                native=np.asarray(Image.fromarray(m).resize((bw,bh),Image.Resampling.NEAREST)).astype(bool)
                global_mask=np.zeros((h,w),bool);global_mask[by:ey,bx:ex]=native;global_masks.append(global_mask)
                image_panel=panel(global_mask,target,f'Candidate {i}; confidence {scores[i]:.3f}')
                image_panel.save(out/f'{slug}-candidate-{i}.png');board.paste(image_panel,((i+1)*408,0))
                candidates.append({'index':i,'model_predicted_iou_not_accuracy':float(scores[i]),'mask_pixels':int(global_mask.sum()),'positive_hits':[bool(global_mask[y,x]) for (x,y),l in zip(target['points'],target['labels']) if l],'negative_hits':[bool(global_mask[y,x]) for (x,y),l in zip(target['points'],target['labels']) if not l]})
            board.save(out/(slug+'-board.png'))
            gm=np.asarray(global_masks)
            np.savez_compressed(out/(slug+'-raw.npz'),masks=np.packbits(gm.reshape(len(gm),-1),axis=1),shape=np.array(gm.shape),scores=scores,low_res_logits=logits)
            report['runs'].append({'target':target['id'],'condition':condition,'input_dimensions':list(image.size),'candidate_file_prefix':slug,'seconds_predict_only':time.monotonic()-ts,'candidates':candidates})
            print(slug,flush=True)
report['elapsed_seconds']=time.monotonic()-t0
(out/'report.json').write_text(json.dumps(report,indent=2))
print('POINT_LOOP_COMPLETE',out,flush=True)
