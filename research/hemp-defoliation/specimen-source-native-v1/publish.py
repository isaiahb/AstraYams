from pathlib import Path
from pypdf import PdfReader
import shutil
p=Path(__file__).resolve().parent
repo=p.parents[2]
o=repo/'runs/hemp-specimen-source-native-v1';o.mkdir(exist_ok=True)
im=PdfReader(repo/'research/hemp-defoliation/height-evidence-v1/papers/massuela-2022.pdf').pages[4].images[0]
assert im.image.size==(1552,627)
im.image.save(o/'figure-native.png')
for n in ['index.html','provenance.json']:shutil.copy2(p/n,o/n)
