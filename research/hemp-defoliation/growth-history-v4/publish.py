"""Copy the small review source to the existing static server's runs folder."""
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent
OUT=HERE.parents[2]/'runs/hemp-growth-history-v4'
OUT.mkdir(parents=True,exist_ok=True)
for name in ('index.html','viewer.mjs','growth.mjs','checks.json','sources.json','leaf-observations.json','RULES.md','foliage-inventory.json'):
    shutil.copy2(HERE/name,OUT/name)
print(OUT)
