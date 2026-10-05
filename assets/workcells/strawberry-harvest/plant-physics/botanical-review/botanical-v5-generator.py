"""Candidate branched beam plant. Parameters are uncalibrated research priors.
No robot/camera/tool geometry changes. Build reads the frozen baseline XML.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np, json, copy, math
P=Path(__file__).resolve().parent; BASE=P.parent/'multi-harvest/scene.xml'
def v(a):return ' '.join(f'{x:.9g}' for x in np.ravel(a))
def sub(p,t,**kw):return ET.SubElement(p,t,{k:str(x) for k,x in kw.items()})
def build(stiffness_scale=1.,segments=6,tag='candidate'):
 root=ET.parse(BASE).getroot();w=root.find('worldbody');eq=root.find('equality');act=root.find('actuator');records=[];junction_roots={};terminal_bodies={}
 root.find('option').set('timestep','.001');root.find('option').set('integrator','implicitfast')
 # Remove only world-attached decorative plant surfaces, not robot hardware.
 for g in list(w.findall('geom')):
  if g.get('material') in ['leaf','stem','fruit'] or g.get('name','').startswith('crop_fruit'):w.remove(g)
 # Preserve the original fruit bodies/visuals as templates. Give every fruit full contacts.
 template=copy.deepcopy(w.find("body[@name='fruit']")); oldfruits=[]
 for j in range(3):
  suf='' if j==0 else '_'+str(j)
  oldfruits.append(w.find("body[@name='fruit"+suf+"']"));w.remove(w.find("body[@name='stem_0"+suf+"']"));w.remove(oldfruits[-1]);eq.remove(eq.find("weld[@name='stem_integrity"+suf+"']"))
 # Branch axes follow local rest geometry; equivalent rotational spring k=EI/L.
 def beam(parent,start,end,name,radius=.0018,n=segments,young=80e6,control=None):
  junction_roots.setdefault(parent.get('name'),[]).append(name)
  start=np.array(start,dtype=float);end=np.array(end,dtype=float)
  control=np.array(control if control is not None else (start+end)/2,dtype=float)
  us=np.linspace(0,1,n+1);points=np.array([(1-u)**2*start+2*u*(1-u)*control+u*u*end for u in us]);deltas=np.diff(points,axis=0)
  b=parent;ks=[];length=0
  for i,delta in enumerate(deltas):
   L=np.linalg.norm(delta);length+=L;t=delta/L;ax=np.cross(t,[1.,0,0])
   if np.linalg.norm(ax)<.1:ax=np.cross(t,[0,1.,0])
   ax/=np.linalg.norm(ax);ay=np.cross(t,ax);r=radius*(1-.16*i/n);I=np.pi*r**4/4;E=young*stiffness_scale;k=E*I/L;kt=E/(2*1.35)*2*I/L;ks.append(k)
   b=sub(b,'body',name=f'{name}_{i}',pos=v(start if i==0 else deltas[i-1]))
   for suffix,axis,kk in [('x',ax,k),('y',ay,k),('twist',t,kt)]:
    sub(b,'joint',name=f'{name}_{i}_{suffix}',type='hinge',axis=v(axis),stiffness=kk,damping=max(.00008,.20*kk),armature='1e-8',limited='false')
   sub(b,'geom',name=f'{name}_{i}_surface',type='capsule',fromto=v([0,0,0,*delta]),size=r,density='900',material='stem',contype='128',conaffinity='255',friction='.45 .002 .0001',solref='.01 1')
  tip=sub(b,'body',name=name+'_tip',pos=v(deltas[-1]))
  terminal_bodies[name+'_tip']=name+'_'+str(n-1)
  records.append(dict(name=name,radius_m=radius,length_m=float(length),segments=n,young_pa=E,natural_shape='Quadratic curved rest centerline, tapering cross section',damping_relaxation_seconds=.20,bend_joint_nm_per_rad=ks))
  return tip
 def fruit(parent,absolute,ident,active=None):
  b=copy.deepcopy(template);suf='' if active==0 else '_'+str(active)
  if active is not None:
   for el in b.iter():
    if 'name' in el.attrib:el.set('name',el.get('name')+suf)
   b.set('name','fruit'+suf);ename='stem_integrity'+suf
  else:
   for el in b.iter():
    if 'name' in el.attrib:el.set('name',f'crop{ident}_'+el.get('name'))
   b.set('name',f'crop_fruit_{ident}');ename=f'crop_integrity_{ident}'
  b.set('pos',v(absolute));w.append(b)
  for g in b.findall('geom'):
   if 'collision' in g.get('name','') or 'cut_stem' in g.get('name',''):g.set('conaffinity','255');g.set('contype','128')
  for g in b.findall('geom'):
   if 'berry_collision' in g.get('name',''):
    g.set('type','mesh');g.set('mesh','strawberry_mesh');g.attrib.pop('size',None)
  contact=root.find('contact')
  if contact is None:contact=sub(root,'contact')
  sub(contact,'exclude',body1=terminal_bodies[parent.get('name')],body2=b.get('name'))
  sub(eq,'weld',name=ename,body1=parent.get('name'),body2=b.get('name'),solref='.002 1',solimp='.9999 .99999 .0001')
  return b
 # Three connected lamina panels share boundary widths; no stack-of-discs appearance.
 for q in range(3):
  verts=[];faces=[]
  for i in range(5):
   x=.022*i/4;t=(q*.022+x)/.066;width=max(.0008,.026*np.sin(np.pi*t)**.65)*(1 if i%2==0 else .90)
   for z in [-.0004,.0004]:
    for y in [-width,width]:verts.append([x,y,z])
  for i in range(4):
   a=i*4;b=(i+1)*4
   for aa,bb,cc,dd in [(a,a+1,b+1,b),(a+2,b+2,b+3,a+3),(a,b,b+2,a+2),(a+1,a+3,b+3,b+1)]:faces.extend([[aa,bb,cc],[aa,cc,dd]])
  faces.extend([[0,2,3],[0,3,1],[16,17,19],[16,19,18]])
  sub(root.find('asset'),'mesh',name=f'plant_leaf_panel_{q}',vertex=v(verts),face=' '.join(str(x) for x in np.ravel(faces)))
 def leaves(parent,cluster):
  # Upright petioles emerge independently from the compact crown, not fruit forks.
  for j,angle in enumerate([-.35,.9,2.15,3.3,4.5]):
   length=.065+.009*(j%3);delta=np.array([length*np.cos(angle),length*np.sin(angle),.095+.012*(j%2)])
   tip=beam(parent,[0,0,.004],delta,f'leafstalk_{cluster}_{j}',radius=.00165,n=5,young=100e6,control=[.015*np.cos(angle),.015*np.sin(angle),.09])
   for leaflet,offset in enumerate([-1.2,0,1.2]):
    angle2=angle+offset;prev=tip
    for q in range(3):
     b=sub(prev,'body',name=f'leaf_{cluster}_{j}_{leaflet}_{q}',pos=v([0,0,0] if q==0 else [.022*np.cos(angle2),.022*np.sin(angle2),0]))
     sub(b,'joint',name=f'leafbend_{cluster}_{j}_{leaflet}_{q}',type='hinge',axis=v([-np.sin(angle2),np.cos(angle2),0]),stiffness='.005',damping='.001',limited='false',armature='1e-8')
     sub(b,'geom',name=f'leaf_surface_{cluster}_{j}_{leaflet}_{q}',type='mesh',mesh=f'plant_leaf_panel_{q}',euler=v([0,0,angle2]),mass='.00012',material='leaf',contype='128',conaffinity='255',solref='.015 1',friction='.35 .001 .0001')
     sub(b,'geom',name=f'leaf_midrib_{cluster}_{j}_{leaflet}_{q}',type='capsule',fromto=v([0,0,.0008,.022*np.cos(angle2),.022*np.sin(angle2),.0008]),size='.00045',rgba='.32 .47 .15 1',mass='0',contype='0',conaffinity='0');prev=b
 # Compound branching: primary terminal fruit plus a secondary fork, with short
 # pedicels. Position all fruit relative to their own crown, not robot targets.
 groups=[('target',.35,[0,1,2],True),('left',.145,[0,1],False),('right',.59,[2,3,4],False)]
 for name,x,ids,isactive in groups:
  anchor=np.array([x,.27,.435]);crown=sub(w,'body',name='crown_'+name,pos=v(anchor))
  sub(crown,'geom',name='crown_surface_'+name,type='ellipsoid',size='.012 .011 .017',pos='0 0 .003',material='stem',contype='128',conaffinity='255')
  leaves(crown,name)
  junction=np.array([x-.008,.16,.46]);shared=beam(crown,[0,0,.009],junction-anchor,'branch_'+name,radius=.0032,n=8,young=120e6,control=[-.012,-.012,.105])
  primary=np.array([x-.055,.10,.405]);stemname='stem_0' if isactive else f'pedicel_{name}_{ids[0]}'
  tip=beam(shared,[0,0,0],primary-junction,stemname,radius=.00155,n=segments,young=80e6,control=[-.035,-.025,-.004])
  if isactive:
   root.find(".//joint[@name='stem_0_0_x']").set('name','stem_0_x');root.find(".//joint[@name='stem_0_0_y']").set('name','stem_0_y')
  fruit(tip,primary,ids[0],ids[0] if isactive else None)
  node=np.array([x+.032,.14,.442]);fork=beam(shared,[0,0,0],node-junction,'secondary_'+name,radius=.002,n=4,young=100e6,control=[.025,.002,-.002])
  for k,ident in enumerate(ids[1:]):
   end=np.array([x+.017+.06*k,.09+.035*k,.398+.025*k]);tip=beam(fork,[0,0,0],end-node,f'pedicel_{name}_{ident}',radius=.00145,n=segments,young=80e6,control=[-.01+.035*k,-.027,-.004]);body=fruit(tip,end,ident,ident if isactive else None)
   if not isactive and ident==4:
    # Smaller immature fruit with matching mass and collision scale.
    scale=.62;mesh=copy.deepcopy(root.find("asset/mesh[@name='strawberry_mesh']"));mesh.set('name','immature_berry_mesh');mesh.set('scale',v([scale]*3));root.find('asset').append(mesh)
    inertial=body.find('inertial');inertial.set('mass',str(float(inertial.get('mass'))*scale**3));inertial.set('pos',v(np.fromstring(inertial.get('pos'),sep=' ')*scale));inertial.set('diaginertia',v(np.fromstring(inertial.get('diaginertia'),sep=' ')*scale**5))
    for g in body.findall('geom'):
     for key in ['pos','size','fromto']:
      if key in g.attrib:g.set(key,v(np.fromstring(g.get(key),sep=' ')*scale))
     if g.get('mesh')=='strawberry_mesh':g.set('mesh','immature_berry_mesh')
     if g.get('material')=='fruit':g.attrib.pop('material');g.set('rgba','.59 .71 .30 1')
 # Joined tissue inside each crown must not collide with itself. Keep crown
 # contacts with robots and external objects, exclude only these attachment pairs.
 contacts=root.find('contact')
 if contacts is None:contacts=sub(root,'contact')
 for cluster in ['target','left','right']:
  roots=[f'leafstalk_{cluster}_{i}_0' for i in range(5)]+[f'branch_{cluster}_0']
  for name in roots:
   sub(contacts,'exclude',body1='crown_'+cluster,body2=name)
   sub(contacts,'exclude',body1='crown_'+cluster,body2=name[:-1]+'1')
  for i,name in enumerate(roots):
   for other in roots[i+1:]:sub(contacts,'exclude',body1=name,body2=other)
 for attached in junction_roots.values():
  for i,name in enumerate(attached):
   for other in attached[i+1:]:
    for a in [0,1]:
     for b in [0,1]:sub(contacts,'exclude',body1=f'{name}_{a}',body2=f'{other}_{b}')
 # Dynamic, force-limited contact probe used only for physical unit experiments.
 b=sub(w,'body',name='test_probe',pos='0 0 0')
 for i,axis in enumerate(np.eye(3)):
  sub(b,'joint',name=f'probe_{i}',type='slide',axis=v(axis),limited='false',damping='.2')
  sub(act,'position',name=f'probe_{i}',joint=f'probe_{i}',kp='250',kv='5',forcerange='-2 2',ctrllimited='false')
 sub(b,'geom',name='probe_surface',type='sphere',size='.012',mass='.025',rgba='.95 .65 .12 1',contype='256',conaffinity='128',solref='.01 1',friction='.4 .002 .0001')
 # Audit hardware and camera subtrees unchanged byte-for-byte.
 original=ET.parse(BASE).getroot();hardware={}
 for name in ['cut_base','catch_base','cutter','catcher']:
  old=original.find(f".//body[@name='{name}']");new=root.find(f".//body[@name='{name}']")
  hardware[name]=old is not None and ET.tostring(old)==ET.tostring(new)
 out=P/tag;out.mkdir(parents=True,exist_ok=True);ET.indent(root);path=out/'scene.xml';path.write_text(ET.tostring(root,encoding='unicode'))
 (out/'model.json').write_text(json.dumps({'model':'Segmented beam equivalent joint stiffness EI/L; not Cosserat/FEM','parameters_status':'Uncalibrated priors; not measured strawberry tissue properties','branches':records,'hardware_unchanged':hardware,'physical_fruits':8,'physical_leaf_panels':135,'limitations':['Leaf panels are coarse hinged surfaces','Fruit is rigid with compliant contacts, no bruising model','Fracture criterion inherited and uncalibrated; not validated here']},indent=2));return path
if __name__=='__main__':print(build())
