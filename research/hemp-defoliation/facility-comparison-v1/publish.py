from pathlib import Path
import shutil
here=Path(__file__).resolve().parent
out=here.parents[2]/'runs/hemp-facility-comparison-v1'
out.mkdir(parents=True,exist_ok=True)
for name in ['index.html','viewer.mjs','growth.mjs','leaf-observations.json','checks.json','sources.json','RULES.md','foliage-inventory.json','references.json']:
 shutil.copy2(here/name,out/name)
print(out)
