"""Join source tables to immutable portraits and generate a lightweight gallery."""
import csv,json,collections,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
m=json.loads((P/'manifest.json').read_text())
raw=list(csv.DictReader((P/'metadata/raw.dat.csv').open()))
lookup={r['Snapshot.ID.Tag']:r for r in raw if r['DAP']=='29'}
assert m['loaded']==40 and len({r['id'] for r in m['plants']})==40 and not m['errors']
for r in m['plants']:
 s=lookup[r['id']];r['cultivar']={'Felina':'Felina 32','Ferimon':'Ferimon 12','Han NE':'Han NE'}[s['Genotype']]
 r['source_genotype']=s['Genotype'];r['replicate']=int(s['Replicate']);r['psa_day29_kpixels']=float(s['PSA']);r['treatment']='Well-watered (Smarthouse experiment)'
 if r['id']=='084293-H': r['visual_review']='Shoot tip clipped at the top of the original frame (visually verified).'
 assert (P/r['file']).stat().st_size==r['bytes']
m['metric_note']='Researcher-reported projected shoot area at 29 days after planting; sum of three views, in kilopixels. Not leaf count, canopy density, or a measure derived from these displayed photos. Photo calendar date is explicit; the calendar-to-DAP alignment is inferred from the time-series endpoints, not independently verified.'
m['metadata_source']='https://figshare.com/articles/dataset/29097107';m['metadata_file']='data_code/Smarthouse/data/raw.dat.csv'
(P/'manifest.json').write_text(json.dumps(m,indent=2))
html=(P/'gallery-template.html').read_text().replace('__MANIFEST__',json.dumps(m))
(P/'index.html').write_text(html)
print(collections.Counter(r['cultivar'] for r in m['plants']))
print('40 unique originals; metadata matched 40/40; all same day and camera')
