"""Remote-only confidence diagnostic against unchanged synthetic coverage gate."""
from worker import require_remote
require_remote()
from pathlib import Path
import json
import numpy as np
root=Path('/workspace/sam3-comparison');out=root/'results'
probes=json.loads((out/'prompt-probe/report.json').read_text());report={}
for name in ['broad-render','narrow-render']:
 tag=name+'-leaf-low-confidence';row=next(r for r in probes['results'] if r['name']==tag)
 masks=np.load(out/'prompt-probe'/tag/'masks.npz')['masks'];confidence=np.array(row['scores'])
 ids=np.load(root/f'baseline/synthetic-audit/{name}/leaf-ids.npz')['ids']
 organs=[v for v in np.unique(ids) if v>=0 and (ids==v).sum()>=16];iou=[]
 for v in organs:
  gt=ids==v;iou.append((masks & gt).sum(axis=(1,2))/np.maximum(1,(masks | gt).sum(axis=(1,2))))
 iou=np.array(iou);report[name]={}
 for threshold in [.1,.25,.5]:
  selected=confidence>=threshold;best=iou[:,selected].max(axis=1) if selected.any() else np.zeros(len(organs))
  report[name][str(threshold)]={'proposals':int(selected.sum()),'visible_leaves_ge16px':len(organs),'covered_at_iou_05':int((best>=.5).sum()),'median_best_iou':float(np.median(best))}
(out/'diagnostic-audit.json').write_text(json.dumps({'notice':'Exploratory threshold comparison, not calibrated real-photo accuracy. Synthetic coverage gate unchanged.','results':report},indent=2))
print(json.dumps(report,indent=2))
