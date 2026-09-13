from pathlib import Path
import csv,json,hashlib,importlib.util,numpy as np
out=Path(__file__).resolve().parent; root=out.parents[2]
# Height summaries preserve experimental pooling and missing values.
rows=list(csv.DictReader((out/'evidence/anderson-2021-phenotypes.csv').read_text().splitlines()[1:]))
days=[31,36,52,67,77,99,114]; curves=[]
for name in sorted({r['Pedigree'] for r in rows if r['Pedigree']}):
 points=[]
 for day in days:
  values=[]
  for r in rows:
   if r['Pedigree']!=name:continue
   try: values.append(float(r[f'HGT {day} DAS'])/100)
   except ValueError: pass
  points.append({'day':day,'median_m':round(float(np.median(values)),4),'q25_m':round(float(np.quantile(values,.25)),4),'q75_m':round(float(np.quantile(values,.75)),4),'n':len(values)})
 curves.append({'name':name,'points':points,'pooling':'Unadjusted median across all six experimental treatments; not cultivar-only effect or commercial target.'})
spec=importlib.util.spec_from_file_location('previous',root/'research/hemp-defoliation/development-v2/build.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
data={'source':'Anderson et al. 2021, S2 raw phenotype data','doi':'10.1371/journal.pone.0252985','source_url':'https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0252985','license':'CC BY','source_sha256':hashlib.sha256((out/'evidence/anderson-2021-phenotypes.csv').read_bytes()).hexdigest(),'raw_height_unit':'cm; converted to metres','days':days,'curves':curves,'profiles':m.P,'warnings':['Height curves are cohort summaries, not individual plant histories.','Small late declines are retained in observations; geometry uses a nondecreasing envelope.','None of these curves specifies branch topology or a commercial production standard.']}
(out/'reference-data.json').write_text(json.dumps(data,indent=2))
import shutil
runtime=root/'runs/hemp-development-v3'; runtime.mkdir(exist_ok=True)
for name in ['index.html','viewer.js','plant.mjs','reference-data.json']:
 shutil.copy2(out/name,runtime/name)
if (out/'evidence/audit.json').exists():shutil.copy2(out/'evidence/audit.json',runtime/'audit.json')
print('Updated reference summaries and runtime at', runtime)
