"""RunPod-only SAM3 interactive point-refinement diagnostic.

Six post-hoc review anchors are oracle prompts, not evaluation labels.  Each
target gets one positive point and one existing same-ROI anchor as a negative
point; raw three-mask ambiguity outputs are retained without claiming an
automatic leaf-instance result.
"""
import hashlib
import json
import os
import platform
import time
from pathlib import Path

if platform.system() != "Linux" or not os.environ.get("RUNPOD_POD_ID"):
    raise SystemExit("Remote RunPod execution only; do not import ML/image libraries on Mac")

import numpy as np
from PIL import Image
import torch
from sam3.model_builder import build_sam3_image_model
from sam3.model.sam3_image_processor import Sam3Processor

ROOT = Path("/workspace/sam3-comparison")
INPUT = Path(os.environ.get("ALT_INPUT", ROOT / "input.png"))
OUT = Path(os.environ.get("POINT_OUT", ROOT / "point-refinement"))
REVIEW = Path(os.environ.get(
    "ALT_REVIEW",
    "/workspace/AstraFactory/research/hemp-defoliation/organ-review-v1/review.json",
))
OUT.mkdir(parents=True, exist_ok=True)


def proxies(rgb):
    a = rgb.astype(float)
    h, w = a.shape[:2]
    roi = np.zeros((h, w), bool)
    roi[3:int(h * .94), 3:w - 3] = True
    bg = np.median(np.concatenate([a[5:30, 5:40].reshape(-1, 3), a[5:30, -40:-5].reshape(-1, 3)]), axis=0)
    g, r, b = a[:, :, 1], a[:, :, 0], a[:, :, 2]
    core = roi & (g - bg[1] > 30) & (g - r > 12) & (g - b > 20)
    fg = roi & (g - bg[1] > 12) & (g - r > 4) & (g - b > 8)
    background = roi & ~((g - bg[1] > 6) & (g - r > 1) & (g - b > 3))
    return roi, core, fg, background


def diagnostic(mask, roi, core, fg, background, review):
    # Proxy numbers are only a shared leakage/coverage diagnostic, never labels.
    mask = mask & roi
    hit, pred = int((mask & fg).sum()), int(mask.sum())
    per_region = []
    for region in review["regions"]:
        x0, y0, x1, y1 = region["review_roi_xyxy"]
        per_region.append({"id": region["id"], "roi_predicted_pixels": int(mask[y0:y1, x0:x1].sum())})
    return {
        "foreground_coverage": hit / max(1, int(fg.sum())),
        "core_coverage": int((mask & core).sum()) / max(1, int(core.sum())),
        "proxy_precision": hit / max(1, pred),
        "proxy_iou": hit / max(1, int((mask | fg).sum())),
        "definite_background_pixels": int((mask & background).sum()),
        "predicted_pixels": pred,
        "review_region_pixels": per_region,
    }


def visual(rgb, mask, positive, negative, path):
    z = (rgb.astype(float) * .35).astype("uint8")
    z[mask] = [65, 205, 140]
    for x, y, color in ((positive[0], positive[1], [255, 230, 60]), (negative[0], negative[1], [235, 70, 85])):
        z[max(0, y - 2):y + 3, max(0, x - 2):x + 3] = color
    Image.fromarray(z).save(path)


image = Image.open(INPUT).convert("RGB")
rgb = np.asarray(image)
h, w = rgb.shape[:2]
review = json.loads(REVIEW.read_text())
if review["image_size"] != [w, h]:
    raise SystemExit("review coordinates do not match frozen input dimensions")
roi, core, fg, background = proxies(rgb)
image.save(OUT / "input.png")

if not torch.cuda.is_available():
    raise SystemExit("CUDA required")
torch.manual_seed(71)
model = build_sam3_image_model(
    checkpoint_path=str(ROOT / "sam3.pt"), load_from_HF=False, device="cuda",
    # Official builder defaults this to False. Enable the SAM1-style predictor
    # explicitly for positive/negative click refinement.
    enable_inst_interactivity=True,
)
if model.inst_interactive_predictor is None:
    raise SystemExit("interactive predictor was not constructed; check enable_inst_interactivity")
processor = Sam3Processor(model, device="cuda")
start = time.monotonic()
with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
    inference_state = processor.set_image(image)

runs = []
for region in review["regions"]:
    anchors = region["anchors"]
    if len(anchors) < 2:
        continue
    for target, other in ((anchors[0], anchors[1]), (anchors[1], anchors[0])):
        positive = target["xy"]
        negative = other["xy"]
        # `multimask_output=True` is the official ambiguous-click mode.  Do not
        # collapse candidates based on proxy metrics; retain all predicted-IoU modes.
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            masks, predicted_ious, low_res_logits = model.predict_inst(
                inference_state,
                point_coords=np.asarray([positive, negative], dtype=np.float32),
                point_labels=np.asarray([1, 0], dtype=np.int32),
                multimask_output=True,
            )
        if torch.is_tensor(masks): masks=masks.detach().cpu().numpy()
        if torch.is_tensor(predicted_ious): predicted_ious=predicted_ious.detach().float().cpu().numpy()
        if torch.is_tensor(low_res_logits): low_res_logits=low_res_logits.detach().float().cpu().numpy()
        masks = masks.astype(bool)
        slug = target["id"]
        np.savez_compressed(OUT / (slug + "-raw-multimask.npz"),
                            masks=np.packbits(masks.reshape(len(masks), h * w), axis=1),
                            shape=np.array(masks.shape), predicted_ious=predicted_ious,
                            low_res_logits=low_res_logits,
                            positive_xy=np.array(positive), negative_xy=np.array(negative))
        candidates = []
        for index, mask in enumerate(masks):
            visual(rgb, mask, positive, negative, OUT / f"{slug}-candidate-{index}.png")
            candidates.append({
                "candidate_index": index,
                "predicted_iou": float(predicted_ious[index]),
                "diagnostic": diagnostic(mask, roi, core, fg, background, review),
            })
        runs.append({
            "region": region["id"], "target_anchor": target["id"],
            "positive_xy": positive, "negative_anchor": other["id"], "negative_xy": negative,
            "candidates": candidates,
        })

report = {
    "method": "SAM3 interactive image predictor, one positive and one negative point, raw multimask outputs",
    "comparison_type": "same checkpoint, targeted oracle-assisted refinement; not automatic instance discovery and not an independent model comparison",
    "input_sha256": hashlib.sha256(INPUT.read_bytes()).hexdigest(), "image_size": [w, h],
    "device": torch.cuda.get_device_name(0), "pod_id": os.environ["RUNPOD_POD_ID"],
    "elapsed_seconds": time.monotonic() - start,
    "prompt_notice": "Points are post-hoc manually reviewed anchors. The negative point is another reviewed point in the same ROI. This tests an interactive labeling technique, not a held-out benchmark or autonomous prompt generation.",
    "evaluation_notice": "Raw multimask candidates are retained. Predicted IoU is a model confidence output, not observed IoU. Color-proxy and review-ROI values are diagnostics only; no boundary/organ accuracy is claimed.",
    "runs": runs,
}
(OUT / "result.json").write_text(json.dumps(report, indent=2))
print(json.dumps({"out": str(OUT), "anchor_runs": len(runs), "elapsed_seconds": report["elapsed_seconds"]}))
print("POINT_REFINEMENT_COMPLETE")
