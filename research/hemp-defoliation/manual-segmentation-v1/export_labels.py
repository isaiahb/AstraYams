"""Export hand-entered vectors and lightweight geometry checks; no rasterization."""
import json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SRC=Path(__file__).parent
d=json.loads((SRC/'annotations.json').read_text())
OUT=ROOT/'runs/hemp-manual-segmentation-v1';OUT.mkdir(exist_ok=True)
def area(p):return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1])))/2
def orient(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
annotations=[];ignore=[];errors=[]
cats={'leaflet':1,'stem':2,'support':3}
for q in d['polygons']:
 p=q['points'];n=len(p)
 if n<3 or area(p)<=0 or any(not(0<=x<=381 and 0<=y<=444) for x,y in p):errors.append(q['id']+':invalid bounds/area')
 for i in range(n):
  for j in range(i+2,n):
   if i==0 and j==n-1:continue
   a,b,c,e=p[i],p[(i+1)%n],p[j],p[(j+1)%n]
   if orient(a,b,c)*orient(a,b,e)<0 and orient(c,e,a)*orient(c,e,b)<0:errors.append(q['id']+':self-crossing')
 if q['label']=='unknown_cluster':ignore.append(q);continue
 xs,ys=zip(*p)
 annotations.append({'id':int(q['id'][1:]),'image_id':1,'category_id':cats[q['label']],
  'segmentation':[[v for xy in p for v in xy]],'bbox':[min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)],
  'area':area(p),'iscrowd':0,'review_status':'provisional assistant trace','trainable':False,
  'certainty':q['certainty'],'parent_leaf_id':None})
report={'counts':dict(Counter(q['label'] for q in d['polygons'])),'geometry_errors':errors,
        'geometry_checks_only':True,'boundary_accuracy_measured':False,'all_25_cells_visually_reviewed':True}
assert not errors,errors
coco={'info':{'description':'Provisional manual visible-part polygons. Unannotated pixels UNKNOWN. Not benchmark ground truth; no pixel-accurate guarantee.'},
 'images':[{'id':1,'file_name':d['image'],'width':381,'height':444,'license':1}],
 'licenses':[{'id':1,'name':'CC BY 4.0','url':'https://creativecommons.org/licenses/by/4.0/'}],
 'categories':[{'id':v,'name':k} for k,v in cats.items()], 'annotations':annotations,
 'ignore_regions':ignore,'unannotated_pixels_status':'unknown','source_url':d['source_url']}
(SRC/'coco-draft.json').write_text(json.dumps(coco,indent=2)+'\n')
(SRC/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
def svg(box,source=None):
 x,y,w,h=box;s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w} {h}">']
 if source:s.append(f'<image href="{source}" x="0" y="0" width="381" height="444"/>')
 for q in d['polygons']:
  if q['label']=='unknown_cluster':continue
  color={'leaflet':'#31e2a4','stem':'#ffd556','support':'#acb5c5'}[q['label']]
  pts=' '.join(f'{a},{b}' for a,b in q['points'])
  s.append(f'<polygon id="{q["id"]}" points="{pts}" fill="{color}" fill-opacity="{.25 if source else 1}" stroke="{color}" stroke-width=".3"><title>{q["id"]}: {q["label"]}</title></polygon>')
 s.append('</svg>');return ''.join(s)
(OUT/'labels.svg').write_text(svg([0,0,381,444]))
(OUT/'overlay.svg').write_text(svg([0,0,381,444],'../hemp-sam3-comparison-v1/results/sam3/reference/input.png'))
tiles=OUT/'tiles';tiles.mkdir(exist_ok=True)
manifest=[]
for r in range(5):
 for c in range(5):
  x0,x1=d['grid_columns'][c:c+2];y0,y1=d['grid_rows'][r:r+2]
  ids=[]
  for q in d['polygons']:
   xs,ys=zip(*q['points'])
   if max(xs)>=x0 and min(xs)<x1 and max(ys)>=y0 and min(ys)<y1:ids.append(q['id'])
  name=f'r{r+1}-c{c+1}.svg';(tiles/name).write_text(svg([x0,y0,x1-x0,y1-y0],'../../hemp-sam3-comparison-v1/results/sam3/reference/input.png'))
  manifest.append({'row':r+1,'column':c+1,'core_xyxy':[x0,y0,x1,y1],'shared_global_ids_bbox_overlap':ids,'reviewed':True,'svg':name})
(SRC/'grid-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(report))
