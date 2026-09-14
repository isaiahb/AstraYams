from pathlib import Path
import shutil
p=Path(__file__).resolve().parent;o=p.parents[2]/'runs/hemp-specimen-reconstruction-v4';o.mkdir(exist_ok=True)
for n in ['index.html','viewer.mjs','specimen.json','checks.json','registration.json']:shutil.copy2(p/n,o/n)
