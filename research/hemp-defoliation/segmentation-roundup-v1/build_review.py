"""Assemble a static evidence summary from returned JSON; no image processing."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'runs/hemp-segmentation-roundup-v1'
OUT.mkdir(parents=True, exist_ok=True)
r = json.loads((ROOT / 'runs/hemp-residual-segmentation-v1/results/report.json').read_text())
rows = []
names = {'unchanged-repeat': 'Unchanged repeat', 'black-fill': 'Black out captured pixels',
         'original-context-residual': 'Residual crops, original context'}
base = r['initial_baseline']['final_foreground_coverage']
for a in r['arms']:
    m = a['metrics']
    rows.append(f"<tr><td>{names[a['arm']]}</td><td>{100*m['final_foreground_coverage']:.2f}%</td>"
                f"<td>+{100*(m['final_foreground_coverage']-base):.2f} pp</td>"
                f"<td>{m['new_definite_background_pixels']}</td><td>{a['seconds']:.1f}s</td></tr>")
html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Plant segmentation · experiment results</title><style>
body{margin:0;background:#f3f4ed;color:#18352e;font:17px/1.55 system-ui,sans-serif}main{max-width:1120px;margin:auto;padding:30px}h1{font-size:38px;line-height:1.15}h2{font-size:24px}a{color:#125c65}section{background:white;border:1px solid #ccd9cd;border-radius:14px;padding:22px;margin:22px 0}.views{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}.views img{width:100%;display:block;background:#101510}figure{margin:0}figcaption{padding:10px 0}.muted{color:#54665e}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}td,th{padding:12px;border-bottom:1px solid #d8e0d7;text-align:left}th{font-size:14px}li{margin:10px 0}@media(max-width:700px){main{padding:18px}.views{grid-template-columns:1fr}h1{font-size:29px}}</style>
<main><p class="muted">AstraFactory · measured segmentation experiments · 2026-09-13</p>
<h1>Does looking at the missed tissue help?</h1>
<p><strong>Yes, slightly in this test. Keeping original context recovered more tissue than blacking it out, but neither solved organ labeling.</strong></p>
<section><h2>Same first pass, same 87-call second-pass budget</h2>
<p>Primary confidence 0.5. Coverage below is measured against a fixed color-based foreground estimate, <strong>not annotated leaf masks</strong>. Changes are percentage points, not percentage improvement. New background pixels count definite-background leakage added beyond the frozen baseline.</p>
<div class="scroll"><table><thead><tr><th>Second pass</th><th>Final proxy coverage</th><th>Gain</th><th>New background pixels</th><th>Run time*</th></tr></thead><tbody>ROWS</tbody></table></div>
<p class="muted">*Includes inference and diagnostics, excludes model setup. Equal call counts did not produce equal execution times. Unchanged repeat reproduced the baseline exactly at 0.5.</p>
<div class="views"><figure><img src="../hemp-sam3-comparison-v1/results/sam3/reference/input.png" alt="Original provisional plant photograph"><figcaption>Original · 381 × 444; preharvest reference, pot not visible.</figcaption></figure><figure><img src="../hemp-residual-segmentation-v1/results/black-fill/overlay.png" alt="Blackout residual result"><figcaption>Black-out result</figcaption></figure><figure><img src="../hemp-residual-segmentation-v1/results/original-context-residual/overlay.png" alt="Original context residual result"><figcaption>Original-context result</figcaption></figure></div>
<p>Blue: baseline coverage. Green: newly covered proxy tissue. Red: still missed. Orange: new definite-background leakage. Colors show tissue coverage, not organ identities.</p>
<p>At permissive confidence 0.1, the unchanged-image condition covered 91.51%, black-fill 90.81%, and residual crops 74.58%. The primary-threshold advantage is not consistent across thresholds. None of these values measures correctly labeled organs.</p>
<p><a href="../hemp-residual-segmentation-v1/index.html">Inspect all residual results, thresholds and close-ups →</a></p></section>
<section><h2>What still fails</h2><ul><li>The upper-left fan is still missed by the context-crop pass at the primary threshold.</li><li>Central and lower-right regions contain incomplete blade coverage. The crop pass produced 131 crop-edge proposals and 470 cross-crop overlapping proposal pairs; these are diagnostic counts, not leaf counts.</li><li>Broad region-exemplar boxes either miss most tissue at high confidence or flood background at permissive thresholds. They are not tight single-leaf examples.</li></ul><p><a href="../../research/hemp-defoliation/segmentation-alternatives-v1/evidence/index.html">Inspect alternative prompting tests and model research →</a></p></section>
<section><h2>Targeted point refinement completed</h2><p>Six manually chosen positive/negative point pairs produced 18 raw candidate masks in 4.62 seconds on the A40. Local candidates isolate small blade regions; broad alternatives also exist. This is an assisted-labeling test, not automatic whole-plant discovery or measured organ accuracy. The initial disabled-predictor configuration error was corrected, and both workers were verified stopped.</p><p><a href="../../research/hemp-defoliation/segmentation-alternatives-v1/evidence/index.html">Inspect every candidate and setup provenance →</a></p><p><a href="../hemp-manual-segmentation-v1/index.html">Inspect Astra’s subsequent direct manual annotation →</a></p></section><section><h2>A more useful source image</h2><p>Recovered an original 2472 × 3296 APPF frame with the plant tip, main stem and pot opening visible. The pot bottom is cropped; a support cage, dark foliage and yellow/brown tissue remain. It is a different sample/view/time from the inherited crop, not a paired before/after comparison. CC BY-NC 4.0.</p><p>This newly recovered reference <strong>has not been tested in the residual A/B</strong>. Its foreground must account for non-green plant tissue and exclude cage/pot before comparison.</p><p><a href="../../research/hemp-defoliation/living-reference-search-v2/index.html">Inspect native reference, alternatives and provenance →</a></p></section>
<p class="muted">Raw masks and failed conditions are preserved. No plant geometry, mechanics or robot-policy claims follow from this comparison.</p></main></html>'''
(OUT / 'index.html').write_text(html.replace('ROWS', ''.join(rows)))
print(OUT / 'index.html')
