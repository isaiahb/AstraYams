"""Remote diagnostic filtering/audit. Does not create semantic ground truth."""
from worker import require_remote
require_remote()
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.stats import spearmanr

root=Path('/workspace/plant-pilot');rows=[];panels=[]
for name in ['reference','broad-render','narrow-render']:
    p=root/'results/sam2-recall'/name;r=json.loads((p/'predictions.json').read_text())
    rgb=np.array(Image.open(p/'input.png'));raw=np.load(p/'masks-0.npz')['masks']
    f=rgb.astype(float);green=(f[:,:,1]>42)&(f[:,:,1]>f[:,:,0]*1.06)&(f[:,:,1]>f[:,:,2]*1.18)
    selection=[];rejected=[]
    for i,m in enumerate(raw):
        frac=float((m&green).sum()/max(1,m.sum()))
        keep=frac>=.6 and 16<=m.sum()<=.12*m.size
        (selection if keep else rejected).append(i)
    chosen=raw[selection];union=np.any(chosen,axis=0) if len(chosen) else np.zeros(green.shape,bool)
    overlay=rgb.astype(float).copy();rng=np.random.default_rng(71)
    for m in chosen:overlay[m]=overlay[m]*.5+rng.integers(35,250,3)*.5
    Image.fromarray(overlay.astype('uint8')).save(p/'foliage-candidates.png')
    row={'image':name,'raw_proposals':len(raw),'foliage_candidates':len(selection),
        'selected_proposals':selection,'rejected_proposals':rejected,
        'verified_leaf_count':None,'candidate_union_fraction':float(union.mean()),
        'filter':'Post-hoc diagnostic only: >=60% green pixels, 16px minimum, <=12% image area. Not flower segmentation or calibrated organ detection.'}
    if name!='reference':
        audit=root/'results/synthetic-audit'/name;row['visible_organ_audit']={}
        for level in ['leaf','leaflet']:
            ids=np.load(audit/(level+'-ids.npz'))['ids'];organ_ids=[x for x in np.unique(ids) if x>=0 and (ids==x).sum()>=16]
            stats={}
            for tag,proposals in [('standard',np.load(root/f'results/sam2/{name}/masks-0.npz')['masks']),('recall_raw',raw),('recall_filtered',chosen)]:
                scores=[]
                for i in organ_ids:
                    gt=ids==i
                    ious=(proposals&gt).sum(axis=(1,2))/np.maximum(1,(proposals|gt).sum(axis=(1,2)))
                    scores.append(float(ious.max()) if len(ious) else 0)
                stats[tag]={'visible_organs_ge16px':len(scores),'organs_with_any_mask_iou_ge05':sum(x>=.5 for x in scores),'median_best_iou':float(np.median(scores))}
            row['visible_organ_audit'][level]=stats
        gt=np.load(audit/'visible-parts.npz');depth=np.load(root/f'results/depth/{name}/depth.npz')['depth'][0]
        resized=np.array(Image.fromarray(depth).resize((rgb.shape[1],rgb.shape[0]),Image.Resampling.BILINEAR))
        valid=(gt['part_ids']>=0)&np.isfinite(gt['depth'])&np.isfinite(resized)
        row['synthetic_depth_rank_correlation']=float(spearmanr(resized[valid],gt['depth'][valid]).statistic)
        row['depth_notice']='Spearman correlation only on visible synthetic geometry; resized prediction. No metric accuracy or real-photo validation.'
    rows.append(row)
    images=[Image.fromarray(rgb),Image.open(root/f'results/sam2/{name}/overlay-0.png'),Image.fromarray(overlay.astype('uint8')),Image.open(root/f'results/depth/{name}/depth-preview.png').resize((rgb.shape[1],rgb.shape[0]))]
    titles=[name,'Default SAM2','Recall: foliage candidates','DA3 relative depth']
    rowim=Image.new('RGB',(rgb.shape[1]*4,rgb.shape[0]+45),'#eff1e8');draw=ImageDraw.Draw(rowim)
    for i,(im,title) in enumerate(zip(images,titles)):
        rowim.paste(im,(i*rgb.shape[1],45));draw.text((i*rgb.shape[1]+9,12),title,fill='#20382b')
    panels.append(rowim)
report={'status':'pilot finished; no reliable automatic organ census established','images':rows}
(root/'results/summary.json').write_text(json.dumps(report,indent=2))
board=Image.new('RGB',(panels[0].width,sum(x.height for x in panels)))
y=0
for im in panels:board.paste(im,(0,y));y+=im.height
board.save(root/'results/comparison.png')
print(json.dumps(report,indent=2))
