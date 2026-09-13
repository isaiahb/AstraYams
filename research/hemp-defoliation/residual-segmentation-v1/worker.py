"""Matched-budget residual SAM3 experiment. RunPod CUDA only."""
import os, platform
if platform.system() != "Linux" or not os.environ.get("RUNPOD_POD_ID"):
    raise SystemExit("RunPod CUDA execution only; no local ML or image processing")

import hashlib, json, time
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from sam3.model_builder import build_sam3_image_model
from sam3.model.sam3_image_processor import Sam3Processor

ROOT = Path("/workspace/residual-segmentation")
OUT = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)
START = time.monotonic()
DEADLINE = START + int(os.environ.get("RESIDUAL_SECONDS", "1800"))
THRESHOLD = 0.5

image = Image.open(ROOT / "input.png").convert("RGB")
rgb = np.asarray(image)
h, w = rgb.shape[:2]
proxies = np.load(ROOT / "foreground-proxies.npz")
fg = proxies["foreground"].astype(bool)
core = proxies["core"].astype(bool)
permissive = proxies["permissive"].astype(bool)
roi = proxies["roi"].astype(bool)
background = roi & ~permissive
baseline_scores = np.load(ROOT / "baseline-scores.npz")["all"]
initial = baseline_scores >= THRESHOLD
baseline_tiles = json.loads((ROOT / "baseline-tiles.json").read_text())
boxes = [tuple(x["box"]) for x in baseline_tiles]
assert len(boxes) == 87, len(boxes)
crop_w, crop_h = boxes[0][2] - boxes[0][0], boxes[0][3] - boxes[0][1]

assert torch.cuda.is_available()
torch.set_num_threads(2)
torch.manual_seed(71)
engine = Sam3Processor(build_sam3_image_model(checkpoint_path=str(ROOT / "sam3.pt"), load_from_HF=False, device="cuda"), device="cuda", confidence_threshold=.1)

def residual_boxes(n):
    residual = fg & ~initial
    candidates = []
    # Rank centers by uncovered proxy mass, then spatially suppress exact repeats.
    ys, xs = np.where(residual)
    for y, x in zip(ys[::2], xs[::2]):
        x0 = min(max(0, int(x) - crop_w // 2), w - crop_w)
        y0 = min(max(0, int(y) - crop_h // 2), h - crop_h)
        mass = int(residual[y0:y0+crop_h, x0:x0+crop_w].sum())
        candidates.append((mass, x0, y0))
    candidates.sort(reverse=True)
    chosen = []
    min_d2 = (min(crop_w, crop_h) * .18) ** 2
    for mass, x0, y0 in candidates:
        cx, cy = x0 + crop_w/2, y0 + crop_h/2
        if all((cx-(a+crop_w/2))**2 + (cy-(b+crop_h/2))**2 >= min_d2 for a,b in chosen):
            chosen.append((x0,y0))
            if len(chosen) == n: break
    if len(chosen) < n:
        for _,x0,y0 in candidates:
            if (x0,y0) not in chosen:
                chosen.append((x0,y0))
                if len(chosen) == n: break
    assert len(chosen) == n
    return [(x0,y0,x0+crop_w,y0+crop_h) for x0,y0 in chosen]

def metrics(mask):
    mask = mask & roi
    new = mask & ~initial
    final = (initial | mask) & roi
    residual_fg = fg & ~initial
    pred = int(final.sum())
    return {
        "final_foreground_coverage": float((final & fg).sum() / max(1, fg.sum())),
        "final_proxy_iou": float((final & fg).sum() / max(1, (final | fg).sum())),
        "new_residual_foreground_pixels": int((new & fg).sum()),
        "residual_foreground_coverage": float((new & fg).sum() / max(1, residual_fg.sum())),
        "new_definite_background_pixels": int((new & background).sum()),
        "final_definite_background_pixels": int((final & background).sum()),
        "background_fraction_of_final_prediction": float((final & background).sum() / max(1, pred)),
        "predicted_pixels": pred,
    }

def run_arm(name, source, arm_boxes):
    dest = OUT / name
    dest.mkdir(exist_ok=True)
    unions = {t:np.zeros((h,w),bool) for t in [.5,.25,.1]}
    proposals = []
    trace = []
    t0 = time.monotonic()
    for ti, (x0,y0,x1,y1) in enumerate(arm_boxes):
        if time.monotonic() > DEADLINE: raise TimeoutError(name)
        crop = source.crop((x0,y0,x1,y1))
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            state = engine.set_image(crop)
            res = engine.set_text_prompt(state=state, prompt="leaf")
            masks = res["masks"].detach().cpu().numpy().reshape(-1,crop.height,crop.width) > .5
            scores = res["scores"].detach().float().cpu().numpy().reshape(-1)
        edge = []
        for pi,(m,s) in enumerate(zip(masks,scores)):
            e = bool((x0>0 and m[:,:2].any()) or (x1<w and m[:,-2:].any()) or (y0>0 and m[:2].any()) or (y1<h and m[-2:].any()))
            edge.append(e)
            if m.any():
                full = np.zeros((h,w),bool); full[y0:y1,x0:x1] = m
                for t in unions:
                    if s>=t: unions[t] |= full
                if s >= THRESHOLD: proposals.append((ti,pi,float(s),e,full))
        packed=np.packbits(masks.reshape(len(masks),-1),axis=1) if len(masks) else np.empty((0,0),np.uint8)
        np.savez_compressed(dest/f"tile-{ti}.npz", masks=packed, shape=np.array(masks.shape), scores=scores, box=np.array([x0,y0,x1,y1]), edge=np.array(edge))
        trace.append({"tile":ti,"box":[x0,y0,x1,y1],"proposals":len(scores),"accepted":int((scores>=THRESHOLD).sum())})
    # Duplicate proxy: accepted cross-crop proposal pairs with IoU >= .5.
    duplicate_pairs = 0
    for i, a in enumerate(proposals):
        for b in proposals[i+1:]:
            if a[0] == b[0]: continue
            inter = int((a[4] & b[4]).sum())
            if inter and inter / int((a[4] | b[4]).sum()) >= .5: duplicate_pairs += 1
    union=unions[THRESHOLD]
    np.savez_compressed(dest/"union.npz", **{"threshold-0.5":unions[.5],"threshold-0.25":unions[.25],"threshold-0.1":unions[.1]})
    (dest/"tiles.json").write_text(json.dumps(trace,indent=2))
    overlay = (rgb*.30).astype(np.uint8)
    overlay[fg & ~(initial|union)] = [245,55,75]
    overlay[initial & fg] = [55,145,240]
    overlay[(union & ~initial) & fg] = [55,220,130]
    overlay[(union & ~initial) & background] = [235,160,45]
    Image.fromarray(overlay).save(dest/"overlay.png")
    instances = (rgb*.24).astype(np.uint8)
    palette=np.array([[247,93,89],[80,214,190],[255,190,75],[126,165,255],[207,124,255],[120,220,90]],np.uint8)
    for k,p in enumerate(proposals): instances[p[4]]=palette[k%len(palette)]
    Image.fromarray(instances).save(dest/"instances.png")
    return {"arm":name,"inference_calls":len(arm_boxes),"accepted_proposals":len(proposals),"edge_accepted_proposals":sum(p[3] for p in proposals),"cross_crop_duplicate_pairs_iou_ge_0_5":duplicate_pairs,"metrics":metrics(union),"lower_confidence_diagnostics":[{"threshold":t,**metrics(unions[t])} for t in [.25,.1]],"seconds":time.monotonic()-t0}

black = rgb.copy(); black[initial] = 0
black_image = Image.fromarray(black)
black_image.save(OUT/"black-input.png")
directed = residual_boxes(len(boxes))
(OUT/"residual-boxes.json").write_text(json.dumps([list(b) for b in directed],indent=2))
rows = [run_arm("unchanged-repeat", image, boxes), run_arm("black-fill", black_image, boxes), run_arm("original-context-residual", image, directed)]
report = {
    "input_sha256": hashlib.sha256((ROOT/"input.png").read_bytes()).hexdigest(),
    "input_label":"preharvest pot-not-visible; not fully suitable target evidence",
    "detached_shoot_images":"rejected; not used",
    "threshold":THRESHOLD,"prompt":"leaf","matched_budget_calls_per_arm":len(boxes),
    "crop_size":[crop_w,crop_h],"initial_baseline":metrics(initial),"arms":rows,
    "proxy_not_ground_truth":True,"device":torch.cuda.get_device_name(0),"pod_id":os.environ["RUNPOD_POD_ID"],
    "elapsed_seconds":time.monotonic()-START
}
(OUT/"report.json").write_text(json.dumps(report,indent=2))

# Fixed calibration ROIs, selected before this experiment; not held-out GT.
review=json.loads((ROOT/"review.json").read_text())
base_instances=(rgb*.24).astype(np.uint8); palette=np.array([[247,93,89],[80,214,190],[255,190,75],[126,165,255],[207,124,255],[120,220,90]],np.uint8); k=0
for f in sorted((ROOT/"baseline-raw").glob("tile-*.npz")):
 z=np.load(f); shape=tuple(z['shape']); masks=np.unpackbits(z['masks'],axis=1,count=shape[1]*shape[2]).reshape(shape).astype(bool); scores=z['scores']; x0,y0,x1,y1=map(int,z['box'])
 for m,s in zip(masks,scores):
  if s>=THRESHOLD and m.any(): base_instances[y0:y1,x0:x1][m]=palette[k%len(palette)]; k+=1
base_union=(rgb*.30).astype(np.uint8); base_union[fg&~initial]=[245,55,75]; base_union[initial&fg]=[55,145,240]; base_union[initial&background]=[235,160,45]
panels=[("original",rgb),("baseline-union",base_union),("baseline-instances",base_instances)]
for name in ["unchanged-repeat","black-fill","original-context-residual"]:
 panels += [(name+"-union",np.asarray(Image.open(OUT/name/"overlay.png"))),(name+"-instances",np.asarray(Image.open(OUT/name/"instances.png")))]
close=OUT/"closeups"; close.mkdir(exist_ok=True)
for region in review["regions"]:
 x0,y0,x1,y1=region["review_roi_xyxy"]; crops=[]
 for label,arr in panels:
  crop=Image.fromarray(arr[y0:y1,x0:x1]).resize(((x1-x0)*5,(y1-y0)*5),Image.Resampling.NEAREST); crop.save(close/f"{region['id']}--{label}.png")
print(json.dumps(report),flush=True)
