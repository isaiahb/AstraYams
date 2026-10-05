"""Cel-shaded rendering of the unchanged MuJoCo action replay.
Uses renderer geometry IDs + depth for ink contours and quantized illumination.
All style changes affect material/light parameters only, never physics or poses.
"""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'speed-study'))
from sweep import *
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import maximum_filter
import imageio.v2 as imageio
DEST=Path(__file__).resolve().parent
RUN=OUT/'recommended';PROFILE=json.loads((OUT/'validation.json').read_text())['profile']
FONT='/System/Library/Fonts/Supplemental/Arial.ttf';BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
INK=np.array([27,37,55],dtype=np.uint8)
PALETTE={'studio_arm':[.85,.89,.91,1],'studio_dark':[.17,.22,.32,1],'tool':[.07,.61,.57,1],'liner':[.29,.78,.65,1],'fruit':[.95,.20,.30,1],'seed':[1,.79,.34,1],'leaf':[.30,.65,.32,1],'stem':[.38,.53,.23,1],'steel':[.57,.69,.80,1],'rail':[.43,.54,.59,1],'basket':[.91,.63,.25,1],'floor':[.79,.83,.78,1],'white':[.70,.78,.79,1],'pad':[.21,.29,.36,1],'soil':[.30,.25,.26,1]}
def apply_style(m):
 for name,color in PALETTE.items():
  try:i=m.material(name).id
  except KeyError:continue
  m.mat_rgba[i]=color;m.mat_specular[i]=0;m.mat_shininess[i]=0;m.mat_reflectance[i]=0
 m.vis.headlight.ambient[:]=.3;m.vis.headlight.diffuse[:]=.15;m.vis.headlight.specular[:]=0
 for i in range(m.nlight):m.light_specular[i]=0

def toon(renderer,e,cam):
 renderer.update_scene(e.data,camera=cam)
 rgb=renderer.render().copy()
 renderer.enable_segmentation_rendering();seg=renderer.render().copy();renderer.disable_segmentation_rendering()
 renderer.enable_depth_rendering();depth=renderer.render().copy();renderer.disable_depth_rendering()
 ids=seg[:,:,0];valid=(ids>=0)&(seg[:,:,1]==int(mujoco.mjtObj.mjOBJ_GEOM));ids=np.clip(ids,0,e.model.ngeom-1)
 colors=e.model.geom_rgba[:,:3].copy()
 for g in range(e.model.ngeom):
  mat=e.model.geom_matid[g]
  if mat>=0:colors[g]=e.model.mat_rgba[mat,:3]
 base=colors[ids]
 lum=rgb.astype(float)@np.array([.2126,.7152,.0722])/255
 blum=np.maximum(base@np.array([.2126,.7152,.0722]),.045)
 shade=lum/blum
 band=np.where(shade<.52,.57,np.where(shade<.90,.80,1.08))
 out=np.clip(base*band[:,:,None]*255,0,255).astype(np.uint8)
 out[~valid]=[215,235,234]
 # Geometric outlines, with depth thresholds to suppress coplanar primitive seams.
 edge=np.zeros(ids.shape,dtype=bool)
 for axis in [0,1]:
  other=np.roll(ids,1,axis);vv=np.roll(valid,1,axis);z=np.roll(depth,1,axis)
  line=(valid!=vv)|((ids!=other)&valid&vv&(np.abs(depth-z)>.0015))
  edge|=line
 edge[0,:]=False;edge[:,0]=False
 # Fixed pixel width, no temporal image-generated changes.
 leaf=np.array([(e.model.geom(i).name or "").startswith("leaf_surface") for i in range(e.model.ngeom)])[ids]
 thick=maximum_filter(edge,size=2)&~leaf
 out[thick]=INK
 out[edge&leaf]=[28,64,34]
 return out

def label(d,p,s,size=22,bold=False,color=(27,37,55)):
 d.text(p,s,font=ImageFont.truetype(BOLD if bold else FONT,size),fill=color)
