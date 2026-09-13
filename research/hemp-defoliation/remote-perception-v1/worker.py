"""Remote CUDA-only perception pilot. Never imports ML packages on macOS.

Run each backend in its own process to release GPU memory between models.
Outputs are predictions, not organ ground truth or physical measurements.
"""
import argparse
import hashlib
import json
import os
import platform
import time
from pathlib import Path


def require_remote():
    if platform.system() != 'Linux' or not os.environ.get('RUNPOD_POD_ID'):
        raise SystemExit('REFUSED: inference is restricted to a Linux RunPod worker. No model imported.')


def main():
    require_remote()  # Must remain before torch/numpy/PIL/model imports.
    parser=argparse.ArgumentParser()
    parser.add_argument('--backend',choices=['sam2','sam3','depth'],required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    import numpy as np
    import torch
    from PIL import Image
    if not torch.cuda.is_available():
        raise SystemExit('REFUSED: CUDA required; no CPU/MPS fallback.')
    torch.set_num_threads(2)
    torch.manual_seed(71)
    config=json.loads(args.manifest.read_text())
    if not 1<=len(config['images'])<=6:
        raise SystemExit('Pilot limited to 1–6 images.')
    args.out.mkdir(parents=True,exist_ok=True)
    if args.backend=='sam2':
        from sam2.build_sam import build_sam2_hf
        from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
        model_id='facebook/sam2.1-hiera-large'
        model=build_sam2_hf(model_id,device='cuda')
        engine=SAM2AutomaticMaskGenerator(model,points_per_side=32,points_per_batch=16,
            crop_n_layers=1,pred_iou_thresh=.8,stability_score_thresh=.95)
    elif args.backend=='sam3':
        from sam3.model_builder import build_sam3_image_model
        from sam3.model.sam3_image_processor import Sam3Processor
        model_id='facebook/sam3'
        model=build_sam3_image_model()
        engine=Sam3Processor(model,device='cuda',confidence_threshold=.5)
    else:
        from depth_anything_3.api import DepthAnything3
        model_id='depth-anything/DA3-SMALL'
        model=DepthAnything3.from_pretrained(model_id).to('cuda').eval()
    reports=[]
    for item in config['images']:
        start=time.monotonic();p=args.manifest.parent/item['file']
        actual_hash=hashlib.sha256(p.read_bytes()).hexdigest()
        if actual_hash!=item['sha256']:raise ValueError('Input checksum mismatch: '+item['id'])
        im=Image.open(p).convert('RGB')
        # Equal native camera resolution on both domains; do not invent detail.
        size=tuple(config['comparison_size']);im=im.resize(size,Image.Resampling.LANCZOS)
        rgb=np.array(im);dest=args.out/item['id'];dest.mkdir(exist_ok=True)
        im.save(dest/'input.png');record={'id':item['id'],'source_sha256':actual_hash,'groups':[]}
        with torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):
            if args.backend=='depth':
                # Never feed different specimens as a multi-view reconstruction.
                pred=model.inference([str(dest/'input.png')])
                np.savez_compressed(dest/'depth.npz',depth=pred.depth,confidence=pred.conf,
                    intrinsics=pred.intrinsics,extrinsics=pred.extrinsics)
                z=pred.depth[0];valid=np.isfinite(z)
                low,high=np.percentile(z[valid],[2,98])
                preview=np.nan_to_num(np.clip((z-low)/max(high-low,1e-8),0,1))*255
                Image.fromarray(preview.astype('uint8')).save(dest/'depth-preview.png')
                record['depth_notice']='Relative predicted depth, not measured meters. Preview independently normalized; compare raw arrays only with documented alignment.'
            else:
                prompts=config['prompts'] if args.backend=='sam3' else ['unlabeled proposals']
                for group_i,prompt in enumerate(prompts):
                    if args.backend=='sam2':
                        proposals=engine.generate(rgb)
                        masks=np.stack([x['segmentation'] for x in proposals]) if proposals else np.zeros((0,size[1],size[0]),bool)
                        metadata=[{k:v for k,v in x.items() if k!='segmentation'} for x in proposals]
                    else:
                        state=engine.set_image(im)
                        result=engine.set_text_prompt(state=state,prompt=prompt)
                        masks=result['masks'].detach().cpu().numpy().reshape(-1,size[1],size[0])>.5
                        scores=result['scores'].detach().cpu().numpy().reshape(-1)
                        metadata=[{'score':float(x)} for x in scores]
                        del state,result
                    np.savez_compressed(dest/f'masks-{group_i}.npz',masks=masks)
                    union=np.any(masks,axis=0) if len(masks) else np.zeros(rgb.shape[:2],bool)
                    overlay=rgb.astype(float).copy();rng=np.random.default_rng(71)
                    # Only the preview composites overlaps; raw masks retain all proposals.
                    for mask in masks:
                        overlay[mask]=.5*overlay[mask]+.5*rng.integers(45,240,size=3)
                    Image.fromarray(overlay.astype('uint8')).save(dest/f'overlay-{group_i}.png')
                    Image.fromarray(union).save(dest/f'union-{group_i}.png')
                    record['groups'].append({'prompt':prompt,'proposal_count':len(masks),
                        'organ_count_verified':False,'union_fraction':float(union.mean()),
                        'vertical_occupancy':[float(x.mean()) for x in np.array_split(union,12)],
                        'masks':metadata})
        record['seconds']=time.monotonic()-start
        (dest/'predictions.json').write_text(json.dumps(record,indent=2))
        reports.append(record)
        print(item['id'],args.backend,'complete',round(record['seconds'],2),flush=True)
    report={'backend':args.backend,'model':model_id,'torch':torch.__version__,
        'gpu':torch.cuda.get_device_name(),'status':'predictions awaiting manual audit',
        'input_manifest':config,'results':reports}
    (args.out/'report.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
