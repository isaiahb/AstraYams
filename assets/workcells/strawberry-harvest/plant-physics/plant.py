"""Candidate branched beam plant. Parameters are uncalibrated research priors.
No robot/camera/tool geometry changes. Build reads the frozen baseline XML.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np, json, copy, math
P=Path(__file__).resolve().parent; BASE=P.parent/'multi-harvest/scene.xml'
def v(a):return ' '.join(f'{x:.9g}' for x in np.ravel(a))
def sub(p,t,**kw):return ET.SubElement(p,t,{k:str(x) for k,x in kw.items()})
def build(stiffness_scale=1.,segments=5,tag='candidate'):
 root=ET.parse(BASE).getroot();w=root.find('worldbody');eq=root.find('equality');act=root.find('actuator');records=[]
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
 def beam(parent,start,end,name,radius=.0018,n=segments,young=80e6):
  start=np.array(start);end=np.array(end);delta=(end-start)/n;L=np.linalg.norm(delta);t=delta/L
  ax=np.cross(t,[1.,0,0])
  if np.linalg.norm(ax)<.1:ax=np.cross(t,[0,1.,0])
  ax/=np.linalg.norm(ax);ay=np.cross(t,ax);I=np.pi*radius**4/4;E=young*stiffness_scale;k=E*I/L;kt=(E/(2*1.35))*(2*I)/L
  b=parent
  for i in range(n):
   b=sub(b,'body',name=f'{name}_{i}',pos=v(start if i==0 else delta))
   for suffix,axis,kk in [('x',ax,k),('y',ay,k),('twist',t,kt)]:
    sub(b,'joint',name=f'{name}_{i}_{suffix}',type='hinge',axis=v(axis),stiffness=kk,damping=max(.00002,.007*kk),armature='1e-8',limited='false')
   sub(b,'geom',name=f'{name}_{i}_surface',type='capsule',fromto=v([0,0,0,*delta]),size=radius,density='900',material='stem',contype='128',conaffinity='255',friction='.45 .002 .0001',solref='.01 1')
  tip=sub(b,'body',name=name+'_tip',pos=v(delta))
  records.append(dict(name=name,radius_m=radius,length_m=float(L*n),segments=n,young_pa=E,bend_joint_nm_per_rad=k,damping_nms_per_rad=max(.00002,.007*k)))
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
  sub(eq,'weld',name=ename,body1=parent.get('name'),body2=b.get('name'),solref='.002 1',solimp='.999 .9999 .0001')
  return b
 # Three connected lamina panels share boundary widths; no stack-of-discs appearance.
 for q in range(3):
  verts=[];faces=[]
  for i in range(5):
   x=.022*i/4;t=(q*.022+x)/.066;width=max(.0008,.018*np.sin(np.pi*t)**.8)*(1 if i%2==0 else .90)
   for z in [-.0004,.0004]:
    for y in [-width,width]:verts.append([x,y,z])
  for i in range(4):
   a=i*4;b=(i+1)*4
   for aa,bb,cc,dd in [(a,a+1,b+1,b),(a+2,b+2,b+3,a+3),(a,b,b+2,a+2),(a+1,a+3,b+3,b+1)]:faces.extend([[aa,bb,cc],[aa,cc,dd]])
  faces.extend([[0,2,3],[0,3,1],[16,17,19],[16,19,18]])
  sub(root.find('asset'),'mesh',name=f'plant_leaf_panel_{q}',vertex=v(verts),face=' '.join(str(x) for x in np.ravel(faces)))
 def leaves(parent,cluster):
  # Trifoliate leaf groups: three leaflets at the end of each flexible petiole.
  for j,angle in enumerate([-.5,1.7,3.4]):
   delta=np.array([.043*np.cos(angle),.043*np.sin(angle),.03]);tip=beam(parent,[0,0,0],delta,f'leafstalk_{cluster}_{j}',radius=.0009,n=3,young=40e6)
   for leaflet,offset in enumerate([-.9,0,.9]):
    angle2=angle+offset;prev=tip
    for q in range(3):
     b=sub(prev,'body',name=f'leaf_{cluster}_{j}_{leaflet}_{q}',pos=v([0,0,0] if q==0 else [.022*np.cos(angle2),.022*np.sin(angle2),0]))
     sub(b,'joint',name=f'leafbend_{cluster}_{j}_{leaflet}_{q}',type='hinge',axis=v([-np.sin(angle2),np.cos(angle2),0]),stiffness='.0014',damping='.00008',limited='false',armature='1e-8')
     sub(b,'geom',name=f'leaf_surface_{cluster}_{j}_{leaflet}_{q}',type='mesh',mesh=f'plant_leaf_panel_{q}',euler=v([0,0,angle2]),mass='.00012',material='leaf',contype='128',conaffinity='255',solref='.015 1',friction='.35 .001 .0001');prev=b
 # Crown rooted in the trough; common flexible parent transfers branch reactions.
 groups=[('target',[.35,.27,.435],[.35,.16,.51],[(.35,-.09,.355),(.35,0,.355),(.35,.09,.355)],[0,1,2],True),('left',[.145,.27,.435],[.145,.18,.485],[(.11,.135,.387),(.18,.135,.400)],[0,1],False),('right',[.59,.27,.435],[.575,.18,.49],[(.52,.125,.400),(.60,.12,.386),(.67,.155,.374)],[2,3,4],False)]
 for name,anchor,junction,ends,ids,isactive in groups:
  crown=sub(w,'body',name='crown_'+name,pos=v(anchor));junction=np.array(junction);shared=beam(crown,[0,0,0],junction-np.array(anchor),'branch_'+name,radius=.004,n=5,young=120e6)
  leaves(crown,name)
  for end,ident in zip(ends,ids):
   end=np.array(end);stemname='stem_0' if isactive and ident==0 else f'pedicel_{name}_{ident}'
   tip=beam(shared,[0,0,0],end-junction,stemname,radius=.0015 if isactive else .0016,n=segments,young=80e6)
   # reset compatibility names expected by original env, still real beam joints.
   if isactive and ident==0:
    root.find(".//joint[@name='stem_0_0_x']").set('name','stem_0_x');root.find(".//joint[@name='stem_0_0_y']").set('name','stem_0_y')
   fruit(tip,end,ident,ident if isactive else None)
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
 (out/'model.json').write_text(json.dumps({'model':'Segmented beam equivalent joint stiffness EI/L; not Cosserat/FEM','parameters_status':'Uncalibrated priors; not measured strawberry tissue properties','branches':records,'hardware_unchanged':hardware,'physical_fruits':8,'physical_leaf_panels':81,'limitations':['Leaf panels are coarse hinged surfaces','Fruit is rigid with compliant contacts, no bruising model','Fracture criterion inherited and uncalibrated; not validated here']},indent=2));return path
if __name__=='__main__':print(build())
