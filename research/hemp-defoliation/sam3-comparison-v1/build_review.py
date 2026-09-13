"""Static review packaging only; safe to run on Mac, no ML or rendering."""
from pathlib import Path
import json,html
root=Path(__file__).resolve().parents[3];out=root/'runs/hemp-sam3-comparison-v1'
s=json.loads((out/'results/summary.json').read_text());panels=[]
for row in s['image_results']:
 name=row['image'];cells=[]
 for title,url in [('Input',f'results/sam3/{name}/input.png'),('SAM2 recall (heuristic filter)',f'../hemp-perception-pilot-v1/results/sam2-recall/{name}/foliage-candidates.png')]+[(f'SAM3: {g["prompt"]}',f'results/sam3/{name}/overlay-{i}.png') for i,g in enumerate(row['groups'])]:
  cells.append(f'<figure><figcaption>{html.escape(title)}</figcaption><a href="{url}"><img src="{url}" alt="{html.escape(title)} / {name}"></a></figure>')
 table=''
 for level,methods in row.get('audit',{}).items():
  table+=f'<h3>{level} coverage against known geometry</h3><table><tr><th>Pipeline</th><th>Matched / visible</th><th>Median best overlap</th></tr>'
  for method,stats in methods.items():
   table+=f'<tr><td>{method}</td><td>{stats["organs_with_any_mask_iou_ge05"]} / {stats["visible_organs_ge16px"]}</td><td>{stats["median_best_iou"]:.3f}</td></tr>'
  table+='</table>'
 counts=' · '.join(f'{html.escape(g["prompt"])}: {g["proposals"]} proposals' for g in row['groups'])
 panels.append(f'<section><h2>{name}</h2><p>{counts}. These are predictions, not verified organ counts.</p><div class="images">'+''.join(cells)+'</div>'+table+'</section>')
diagnostics=[]
for folder in ['prompt-probe','concept-probe']:
 path=out/'results'/folder/'report.json'
 if not path.exists():continue
 rows=json.loads(path.read_text())['results'];tiles=[]
 for r in rows:
  if not r['name'].startswith('reference'):continue
  url='results/'+folder+'/'+r['name']+'/overlay.png'
  label=r['name'].replace('reference-','')+' — '+str(r['proposals'])+' candidates'
  tiles.append(f'<figure><figcaption>{html.escape(label)}</figcaption><a href="{url}"><img src="{url}" alt="{html.escape(label)}"></a></figure>')
 diagnostics.append('<section><h2>Reference: '+folder+'</h2><p>Exploratory only. Threshold 0.5 unless labeled low-confidence (0.1). White rectangle marks the manual example. Broad masks can include gaps and whole plant regions.</p><div class="images">'+''.join(tiles)+'</div></section>')
panels.extend(diagnostics)
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SAM3 · plant segmentation comparison</title><style>body{background:#edf0e5;color:#243a2e;font:16px/1.5 system-ui;margin:0}main{padding:30px;max-width:1600px;margin:auto}h1{font-size:36px;line-height:1.15}section{background:#fafbf5;border:1px solid #bac7b2;padding:24px;border-radius:16px;margin:24px 0}.images{display:flex;overflow-x:auto;gap:14px}figure{flex:1;min-width:235px;margin:0}img{width:100%;aspect-ratio:381/444;object-fit:contain;background:#10160e}figcaption{font-size:14px;margin:10px 0}table{border-collapse:collapse}td,th{padding:6px 18px;text-align:left;border-bottom:1px solid #d7dfce}a{color:#286144}.note{background:#f5ecd6;border-left:4px solid #aa8440;padding:16px}p{max-width:1150px}</style><main><small>ASTRAFACTORY · ACTUAL RUNPOD INFERENCE</small><h1>SAM3, on the same plant images</h1><p>The full official image model, with text prompts for leaves, leaflets, stems and flower clusters. Same source pixels and geometry as the earlier pilot. No inference on the Mac.</p><div class="note"><b>Result:</b> plain leaf prompts found no reference leaves at confidence 0.5. Lower-confidence masks recover regions but include whole-canopy errors; examples and crops help only a little. No automatic accuracy claim is justified.<br><br><b>How to read this:</b> colored regions are model predictions. SAM3 text prompting and SAM2 automatic proposals are different pipelines. Known synthetic geometry lets us measure missed visible organs; real-photo accuracy still needs reviewed labels. The comparison does not prove every colored region is one leaf.</div>'''+''.join(panels)+'''<section><h2>What was tested</h2><p>SAM3 bfloat16 autocast, confidence 0.5, native 381×444 input; four prompts fixed before inference. No post-hoc green filter on SAM3. Synthetic coverage uses visible organs occupying at least 16 pixels and best mask IoU ≥0.5. Coverage is not one-to-one precision or average precision.</p><p>SAM3.1's published update focuses on video tracking. The current official still-image builder loads SAM3 weights.</p><p><a href="results/summary.json">Comparison metrics</a> · <a href="results/sam3/report.json">Full run report</a> · <a href="results/comparison.png">Comparison board</a> · <a href="https://github.com/facebookresearch/sam3">Official model</a> · <a href="https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md">3.1 release notes</a></p></section></main></html>'''
(out/'index.html').write_text(page);print(out/'index.html')
