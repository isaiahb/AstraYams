"""Two official YAMs, Rev-C jaw shears, contact-held catcher and deformable net.

Offline setup only. All runtime movement must go through finite motor commands.
"""
import copy,json,argparse,xml.etree.ElementTree as E
from pathlib import Path
import numpy as np,mujoco,trimesh
from scipy.optimize import least_squares
from build_catcher_positioning import ROOT,CAD,F,vec,add,local
from cad_collision import sliced_hulls
SOURCE=ROOT/'tasks/yam_catcher_positioning_v2';OUT=ROOT/'tasks/yam_dual_harvest_v1'

def main():
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'meshes').mkdir(exist_ok=True)
 root=E.parse(SOURCE/'scene.xml').getroot();world=root.find('worldbody');asset=root.find('asset');eq=root.find('equality');contact=root.find('contact')
 src=mujoco.MjModel.from_xml_path(str(SOURCE/'scene.xml'));sd=mujoco.MjData(src);sd.qpos[:]=np.load(SOURCE/'initial.npz')['qpos'];mujoco.mj_forward(src,sd)
 # Plant=1, catcher arm=2, catcher rigid=4, cutter arm and attached tools=8,
 # textile=16. Inter-arm and cross-tool contacts enabled; same-arm proxy contacts
 # remain disabled pending exact collision decomposition of the source meshes.
 for g in root.find(".//body[@name='plant_frame']").iter('geom'):
  if g.get('contype')!='0':g.set('conaffinity','31')
 original=root.find(".//body[@name='base']")
 for g in original.iter('geom'):
  if g.get('contype')!='0':g.set('conaffinity','29')
 robot=copy.deepcopy(original)
 refkeys={'name','joint','joint1','joint2','body','body1','body2','site','site1','site2','tendon','target'}
 for e in robot.iter():
  for k in refkeys & e.attrib.keys():e.set(k,'cut_'+e.get(k))
  if e.tag=='geom' and e.get('contype')!='0':e.set('contype','8');e.set('conaffinity','23')
 robot.set('pos','.65 -.18 0');robot.set('quat','0 0 0 1');world.append(robot)
 for a in list(root.find('actuator')):
  b=copy.deepcopy(a);b.set('name','cut_'+a.get('name'));b.set('joint','cut_'+a.get('joint'));root.find('actuator').append(b)
 for e in list(eq):
  if e.tag=='joint':
   b=copy.deepcopy(e)
   for k in ['name','joint1','joint2']:b.set(k,'cut_'+e.get(k))
   eq.append(b)
 # Exact CAD visual and mass for bolted finger cartridges. No powered scissors.
 spec=json.loads((CAD/'design.json').read_text());mount_masses={}
 for side in ['left','right']:
  tip=robot.find(f".//body[@name='cut_tip_{side}']");offset=np.fromstring(tip.get('pos'),sep=' ')
  mount=add(tip,'body',name='cut_'+side+'_cartridge',pos=vec(-offset));total=0.;first=np.zeros(3);second=np.zeros((3,3))
  for p in [p for p in spec['parts'] if p['group']=='cutter_'+side]:
   source=CAD.parent/'rev-c/right_blade.stl' if p['name']=='right_blade' else CAD/p['file']
   mesh=trimesh.load(source,force='mesh');canonical=mesh.vertices.copy();mesh.vertices=canonical@F/1000
   rho=7800 if 'steel' in p['material'] else 2700 if 'aluminium' in p['material'] else 1100
   mesh.density=rho;prop=mesh.mass_properties;mass=prop.mass;com=prop.center_mass;total+=mass;first+=mass*com;second+=prop.inertia+mass*((com@com)*np.eye(3)-np.outer(com,com))
   path=OUT/'meshes'/('cut_'+p['name']+'.stl');mesh.export(path);nm='cut_'+p['name']
   add(asset,'mesh',name=nm,file=str(path));rgb=[int(p['color'][i:i+2],16)/255 for i in [1,3,5]]
   add(mount,'geom',name=nm+'_visual',type='mesh',mesh=nm,rgba=vec(rgb+[1]),contype='0',conaffinity='0',mass='0')
   # Thin blade contact uses triangle prisms, preserving the hooked notch.
   hulls=[]
   if p['name'].endswith('_blade'):
    zmin,zmax=canonical[:,2].min(),canonical[:,2].max()
    for face in mesh.faces:
     tri=canonical[face]
     if np.max(abs(tri[:,2]-zmax))<1e-5:
      v=np.vstack([np.c_[tri[:,:2],np.full(3,zmin)],np.c_[tri[:,:2],np.full(3,zmax)]])
      try:hulls.append(trimesh.convex.convex_hull(v@F/1000))
      except Exception:pass
   else:
    for hull in sliced_hulls(canonical,mesh.faces):
     hull.vertices=hull.vertices@F/1000;hulls.append(hull)
   if not hulls:raise ValueError(f"No collision volume for {p['name']}")
   for j,h in enumerate(hulls):
    name=f'{nm}_contact_{j}';add(asset,'mesh',name=name,vertex=vec(h.vertices),face=' '.join(map(str,h.faces.ravel())))
    add(mount,'geom',name=name,type='mesh',mesh=name,mass='0',rgba='0 0 0 0',contype='8',conaffinity='23',friction='.3 .001 .0001',solref='.003 1')
  com=first/total;I=second-total*((com@com)*np.eye(3)-np.outer(com,com));add(mount,'inertial',mass=total,pos=vec(com),fullinertia=vec([I[0,0],I[1,1],I[2,2],I[0,1],I[0,2],I[1,2]]));mount_masses[side]=total
 add(robot.find(".//body[@name='cut_gripper']"),'site',name='cut_center',pos=vec(np.array([202,0,0])@F/1000),size='.0006',rgba='0 0 0 0')
 # Calyx surfaces previously had no collision. Each connected sepal component
 # gets a conservative rigid contact envelope on its own fruit body. This is
 # an explicit first approximation, not a claim of calibrated flexible sepals.
 for fruitname in ['primary','secondary_a','secondary_b','green']:
  name=f'fruit_detail_{fruitname}_calyx';gi=src.geom(name).id;k=src.geom_dataid[gi]
  v=src.mesh_vert[src.mesh_vertadr[k]:src.mesh_vertadr[k]+src.mesh_vertnum[k]];faces=src.mesh_face[src.mesh_faceadr[k]:src.mesh_faceadr[k]+src.mesh_facenum[k]]
  rot=np.zeros(9);mujoco.mju_quat2Mat(rot,src.geom_quat[gi]);v=v@rot.reshape(3,3).T+src.geom_pos[gi]
  geo=trimesh.Trimesh(v,faces,process=True);body=root.find(f".//body[@name='fruit_{fruitname}']")
  for j,part in enumerate(geo.split(only_watertight=False)):
   if len(part.vertices)<4:continue
   try:h=part.convex_hull
   except Exception:continue
   nm=f'calyx_contact_{fruitname}_{j}';add(asset,'mesh',name=nm,vertex=vec(h.vertices),face=' '.join(map(str,h.faces.ravel())))
   add(body,'geom',name=nm,type='mesh',mesh=nm,mass='0',rgba='0 0 0 0',contype='1',conaffinity='30',solref='.001 1',solimp='.999 .999 .0001',priority='1')
 # Split the last stalk segment at its midpoint. The released assembly includes
 # distal stem + calyx + original finite-mass berry, preserving fruit orientation.
 parent=root.find(".//body[@name='secondary_b_5']");g=parent.find("geom[@name='secondary_b_5_surface']");end=np.fromstring(g.get('fromto'),sep=' ')[3:];mid=end/2;r=float(g.get('size'));u=end/np.linalg.norm(end)
 # Flat cut faces created by intersecting the original capsule with a halfspace.
 capsule=trimesh.creation.capsule(radius=r,height=np.linalg.norm(end),count=[12,24]).convex_hull;T=trimesh.geometry.align_vectors([0,0,1],u);T[:3,3]=mid;capsule.apply_transform(T)
 distal=add(world,'body',name='cut_branch');add(distal,'freejoint',name='cut_branch_free')
 for name,normal,body,shift in [('proximal_cut_stem',-u,parent,np.zeros(3)),('distal_cut_stem',u,distal,mid)]:
  box=trimesh.creation.box(extents=[.1,.1,.1]);BT=trimesh.geometry.align_vectors([0,0,1],normal);BT[:3,3]=mid+normal*.05;box.apply_transform(BT)
  half=trimesh.boolean.intersection([capsule,box],engine='manifold');half.vertices-=shift;path=OUT/'meshes'/(name+'.stl');half.export(path)
  add(asset,'mesh',name=name,file=str(path));add(body,'geom',name=name,type='mesh',mesh=name,density='850',rgba='.3 .4 .10 1',contype='1',conaffinity='31',solref='.003 1')
 parent.remove(g)
 for b in list(parent):
  if b.tag=='body':parent.remove(b);b.set('pos',vec(np.fromstring(b.get('pos','0 0 0'),sep=' ')-mid));distal.append(b)
 add(eq,'weld',name='stem_integrity',body1='secondary_b_5',body2='cut_branch',relpose=vec(np.r_[mid,1,0,0,0]),solref='.001 1',solimp='.999 .999 .001',torquescale='.03')
 # Faces coincide while intact. Their contact is explicitly restored upon cut.
 add(contact,'exclude',name='intact_cut_faces',body1='secondary_b_5',body2='cut_branch')
 # Deforming woven net: 1D flex capsules. Holes are real, no invisible bowl.
 tool=root.find(".//body[@name='catcher']");tool.remove(tool.find("geom[@name='catcher_net_visual']"))
 for g in tool.iter('geom'):
  if g.get('contype')=='4':g.set('conaffinity','11')
 # Remove textile lump from rigid inertia; give 1.5 g to moving fiber nodes.
 ti=tool.find('inertial');oldmass=float(ti.get('mass'));oldcom=np.fromstring(ti.get('pos'),sep=' ');vals=np.fromstring(ti.get('fullinertia'),sep=' ');oldI=np.array([[vals[0],vals[3],vals[4]],[vals[3],vals[1],vals[5]],[vals[4],vals[5],vals[2]]]);nc=local([[0,0,-10]])[0];newmass=oldmass-.0015;newcom=(oldmass*oldcom-.0015*nc)/newmass
 S=oldI+oldmass*((oldcom@oldcom)*np.eye(3)-np.outer(oldcom,oldcom))-.0015*(np.eye(3)*.015**2+(nc@nc)*np.eye(3)-np.outer(nc,nc));I=S-newmass*((newcom@newcom)*np.eye(3)-np.outer(newcom,newcom));ti.set('mass',str(newmass));ti.set('pos',vec(newcom));ti.set('fullinertia',vec([I[0,0],I[1,1],I[2,2],I[0,1],I[0,2],I[1,2]]))
 points=[[0,0,2.65-28]];rings=4;n=24;edges=[]
 for j in range(1,rings+1):
  rad=j/rings
  for i in range(n):points.append([27*rad*np.cos(i*2*np.pi/n),23*rad*np.sin(i*2*np.pi/n),2.65-28*(1-rad*rad)])
  for i in range(n):
   a=1+(j-1)*n+i;b=1+(j-1)*n+(i+1)%n;edges.append([a,b]);edges.append([0 if j==1 else a-n,a])
   if j>1:edges.append([a-n,b])
 points=local(points);bodies=[];vertices=[];moving=1+(rings-1)*n
 for i,p in enumerate(points):
  if i>=moving:bodies.append('catcher');vertices.append(p)
  else:
   name=f'net_node_{i}';b=add(tool,'body',name=name,pos=vec(p));add(b,'inertial',mass=.0015/moving,pos='0 0 0',diaginertia='1e-11 1e-11 1e-11')
   for k in range(3):add(b,'joint',name=f'{name}_{k}',type='slide',axis=vec(np.eye(3)[k]),damping='0.00001')
   bodies.append(name);vertices.append([0,0,0])
 deform=root.find('deformable')
 if deform is None:deform=add(root,'deformable')
 net=add(deform,'flex',name='catcher_net',dim='1',radius='.0003',body=' '.join(bodies),vertex=vec(vertices),element=' '.join(map(str,np.array(edges).ravel())),rgba='.55 .47 .32 1')
 add(net,'edge',stiffness='60',damping='.015');add(net,'contact',priority='2',margin='.0003',contype='16',conaffinity='9',friction='.5 .001 .0001',solref='.0005 1',solimp='.9999 .9999 .0001',selfcollide='none')
 size=root.find('size')
 if size is None:size=add(root,'size')
 size.set('memory','192M')
 root.find('option').set('noslip_iterations','4');root.find('option').set('timestep','.00025');root.find('option').set('integrator','implicitfast')
 def save():E.indent(root);E.ElementTree(root).write(OUT/'scene.xml',encoding='unicode')
 save();m=mujoco.MjModel.from_xml_path(str(OUT/'scene.xml'));d=mujoco.MjData(m)
 for j in range(src.njnt):
  name=src.joint(j).name;dest=m.joint(name).qposadr[0];start=src.jnt_qposadr[j];count={0:7,1:4,2:1,3:1}[int(src.jnt_type[j])];d.qpos[dest:dest+count]=sd.qpos[start:start+count]
 b=src.body('secondary_b_5').id;adr=m.joint('cut_branch_free').qposadr[0];d.qpos[adr:adr+3]=sd.xpos[b]+sd.xmat[b].reshape(3,3)@mid;d.qpos[adr+3:adr+7]=sd.xquat[b]
 qids=np.array([m.joint(f'cut_joint{i}').qposadr[0] for i in range(1,7)]);vids=np.array([m.joint(f'cut_joint{i}').dofadr[0] for i in range(1,7)]);limits=np.array([m.joint(f'cut_joint{i}').range for i in range(1,7)])
 mujoco.mj_forward(m,d);goal=d.xpos[m.body('cut_branch').id].copy();angle=-np.deg2rad(25);yawR=np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]])
 desired=goal+yawR@np.array([.035,0,0]);R=yawR@np.array([[0,0,1],[0,1,0],[-1,0,0.]])
 sid=m.site('cut_center').id;lo=limits[:,0]+.12;hi=limits[:,1]-.12;rng=np.random.default_rng(19);candidate=None
 def residual(q):
  d.qpos[qids]=q;mujoco.mj_kinematics(m,d);mujoco.mj_comPos(m,d);rot=d.site_xmat[sid].reshape(3,3)
  return np.r_[20*(d.site_xpos[sid]-desired),2*(rot-R).ravel()]
 for _ in range(12):
  res=least_squares(residual,rng.uniform(lo,hi),bounds=(lo,hi),max_nfev=160);err=np.linalg.norm(residual(res.x));score=err+.0005*np.max(abs(d.qfrc_bias[vids]))
  if candidate is None or score<candidate[0]:candidate=(score,res.x.copy(),err)
 _,best,err=candidate;assert err<.025,err;d.qpos[qids]=best
 for j in ['cut_joint7','cut_joint8']:d.qpos[m.joint(j).qposadr[0]]=-.007
 mujoco.mj_forward(m,d);np.savez_compressed(OUT/'initial.npz',qpos=d.qpos)
 report=dict(nq=m.nq,nv=m.nv,source=str(SOURCE),cut_initial_q=best.tolist(),cut_initial_position_error_m=float(np.linalg.norm(d.site_xpos[sid]-desired)),cut_target_world=goal.tolist(),cutter_mount_mass_kg=mount_masses,net_nodes=len(points),net_edges=len(edges),net_mass_kg=.0015,net_edge_stiffness_N_per_m=60,net_edge_damping_Ns_per_m=.015,scope='Two dynamic YAMs. Offline initial pose only. Actual jaw-driven CAD shears with hooked Rev-C counterblade. Clipped CAD contact envelopes; rigid calyx contact envelopes. Same V4 plant, distal stalk capsule split into two pieces joined by an integrity weld. Deformable fiber net, contact-held frame. No learned dual-task result yet. Same-arm self-collision unresolved; inter-arm contacts enabled.',net_parameters='Uncalibrated structural priors; the coarse woven lattice is a task model, not a fitted textile.')
 (OUT/'build.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
