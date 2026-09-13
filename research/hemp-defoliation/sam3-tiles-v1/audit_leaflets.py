"""Remote audit: report leaflets separately from compound leaves."""
import os,platform
if platform.system()!='Linux' or not os.environ.get('RUNPOD_POD_ID'):raise SystemExit('RunPod only')
from pathlib import Path
import ast,json
import numpy as np
from scipy.optimize import linear_sum_assignment
root=Path('/workspace/sam3-comparison');out=root/'results/tiles-v1'
# Reuse exactly the scoring function without loading the model or running inference.
tree=ast.parse((root/'run_tiles.py').read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='evaluate')
exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'evaluate','exec'))
r=json.loads((out/'report.json').read_text())
for row in r['results']:
 if row['image']=='reference':continue
 ids=np.load(root/f"baseline/synthetic-audit/{row['image']}/leaflet-ids.npz")['ids']
 tag='standard' if row['threshold']==.5 else 'low-confidence'
 masks=np.load(out/f"{row['image']}/grid-{row['grid']}/{tag}-complete.npz")['masks']
 a=evaluate([{'mask':m} for m in masks],ids);a['visible_leaflets_ge16px']=a.pop('visible_whole_leaves_ge16px');row['leaflet_audit']=a
# Confirm exact optimization against already completed rows from the first pass.
old=[]
for line in (root/'first-pass.log').read_text().splitlines():
 if line.startswith('{'):old.append(json.loads(line))
checks=[]
for x in old:
 y=next(q for q in r['results'] if all(q[k]==x[k] for k in ['image','grid','threshold']))
 keys=['raw','edge_fragments','deduplicated_all','deduplicated_complete']+(['complete_audit','all_audit'] if 'complete_audit' in x else [])
 checks.append({'image':x['image'],'grid':x['grid'],'threshold':x['threshold'],'equal':all(x[k]==y[k] for k in keys)})
assert all(c['equal'] for c in checks)
(out/'acceleration-check.json').write_text(json.dumps({'unchanged_completed_rows':len(checks),'checks':checks},indent=2))
(out/'report.json').write_text(json.dumps(r,indent=2))
print(json.dumps([{'image':x['image'],'grid':x['grid'],'whole':x.get('complete_audit'),'leaflet':x.get('leaflet_audit')} for x in r['results'] if x['threshold']==.5],indent=2))
