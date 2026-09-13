"""Reproducible offline orthographic diagnostic renders of the exported mesh.

Uses depth-sorted triangles for compact review figures; WebGL viewer provides
depth-buffered interactive inspection. These images do not add plant geometry.
"""
from pathlib import Path
import json,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=ROOT/'runs/hemp-photo-fit-v1'
M=json.loads((OUT/'manifest.json').read_text());C=M['camera'];PX=C['m_per_pixel']
W,H=C['width'],C['height'];UP=2
CENTER=np.array([(W/2-C['root_pixel'][0])*PX,0,(C['root_pixel'][1]-H/2)*PX])

def render(name,view='front',skeleton=False):
    data=json.loads((OUT/(name+'.json')).read_text());im=Image.new('RGB',(W*UP,H*UP),'#10160e');draw=ImageDraw.Draw(im)
    if view=='side':right=np.array([0,1,0]);up=np.array([0,0,1]);depth=np.array([-1,0,0])
    elif view=='top':right=np.array([1,0,0]);up=np.array([0,1,0]);depth=np.array([0,0,-1])
    else:right=np.array([1,0,0]);up=np.array([0,0,1]);depth=np.array([0,1,0])
    triangles=[];light=np.array([-.25,-.6,.76]);light/=np.linalg.norm(light)
    for part in data['parts']:
        if skeleton and part['kind']!='axis':continue
        xyz=np.array(part['positions']).reshape(-1,3);ind=np.array(part['indices']).reshape(-1,3)
        pos=np.column_stack([((xyz-CENTER)@right/PX+W/2)*UP,(H/2-(xyz-CENTER)@up/PX)*UP])
        d=xyz@depth
        color=np.array([int(part['color'][i:i+2],16) for i in [1,3,5]])
        normals=np.cross(xyz[ind[:,1]]-xyz[ind[:,0]],xyz[ind[:,2]]-xyz[ind[:,0]])
        lengths=np.linalg.norm(normals,axis=1);normals/=np.maximum(lengths[:,None],1e-10)
        levels=.58+.64*np.abs(normals@light)
        cols=np.clip(levels[:,None]*color,0,255).astype(np.uint8)
        for k,ids in enumerate(ind):
            if lengths[k]<1e-12:continue
            triangles.append((d[ids].mean(),pos[ids],tuple(map(int,cols[k]))))
    for _,pts,col in sorted(triangles,key=lambda a:-a[0]):draw.polygon([tuple(p) for p in pts],fill=col)
    im.save(OUT/f'{name}-{view}{"-axes" if skeleton else ""}.png')
    return im

def title_image(im,title,subtitle):
    w,h=im.size;canvas=Image.new('RGB',(w,h+95),'#edf0e5');canvas.paste(im,(0,95));d=ImageDraw.Draw(canvas)
    font='/System/Library/Fonts/Supplemental/Arial.ttf'
    d.text((18,12),title,fill='#223d2e',font=ImageFont.truetype(font,27))
    d.text((18,52),subtitle,fill='#526449',font=ImageFont.truetype(font,17))
    return canvas

def main():
    src=Image.open(OUT/'reference.jpg').resize((W*UP,H*UP))
    initial=render('initial');fitted=render('fitted');shaped=render('shape-constrained');side=render('shape-constrained','side');top=render('shape-constrained','top');skel=render('shape-constrained','front',True)
    panels=[title_image(src,'Published reference','Cherry Wine · actual photograph'),title_image(fitted,'Mask-optimized hypothesis','Coverage objective favors broader leaves'),title_image(shaped,'Narrower-leaf hypothesis','Curved medial mesh · width not mask-optimized')]
    board=Image.new('RGB',(sum(x.width for x in panels),panels[0].height),'#edf0e5');x=0
    for panel in panels:board.paste(panel,(x,0));x+=panel.width
    board.save(HERE/'evidence/spot-the-difference.png');board.save(OUT/'spot-the-difference.png')
    panels=[title_image(skel,'Connections','Manual projections + latent secondary axes'),title_image(side,'Side view','Unobserved depth hypothesis A'),title_image(top,'Top view','No independent depth measurement')]
    board=Image.new('RGB',(sum(x.width for x in panels),panels[0].height),'#edf0e5');x=0
    for panel in panels:board.paste(panel,(x,0));x+=panel.width
    board.save(HERE/'evidence/geometry-review.png');board.save(OUT/'geometry-review.png')
    print('Saved actual exported-mesh comparison and orthogonal review')

if __name__=='__main__':main()
