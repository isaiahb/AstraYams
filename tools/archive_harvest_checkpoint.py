"""Archive selected local evidence and referenced CAD meshes, without publishing."""
from pathlib import Path
import argparse,hashlib,io,json,subprocess,tarfile,xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='append',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();files=set();visited=set()
 if a.out.exists():raise FileExistsError('Choose a new checkpoint filename; existing archives are preserved')
 def add(path):
  path=path.absolute()
  if not path.is_relative_to(ROOT):raise ValueError('Checkpoint dependency outside repository: '+str(path))
  if path in visited:return
  visited.add(path)
  if not path.exists():raise FileNotFoundError(path)
  if path.is_dir():
   for child in path.rglob('*'):
    if child.is_file() and '__pycache__' not in child.parts:files.add(child)
  else:files.add(path)
 for run in a.run:
  run=ROOT/run;add(run)
  config=run.with_suffix('.json')
  if config.exists():
   add(config);cfg=json.loads(config.read_text())
   for key,value in cfg.items():
    if (key.endswith('_source') or key=='task') and isinstance(value,str):add(ROOT/value)
   for value in cfg.get('policies',{}).values():add(ROOT/value)
 # Preserve source separately from the recorded evidence; no runtime caches,
 # credentials, .git directory or environment variables enter the archive.
 for base in [ROOT/'src/astrafactory',ROOT/'tools']:
  for x in base.glob('*.py'):add(x)
 for x in [ROOT/'tools/templates/dual-harvest-review.html',ROOT/'docs/evidence/harvest-skill-suite']:add(x)
 for scene in [x for x in files if x.name=='scene.xml']:
  tree=E.parse(scene);compiler=tree.getroot().find('compiler');meshdir=compiler.get('meshdir','') if compiler is not None else ''
  for item in tree.iter():
   if item.tag not in ['mesh','texture','hfield','include'] or 'file' not in item.attrib:continue
   dep=Path(item.get('file'))
   if not dep.is_absolute():dep=scene.parent/(meshdir if item.tag=='mesh' else '')/dep
   add(dep)
 manifest={str(x.relative_to(ROOT)):dict(bytes=x.stat().st_size,sha256=hashlib.sha256(x.read_bytes()).hexdigest()) for x in sorted(files)}
 metadata=dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),original_root=str(ROOT),scope='Local checkpoint only. Absolute mesh paths need rebasing on another checkout; Python/runtime dependencies and Three.js are installed separately. MP4 files are standalone.',files=manifest)
 a.out.parent.mkdir(parents=True,exist_ok=True)
 with tarfile.open(a.out,'w:gz',dereference=True) as archive:
  for x in sorted(files):archive.add(x,arcname=str(x.relative_to(ROOT)),recursive=False)
  raw=json.dumps(metadata,indent=2).encode();info=tarfile.TarInfo('CHECKPOINT-MANIFEST.json');info.size=len(raw);archive.addfile(info,io.BytesIO(raw))
 # Verify archived bytes, not just the files that were intended for inclusion.
 with tarfile.open(a.out) as archive:
  for name,expected in manifest.items():
   raw=archive.extractfile(name).read();assert len(raw)==expected['bytes'] and hashlib.sha256(raw).hexdigest()==expected['sha256'],name
 receipt=dict(archive=str(a.out),bytes=a.out.stat().st_size,sha256=hashlib.sha256(a.out.read_bytes()).hexdigest(),verified_files=len(manifest),git_head=metadata['git_head']);a.out.with_suffix(a.out.suffix+'.receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
if __name__=='__main__':main()
