import os,platform
if platform.system()!='Linux' or not os.environ.get('RUNPOD_POD_ID'):raise SystemExit('RunPod only')
import urllib.request,hashlib,zipfile,json
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
p=Path('/workspace/sam3-comparison/source-probe');p.mkdir(exist_ok=True)
u='https://zenodo.org/api/records/17783092/files/2022_GH-15B_Hemp_ShootCamera_Images.zip/content'
z=p/'shoots.zip';h=hashlib.md5()
with urllib.request.urlopen(u,timeout=90) as r,z.open('wb') as f:
 while True:
  b=r.read(1024*1024)
  if not b:break
  h.update(b);f.write(b)
assert h.hexdigest()=='744e231722aa8b7197bcd2b912fa5fcc'
with zipfile.ZipFile(z) as archive:
 names=sorted(n for n in archive.namelist() if n.lower().endswith(('.jpg','.png','.jpeg','.tif','.tiff')) and not '__MACOSX' in n)
 rows=[];board=Image.new('RGB',(1000,750),'#e7ece5');draw=ImageDraw.Draw(board)
 for i,n in enumerate(names[:6]):
  with archive.open(n) as f:im=Image.open(f);im.load();im=im.convert('RGB')
  name='sample-'+str(i)+'.png';im.save(p/name)
  thumb=ImageOps.contain(im,(325,325));board.paste(thumb,((i%3)*333,(i//3)*375+30));draw.text(((i%3)*333+3,(i//3)*375+3),f'{i}: {im.size}',fill='black')
  rows.append({'archive_path':n,'file':name,'size':im.size})
 board.save(p/'contact-sheet.png')
 (p/'sources.json').write_text(json.dumps({'url':u,'doi':'10.5281/zenodo.17783092','license':'CC BY 4.0','authors':'Elisa Morales; Marcus Griffiths; Christopher Topp','archive_md5':h.hexdigest(),'image_count':len(names),'samples':rows},indent=2))
 print((p/'sources.json').read_text())
