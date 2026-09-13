"""RunPod-only SAM3 visual-region-exemplar diagnostic against the frozen plant image.

This is a prompting-method comparison, not an independent model comparison and
not an organ-label accuracy evaluation.  The three boxes and six points come
from the post-hoc provisional review and therefore cannot be treated as held out.
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
OUT = Path(os.environ.get("ALT_OUT", ROOT / "visual-exemplar"))
REVIEW = Path(os.environ.get(
    "ALT_REVIEW",
    "/workspace/AstraFactory/research/hemp-defoliation/organ-review-v1/review.json",
))
OUT.mkdir(parents=True, exist_ok=True)


def foreground_proxies(rgb):
    """Frozen proxy used by sam3-grid-search-v1; it is explicitly not truth."""
    a = rgb.astype(float)
    h, w = a.shape[:2]
    roi = np.zeros((h, w), bool)
    roi[3 : int(h * 0.94), 3 : w - 3] = True
    bg = np.median(np.concatenate([
        a[5:30, 5:40].reshape(-1, 3), a[5:30, -40:-5].reshape(-1, 3)
    ]), axis=0)
    g, r, b = a[:, :, 1], a[:, :, 0], a[:, :, 2]
    core = roi & (g - bg[1] > 30) & (g - r > 12) & (g - b > 20)
    fg = roi & (g - bg[1] > 12) & (g - r > 4) & (g - b > 8)
    permissive = roi & (g - bg[1] > 6) & (g - r > 1) & (g - b > 3)
    return roi, core, fg, permissive, roi & ~permissive, bg


def metrics(score, threshold, roi, core, fg, background):
    mask = (score >= threshold) & roi
    hit = int((mask & fg).sum())
    pred = int(mask.sum())
    return {
        "threshold": threshold,
        "foreground_coverage": hit / max(1, int(fg.sum())),
        "core_coverage": int((mask & core).sum()) / max(1, int(core.sum())),
        "proxy_precision": hit / max(1, pred),
        "proxy_iou": hit / max(1, int((mask | fg).sum())),
        "definite_background_pixels": int((mask & background).sum()),
        "background_fraction_of_prediction": int((mask & background).sum()) / max(1, pred),
        "predicted_pixels": pred,
    }


def review_diagnostic(score, threshold, review):
    """Point/rectangle diagnostics only; neither is a mask or an accuracy score."""
    mask = score >= threshold
    rows = []
    for region in review["regions"]:
        x0, y0, x1, y1 = region["review_roi_xyxy"]
        anchors = []
        for anchor in region["anchors"]:
            x, y = anchor["xy"]
            anchors.append({"id": anchor["id"], "covered": bool(mask[y, x])})
        rows.append({
            "id": region["id"],
            "roi_predicted_pixels": int(mask[y0:y1, x0:x1].sum()),
            "anchors": anchors,
        })
    return rows


def coverage_visual(rgb, score, fg, background, threshold, path):
    mask = score >= threshold
    z = (rgb.astype(float) * 0.28).astype("uint8")
    z[fg & ~mask] = [240, 65, 85]
    z[fg & mask] = [60, 205, 140]
    z[background & mask] = [70, 145, 255]
    Image.fromarray(z).save(path)


def prompt_box(region, width, height):
    x, y, bw, bh = region["crop_xywh"]
    return [(x + bw / 2) / width, (y + bh / 2) / height, bw / width, bh / height]


def load_optional_baseline(path, roi, core, fg, background, review):
    if not path:
        return None
    candidate = Path(path)
    if not candidate.exists():
        return {"requested": str(candidate), "available": False}
    score = np.load(candidate)["all"]
    if score.shape != roi.shape:
        return {"requested": str(candidate), "available": False, "reason": "shape mismatch"}
    return {
        "requested": str(candidate), "available": True,
        "metrics": [metrics(score, t, roi, core, fg, background) for t in (0.5, 0.25, 0.1)],
        "review_diagnostic": [
            {"threshold": t, "regions": review_diagnostic(score, t, review)}
            for t in (0.5, 0.25, 0.1)
        ],
    }


image = Image.open(INPUT).convert("RGB")
rgb = np.asarray(image)
h, w = rgb.shape[:2]
review = json.loads(REVIEW.read_text())
if review["image_size"] != [w, h]:
    raise SystemExit("review coordinates do not match frozen input dimensions")
roi, core, fg, permissive, background, bg = foreground_proxies(rgb)
image.save(OUT / "input.png")
np.savez_compressed(OUT / "foreground-proxies.npz", roi=roi, core=core, foreground=fg,
                    permissive=permissive, background=background)

torch.manual_seed(71)
if not torch.cuda.is_available():
    raise SystemExit("CUDA required")
engine = Sam3Processor(
    build_sam3_image_model(checkpoint_path=str(ROOT / "sam3.pt"), load_from_HF=False, device="cuda"),
    device="cuda", confidence_threshold=0.1,
)
method_rows = []
start = time.monotonic()
for region in review["regions"]:
    # Each review rectangle is one independent visual exemplar; never union them.
    # This keeps a seed's matched instances inspectable and avoids score mixing.
    box = prompt_box(region, w, h)
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        state = engine.set_image(image)
        state = engine.add_geometric_prompt(box=box, label=True, state=state)
    masks = state["masks"].detach().cpu().numpy().reshape(-1, h, w).astype(bool)
    scores = state["scores"].detach().float().cpu().numpy().reshape(-1)
    scoremap = np.zeros((h, w), np.float32)
    for mask, score in zip(masks, scores):
        np.maximum(scoremap, mask * score, out=scoremap)
    slug = region["id"]
    np.savez_compressed(OUT / (slug + "-proposals.npz"),
                        masks=np.packbits(masks.reshape(len(masks), h * w), axis=1),
                        shape=np.array(masks.shape), scores=scores, box=np.array(box))
    np.savez_compressed(OUT / (slug + "-scores.npz"), all=scoremap)
    for threshold in (0.5, 0.25, 0.1):
        coverage_visual(rgb, scoremap, fg, background, threshold,
                        OUT / f"{slug}-coverage-{threshold}.png")
    method_rows.append({
        "seed_region": slug,
        "seed_box_cxcywh_normalized": box,
        "proposal_count_score_ge_0_1": int(len(scores)),
        "metrics": [metrics(scoremap, t, roi, core, fg, background) for t in (0.5, 0.25, 0.1)],
        "review_diagnostic": [
            {"threshold": t, "regions": review_diagnostic(scoremap, t, review)}
            for t in (0.5, 0.25, 0.1)
        ],
    })

report = {
    "method": "SAM3 full-image visual-region-exemplar box prompting",
    "comparison_type": "same SAM3 checkpoint, different prompt/inference method; not an independent model comparison",
    "input_sha256": hashlib.sha256(INPUT.read_bytes()).hexdigest(),
    "image_size": [w, h],
    "device": torch.cuda.get_device_name(0),
    "pod_id": os.environ["RUNPOD_POD_ID"],
    "elapsed_seconds": time.monotonic() - start,
    "fixed_evaluation": "same foreground proxy/ROI/thresholds as sam3-grid-search-v1; proxy is not ground truth",
    "review_notice": "The three seeds are broad, post-hoc review rectangles that contain multiple blades, and may include stem/background; they are not tight single-organ exemplars. The six point anchors are also not held out. ROI pixels and point hits are diagnostics only, not boundary or organ accuracy.",
    "background_rgb": bg.tolist(),
    "runs": method_rows,
    "optional_baseline": load_optional_baseline(os.environ.get("BASELINE_SCORES"), roi, core, fg, background, review),
}
(OUT / "result.json").write_text(json.dumps(report, indent=2))
print(json.dumps({"out": str(OUT), "runs": len(method_rows), "elapsed_seconds": report["elapsed_seconds"]}))
print("VISUAL_EXEMPLAR_COMPLETE")
