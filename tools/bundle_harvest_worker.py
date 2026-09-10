"""Stream only task sources/checkpoints and referenced mesh assets to our worker.

Preserve absolute asset paths on Linux; do not upload credentials or user folders.
"""
import argparse,json,subprocess,tarfile,xml.etree.ElementTree as E
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def files():
 selected=set()
 for folder in ['src/astrafactory','tools']:
  selected.update((ROOT/folder).glob('*.py'))
 runs=['runs/dual-harvest-commission-v13','runs/harvest-skill-suite/curriculum','runs/harvest-skill-suite/dynamic-net-curriculum','runs/harvest-skill-suite/population-cells','runs/harvest-skill-suite/clip-v2','runs/harvest-skill-suite/approach-v1','runs/harvest-skill-suite/withdraw-v3','runs/harvest-skill-suite/basket-commission-v4','runs/harvest-skill-suite/basket-task-v3','runs/catcher-specialist-v3']
 for folder in runs:
  for p in (ROOT/folder).rglob('*'):
   if p.is_file() and p.suffix in ['.xml','.npz','.npy','.zip','.json'] and not any(t in p.parts for t in ['review','mesh-export','presentation']):selected.add(p)
 for path in list(selected):
  if path.suffix!='.xml':continue
  for node in E.parse(path).iter():
   if not node.get('file'):continue
   dependency=(path.parent/node.get('file')).resolve()
   if not str(dependency).startswith('/Users/isaiah/Documents/BallahTech/') or not dependency.is_file():raise ValueError('Unexpected or missing referenced asset: '+str(dependency))
   selected.add(dependency)
 return sorted(selected)

def main():
 p=argparse.ArgumentParser();p.add_argument('--connection',default='/tmp/astrafactory-harvest-worker/connection.json');a=p.parse_args();c=json.loads(Path(a.connection).read_text());host=c['publicIp'];port=c['portMappings']['22'];selected=files();print('Files',len(selected),'MB',sum(p.stat().st_size for p in selected)/1e6,flush=True)
 ssh=['ssh','-i','/tmp/astrafactory-runpod/id_ed25519','-o','UserKnownHostsFile=/tmp/astrafactory-harvest-worker/known_hosts','-o','StrictHostKeyChecking=accept-new','-p',str(port),'root@'+host,'tar xzf - -C /']
 process=subprocess.Popen(ssh,stdin=subprocess.PIPE)
 with tarfile.open(fileobj=process.stdin,mode='w|gz') as tar:
  for path in selected:tar.add(path,arcname=str(path).lstrip('/'),recursive=False)
 process.stdin.close();assert process.wait()==0
 print('STREAMED',flush=True)
if __name__=='__main__':main()
