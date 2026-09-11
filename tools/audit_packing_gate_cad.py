"""Check rigid gate sweep against its fixed frame and hinge ears."""
import json
from pathlib import Path
import cadquery as cq
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'runs/tower-lift-v9/cad'
fixed={n:cq.importers.importStep(str(P/(n+'.step'))).val() for n in ['pack_net_frame','gate_fixed_ears']}
ring=cq.importers.importStep(str(P/'gate_floor_ring.step')).val();lever=cq.importers.importStep(str(P/'gate_trigger_lever.step')).val().translate((0,70,0))
records=[]
for a in [0,5,15,30,45,60,90,105]:
 for name,part in [('floor',ring),('lever',lever)]:
  shape=part.rotate((0,0,0),(0,1,0),a).translate((-40,0,-5))
  for fn,base in fixed.items():
   common=shape.intersect(base);vol=common.Volume();records.append(dict(angle_deg=a,moving=name,fixed=fn,intersection_mm3=vol));print(a,name,fn,round(vol,5),flush=True)
(P/'gate-sweep-checks.json').write_text(json.dumps(dict(scope=__doc__,method='OpenCascade exact-solid intersections, 8 sampled angles; shaft-bearing clearance and structural loads excluded',records=records),indent=2)+'\n')
