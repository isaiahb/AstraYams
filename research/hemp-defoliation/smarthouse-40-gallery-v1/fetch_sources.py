"""Fetch one unmodified camera PNG per plant; no image processing or ML.
Requires remotezip (pip install remotezip). Raw photos stay outside Git.
"""
import concurrent.futures, datetime, hashlib, json, re, struct, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path
from remotezip import RemoteZip
ROOT=Path(__file__).resolve().parent
BASE='https://projects.pawsey.org.au/appf-tpa-0541-ph-ua-gill-hemp-pia'
DAY='2021-02-18'
PREFIX='RGB_3D_3D_side_far_0_'
(ROOT/'images').mkdir(exist_ok=True)

def fetch(key):
    ident=re.search(r'(\d{6}-H)',key).group(1)
    cached=ROOT/'records'/f'{ident}.json'
    if cached.exists():
        record=json.loads(cached.read_text())
        if (ROOT/record['file']).exists(): return record
    with RemoteZip(BASE+'/'+key, timeout=90) as z:
        members=[i for i in z.infolist() if i.filename.endswith('.png') and DAY in i.filename]
        if len(members)!=1: raise ValueError(f'{ident}: expected one frame on {DAY}, found {len(members)}')
        info=members[0]; data=z.read(info.filename)
    if data[:8]!=b'\x89PNG\r\n\x1a\n': raise ValueError('not a PNG')
    name='images/'+info.filename
    (ROOT/name).write_bytes(data)
    record=dict(id=ident,date=DAY,file=name,archive=BASE+'/'+key,member=info.filename,
      dimensions=struct.unpack('>II',data[16:24]),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
      cultivar=None,visual_review='pending',source='https://doi.org/10.25909/23211779.v1',
      license='CC BY-NC 4.0',attribution='Rachel Burton; APPF Plant Accelerator, University of Adelaide; UA (Gill)')
    cached.parent.mkdir(exist_ok=True);cached.write_text(json.dumps(record,indent=2))
    return record

def main():
    xml=ET.fromstring(urllib.request.urlopen(BASE+'?prefix='+PREFIX).read())
    keys=sorted(e.text for e in xml.iter() if e.tag.endswith('Key') and re.fullmatch(PREFIX+r'\d{6}-H.zip',e.text or ''))
    assert len(keys)==40, f'Expected 40 plants, found {len(keys)}'
    rows=[];errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(fetch,k):k for k in keys}
        for f in concurrent.futures.as_completed(futures):
            try:
                r=f.result();rows.append(r);print(f'{len(rows)}/40 {r["id"]} {r["dimensions"]}',flush=True)
            except Exception as e:
                errors.append(dict(archive=futures[f],error=str(e)));print('ERROR',errors[-1],flush=True)
            (ROOT/'manifest.json').write_text(json.dumps(dict(date=DAY,expected=40,loaded=len(rows),plants=sorted(rows,key=lambda x:x['id']),errors=errors),indent=2))
    if errors: raise SystemExit('Fetch incomplete; rerun to retry missing records')
if __name__=='__main__': main()
