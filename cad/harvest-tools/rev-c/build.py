"""Rev-C concept: a hooked counterblade arrests forward stem escape.
Nominal steel solid only; no production edge grinding or calibration claim.
"""
from pathlib import Path
import json,cadquery as cq
P=Path(__file__).resolve().parent;B=P.parent/'rev-b'
blade=cq.importers.importStep(str(B/'right_blade.step'))
wall=cq.Workplane('XY').box(3.8,12,.5).translate((205.3,0,.27))
nose=cq.Workplane('XY').box(5.5,2,.5).translate((204.45,-5,.27))
shape=blade.union(wall).union(nose).clean();s=shape.val();assert s.isValid() and len(s.Solids())==1
cq.exporters.export(s,str(P/'right_blade.step'));cq.exporters.export(s,str(P/'right_blade.stl'),tolerance=.04,angularTolerance=.12)
restored=cq.importers.importStep(str(P/'right_blade.step')).val();assert restored.isValid() and abs(restored.Volume()-s.Volume())<.01
report=dict(parent='rev-b',change='Hooked counterblade to retain stalk against the exposed cutting edges; blade thickness and bypass separation preserved.',part='right_blade',volume_mm3=s.Volume(),valid=True,solid_count=len(s.Solids()),cut_site_canonical_mm=[202,0,0],limitations=['Prototype geometry, not manufactured or calibrated','Grinding, surface finish, blade stiffness and tolerances unverified'])
(P/'design.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
