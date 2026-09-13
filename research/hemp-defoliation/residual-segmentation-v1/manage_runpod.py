"""Provision/status/stop the isolated residual experiment worker."""
import json, os, sys, time, urllib.request
from pathlib import Path
HERE=Path(__file__).parent
H={'Authorization':'Bearer '+os.environ['RUNPOD_API_KEY'],'User-Agent':'AstraFactory/1.0','Content-Type':'application/json'}
def api(path,method='GET',body=None):
 req=urllib.request.Request('https://rest.runpod.io/v1/'+path,headers=H,method=method,data=json.dumps(body).encode() if body else None)
 with urllib.request.urlopen(req,timeout=30) as r:
  b=r.read(); return json.loads(b) if b else {}
cmd=sys.argv[1]
if cmd in ('create-watch','restart-watch'):
 body={'name':'astra-residual-segmentation-v1-20260913','imageName':'runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04','gpuTypeIds':['NVIDIA A40'],'gpuCount':1,'cloudType':'SECURE','computeType':'GPU','containerDiskInGb':40,'volumeInGb':0,'ports':['22/tcp'],'supportPublicIp':True,'env':{'PUBLIC_KEY':Path('/tmp/astrafactory-sam3/id_ed25519.pub').read_text().strip()}}
 if cmd=='create-watch':
  x=api('pods','POST',body); pod=x['id']
 else:
  pod=json.loads((HERE/'pod.json').read_text())['id']; (HERE/'stop').unlink(missing_ok=True); api('pods/'+pod+'/start','POST'); x=api('pods/'+pod)
 deadline=time.time()+1800
 (HERE/'pod.json').write_text(json.dumps({'id':pod,'deadline':deadline},indent=2))
 print(json.dumps({k:x.get(k) for k in ['id','name','costPerHr','desiredStatus']}),flush=True)
 while True:
  if time.time()>deadline or (HERE/'stop').exists():
   try:
    api('pods/'+pod+'/stop','POST'); x=api('pods/'+pod)
    if x.get('desiredStatus')=='EXITED':
     (HERE/'shutdown.json').write_text(json.dumps({'id':pod,'desiredStatus':'EXITED','verified_at_unix':time.time(),'costPerHr':x.get('costPerHr'),'local_inference':False},indent=2)); print('Verified EXITED',flush=True); break
   except Exception as e: print('Stop retry '+type(e).__name__,flush=True)
  time.sleep(10)
else:
 pod=json.loads((HERE/'pod.json').read_text())['id']
 if cmd=='stop':
  (HERE/'stop').touch(); api('pods/'+pod+'/stop','POST'); print('Stop requested')
 else:
  x=api('pods/'+pod); print(json.dumps({k:x.get(k) for k in ['id','desiredStatus','publicIp','portMappings','costPerHr']}))
