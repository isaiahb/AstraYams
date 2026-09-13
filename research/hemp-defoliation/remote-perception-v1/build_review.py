"""Lightweight HTML packaging only. No image processing or model imports."""
from pathlib import Path
import json,html

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'runs/hemp-perception-pilot-v1'
r=json.loads((OUT/'results/summary.json').read_text())
panels=[]
for row in r['images']:
    name=row['image'];metrics=''
    for level,settings in row.get('visible_organ_audit',{}).items():
        baseline=settings['standard'];test=settings['recall_filtered']
        metrics+=f'<p>{level} coverage against exact scene masks (visible ≥16px; best IoU ≥0.5): default <b>{baseline["organs_with_any_mask_iou_ge05"]}/{baseline["visible_organs_ge16px"]}</b>, recall candidates <b>{test["organs_with_any_mask_iou_ge05"]}/{test["visible_organs_ge16px"]}</b>.</p>'
    if 'synthetic_depth_rank_correlation' in row:
        metrics+=f'<p>Predicted vs exact synthetic depth: rank correlation <b>{row["synthetic_depth_rank_correlation"]:.3f}</b>. This does not establish real-photo depth accuracy.</p>'
    images=[('Input',f'sam2/{name}/input.png'),('Default SAM2',f'sam2/{name}/overlay-0.png'),('Recall foliage candidates',f'sam2-recall/{name}/foliage-candidates.png'),('DA3 relative depth',f'depth/{name}/depth-preview.png')]
    if name!='reference':images.append(('Exact visible leaf IDs',f'synthetic-audit/{name}/leaf-ids.png'))
    cells=''.join(f'<figure><figcaption>{title}</figcaption><a href="results/{path}"><img src="results/{path}" alt="{title}: {name}"></a></figure>' for title,path in images)
    panels.append(f'<section><h2>{html.escape(name)}</h2><p>Permissive pass: {row["raw_proposals"]} raw region proposals → {row["foliage_candidates"]} heuristic foliage candidates. <strong>Neither is a verified leaf count.</strong></p><div class="row">{cells}</div>{metrics}</section>')
page='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Remote plant perception · actual results</title>
<style>body{margin:0;background:#edf0e5;color:#243a2e;font:16px/1.5 system-ui}main{max-width:1500px;margin:auto;padding:28px}h1{font-size:34px;letter-spacing:-.03em}section{padding:22px;background:#fafbf5;border:1px solid #b8c6b0;border-radius:16px;margin:22px 0}.row{display:flex;gap:12px;overflow:auto}figure{margin:0;flex:1;min-width:190px}img{width:100%;object-fit:contain;aspect-ratio:381/444;background:#10160e}figcaption{font-size:13px;margin:8px 0}a{color:#24633f}.notice{padding:16px;border-left:4px solid #a3833c;background:#f7edd6}p{max-width:1100px}</style>
<main><small>ASTRAFACTORY · REMOTE GPU EVIDENCE</small><h1>Can vision models measure our plant's missing detail?</h1>
<p>Actual SAM2.1-large and Depth Anything3-small results from a RunPod A40. No model inference ran on the Mac.</p>
<div class="notice"><b>Result: useful proposals, not an automatic organ census.</b> Default masks missed most fine foliage. A denser, lower-threshold pass recovered more regions but also background. Its shown foliage filter is a post-hoc green/size heuristic, not flower classification or ground truth. Both settings and raw masks are retained.</div>
<p>Exact synthetic masks come from ray casting the same exported mesh. They reveal segmentation failure separately from model omissions. Photo masks cannot see hidden leaves. Depth previews have individual contrast normalization and must not be compared as metric distances.</p>'''+''.join(panels)+'''<section><h2>How this changes the next iteration</h2><p>Use reviewed local masks to constrain visible organ shape and occupancy. Audit clear leaves and overlapping clusters separately. Acquire a higher-resolution source or existing SAM3 access before promising every leaf, flower or bud. Do not fit mechanics to these predicted depths.</p><p><a href="results/summary.json">Metrics and filter settings</a> · <a href="results/sam2/report.json">Default run</a> · <a href="results/sam2-recall/report.json">Recall run</a> · <a href="results/depth/report.json">Depth run</a> · <a href="results/comparison.png">Full comparison image</a></p></section></main>'''
(OUT/'index.html').write_text(page)
print(OUT/'index.html')
