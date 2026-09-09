"""Reference-linked, single-specimen contact model. All mechanics are uncalibrated.
The source graph is the design input; leaves/fruit grow from graph attachments.
"""
from pathlib import Path
import json,math,copy,argparse
import xml.etree.ElementTree as ET
import numpy as np
import mujoco,trimesh
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/workcells/strawberry-specimen'
def v(a):return ' '.join(f'{float(x):.8g}' for x in np.ravel(a))
def add(p,t,**kw):return ET.SubElement(p,t,{k:str(x) for k,x in kw.items()})
def build():
 spec=json.loads((ROOT/'tasks/strawberry_specimen/reference-graph.json').read_text());OUT.mkdir(exist_ok=True,parents=True)
 r=ET.Element('mujoco',model='reference_specimen_contact_only');add(r,'compiler',angle='radian',autolimits='true')
 add(r,'option',timestep='.0005',integrator='implicitfast',gravity='0 0 -9.81',iterations='80',cone='elliptic')
 vis=add(r,'visual');add(vis,'global',offwidth='1200',offheight='900');add(vis,'headlight',diffuse='.6 .6 .6',ambient='.4 .4 .4',specular='.1 .1 .1');add(vis,'quality',shadowsize='2048')
 asset=add(r,'asset');add(asset,'texture',name='sky',type='skybox',builtin='gradient',rgb1='.84 .87 .82',rgb2='.94 .95 .92',width='512',height='512');contact=add(r,'contact');w=add(r,'worldbody');act=add(r,'actuator');defaults=add(r,'default');add(defaults,'geom',condim='3',solref='.004 1',solimp='.95 .99 .001',friction='.45 .003 .001',rgba='.2 .35 .07 1')
 add(w,'light',pos='-.3 -.4 1.1',dir='.2 .3 -1',diffuse='.8 .8 .75',castshadow='true')
 add(w,'geom',name='ground',type='plane',size='1 1 .1',rgba='.88 .9 .85 1')
 # A real rim and substrate define support geometry; the stem is not pre-draped.
 add(w,'geom',name='trough_front',type='box',pos='0 .012 .215',size='.22 .012 .065',rgba='.8 .84 .79 1')
 add(w,'geom',name='trough_rim',type='capsule',fromto='-.22 -.002 .28 .22 -.002 .28',size='.007',rgba='.72 .77 .71 1')
 add(w,'geom',name='substrate',type='box',pos='0 .089 .258',size='.218 .068 .016',rgba='.16 .11 .07 1')
 add(w,'geom',name='trough_back',type='box',pos='0 .165 .215',size='.22 .012 .065',rgba='.8 .84 .79 1')
 for x in [-.215,.215]:add(w,'geom',name='trough_end_'+str(x),type='box',pos=v([x,.09,.21]),size='.008 .072 .06',rgba='.8 .84 .79 1')
 crown=add(w,'body',name='crown',pos=v(spec['crown_m']))
 # Short irregular crown at the soil line; compressed stem, not an exposed bulb.
 verts=[]
 for z,rad in [(-.012,.0055),(-.004,.007),( .003,.0065),(.009,.0045)]:
  for j in range(9):
   th=j*2*np.pi/9;rr=rad*(1+.12*np.sin(j*2.3));verts.append([rr*np.cos(th),rr*np.sin(th),z])
 hull=trimesh.convex.convex_hull(verts);add(asset,'mesh',name='crown_core_mesh',vertex=v(hull.vertices),face=' '.join(str(int(a)) for a in hull.faces.ravel()))
 add(crown,'geom',name='crown_core',type='mesh',mesh='crown_core_mesh',rgba='.25 .19 .075 1')
 records=[];roots={};ends={}
 def beam(parent,delta,name,radius,n=6,young=50e6):
  delta=np.array(delta,float);offset=np.zeros(3)
  if parent is crown:
   az=np.arctan2(delta[1],delta[0]);offset=np.array([.0045*np.cos(az),.0045*np.sin(az),.005+.001*np.cos(2*az)]);delta=delta-offset
   # Compact, overlapping basal sheath follows this stalk's actual attachment.
   stop=offset+delta/np.linalg.norm(delta)*.018
   add(crown,'geom',name=name+'_basal_sheath',type='capsule',fromto=v([offset[0]*.7,offset[1]*.7,-.003,*stop]),size='.0021',rgba='.32 .32 .09 1')
   # Thin stipule flanks the sheath; it is anatomy, not a detached decorative sphere.
   side=np.array([-np.sin(az),np.cos(az),0.])*.0035
   vv=np.array([offset+side,offset-side,stop+side*.25,stop-side*.25,offset+np.array([0,0,-.002]),stop+np.array([0,0,-.0007])]);hh=trimesh.convex.convex_hull(vv);mn=name+'_stipule_mesh';add(asset,'mesh',name=mn,vertex=v(hh.vertices),face=' '.join(str(int(a)) for a in hh.faces.ravel()));add(crown,'geom',name=name+'_stipule',type='mesh',mesh=mn,rgba='.4 .35 .14 1')
  u=np.linspace(0,1,n+1);points=u[:,None]*delta
  # Slight upward unloaded growth bias. Berry load supplies the hanging shape.
  points[:,2]+=.012*np.sin(np.pi*u);ds=np.diff(points,axis=0);prev=parent
  roots.setdefault(parent.get('name'),[]).append(name+'_0')
  for i,dx in enumerate(ds):
   rad=radius*(1-.22*i/n);L=np.linalg.norm(dx);k=young*np.pi*rad**4/4/L
   b=add(prev,'body',name=f'{name}_{i}',pos=v(offset if i==0 and parent is crown else [0,0,0] if i==0 else ds[i-1]))
   add(b,'joint',name=f'{name}_{i}_bend',type='ball',stiffness=k,damping=max(.001,k*.18),armature='1e-7')
   add(b,'geom',name=f'{name}_{i}_surface',type='capsule',fromto=v([0,0,0,*dx]),size=rad,density='850',rgba='.3 .4 .10 1')
   prev=b
  tip=add(prev,'body',name=name+'_tip',pos=v(ds[-1]));ends[tip.get('name')]=prev.get('name')
  records.append({'id':name,'radius_m':radius,'young_pa':young,'segments':n,'rest_shape':'near-straight upward growth bias; not loaded sag'})
  return tip
 def mesh(name,verts,faces):
  add(asset,'mesh',name=name,vertex=v(verts),face=' '.join(str(int(a)) for a in np.ravel(faces)))
 # Small convex wedges preserve serration and crease in BOTH visual and collision geometry.
 def leaflet(parent,name,length,width,pitch,roll,yaw,color):
  root=add(parent,'body',name=name+'_root',euler=v([roll,pitch,yaw]))
  add(root,'geom',name=name+'_petiolule',type='capsule',fromto='0 0 0 .009 0 0',size='.00075',mass='.00003',rgba='.35 .46 .1 1')
  prev=root;n=20;dx=length/n;span=n//4;profile=np.array(spec['leaflet_profile']['normalized_halfwidth_stations'])
  for panel in range(4):
   b=add(prev,'body',name=f'{name}_panel{panel}',pos=v([.009 if panel==0 else dx*span,0,0]))
   add(b,'joint',name=f'{name}_bend{panel}',type='hinge',axis='0 1 0',stiffness='.009',damping='.0009',armature='2e-8')
   for j in range(span):
    idx=panel*span+j;ts=np.array([idx,idx+1])/n;xx=ts*length
    # Obovate broad terminal leaflet; alternating tooth depth is resolved per wedge.
    widths=width*.5*np.interp(ts,profile[:,0],profile[:,1])*np.array([1 if idx%2 else .90,1 if (idx+1)%2 else .90]);widths=np.maximum(widths,.0005)
    centerz=.0018*np.sin(np.pi*ts);edgez=centerz+.003*np.sin(np.pi*ts)
    for side in [-1,1]:
     top=np.array([[j*dx,0,centerz[0]],[(j+1)*dx,0,centerz[1]],[(j+1)*dx,side*widths[1],edgez[1]],[j*dx,side*widths[0],edgez[0]]]);bot=top.copy();bot[:,2]-=.00045;verts=np.vstack([top,bot]);faces=trimesh.convex.convex_hull(verts).faces
     hull=trimesh.convex.convex_hull(verts);mn=f'{name}_w{idx}_{side}';mesh(mn,hull.vertices,hull.faces)
     add(b,'geom',name=mn,type='mesh',mesh=mn,mass=str(.0008/(n*2)),rgba=v(color))
    add(b,'geom',name=f'{name}_vein{idx}',type='capsule',fromto=v([j*dx,0,centerz[0]+.0002,(j+1)*dx,0,centerz[1]+.0002]),size='.00025',mass='0',contype='0',conaffinity='0',rgba='.36 .49 .13 1')
   prev=b
  add(contact,'exclude',body1=ends.get(parent.get('name'),parent.get('name')),body2=root.get('name'))
 for leaf in spec['leaves']:
  tip=beam(crown,np.array(leaf['tip'])-spec['crown_m'],'petiole_'+leaf['id'],.00165,n=7,young=85e6)
  for i,off in enumerate([-1.05,0,1.05]):
   length=leaf['length']*(1 if i==1 else .88);color=[.22,.39,.08,1] if leaf['age']=='mature' else [.35,.51,.12,1]
   leaflet(tip,f"leaf_{leaf['id']}_{i}",length,length/spec['leaflet_profile']['length_to_width'],leaf['pitch']+(i-1)*.1,(i-1)*.12,leaf['yaw']+off,color)
 nodes={'crown':crown}
 def berry(parent,f):
  body=add(parent,'body',name='fruit_'+f['id']);rad=f['radius'];length=f['length'];verts=[];faces=[];N=32;R=18
  for i in range(R+1):
   t=i/R;rr=rad*(.12+np.sin(np.pi*(t*.86+.1))**.8)*(1-.72*t)
   for j in range(N):
    th=2*np.pi*j/N;verts.append([rr*np.cos(th),rr*np.sin(th),-.002-length*t])
  for i in range(R):
   for j in range(N):a=i*N+j;b=i*N+(j+1)%N;c=(i+1)*N+j;dd=(i+1)*N+(j+1)%N;faces.extend([[a,b,c],[b,dd,c]])
  faces.extend([[0,j+1,j] for j in range(1,N-1)]);faces.extend([[R*N,R*N+j,R*N+j+1] for j in range(1,N-1)])
  mn='berrymesh_'+f['id'];mesh(mn,verts,faces);color={'red':[.65,.045,.025,1],'green':[.45,.56,.16,1],'turning':[.73,.3,.11,1]}[f['maturity']]
  add(body,'geom',name='berry_'+f['id'],type='mesh',mesh=mn,mass=f['mass'],rgba=v(color))
  for j in range(5):
   th=j*2*np.pi/5;add(body,'geom',name=f"calyx_{f['id']}_{j}",type='ellipsoid',size=v([rad*.55,.002,.0008]),pos=v([rad*.38*np.cos(th),rad*.38*np.sin(th),-.001]),euler=v([0,-.12,th]),mass='.00001',rgba='.18 .33 .055 1',contype='0',conaffinity='0')
  for i in range(2,R-1,2):
   for j in range(12):
    t=i/R;th=(j+.5*(i%4))*2*np.pi/12;rr=rad*(.12+np.sin(np.pi*(t*.86+.1))**.8)*(1-.72*t)
    add(body,'geom',name=f"seed_{f['id']}_{i}_{j}",type='ellipsoid',size='.00035 .00025 .0006',pos=v([rr*np.cos(th),rr*np.sin(th),-.002-length*t]),mass='0',rgba='.68 .55 .18 1',contype='0',conaffinity='0')
  add(contact,'exclude',body1=ends[parent.get('name')],body2=body.get('name'))
 for branch in spec['truss']:
  tip=beam(nodes[branch['parent']],branch['unloaded_delta'],branch['id'],branch['radius'],n=7,young=45e6);nodes[branch['id']]=tip
  if 'fruit' in branch:berry(tip,branch['fruit'])
 for parent,kids in roots.items():
  for a in kids:
   add(contact,'exclude',body1=parent,body2=a)
   if parent=='crown':add(contact,'exclude',body1=parent,body2=a[:-1]+'1')
   if parent in ends:add(contact,'exclude',body1=ends[parent],body2=a)
   for b in kids:
    if a<b:add(contact,'exclude',body1=a,body2=b)
 probe=add(w,'body',name='probe',pos='0 0 0');add(probe,'geom',name='probe_surface',type='sphere',size='.009',mass='.025',rgba='.9 .54 .12 1',contype='2',conaffinity='1')
 for i in range(3):
  axis=np.eye(3)[i];add(probe,'joint',name=f'probe_{i}',type='slide',axis=v(axis),damping='.5');add(act,'position',name=f'probe_{i}',joint=f'probe_{i}',kp='180',kv='4',forcerange='-1.5 1.5')
 ET.indent(r);ET.ElementTree(r).write(OUT/'scene.xml',encoding='unicode')
 (OUT/'model.json').write_text(json.dumps({'reference_graph':spec,'beam_parameters':records,'scope':'one representative specimen; inferred depth and attachments; uncalibrated contact model; no cutting, no robot policy','collision':'leaf surfaces consist of convex wedges, same rendered/contact mesh; berry convex collision'},indent=2))
 mujoco.MjModel.from_xml_path(str(OUT/'scene.xml'));print('Compiled',OUT/'scene.xml')
if __name__=='__main__':build()
