"""Full dynamic V4 plant + official YAM + the actual revision-B catcher CAD.

This task stops before fruit/net contact. Net rest-shape is visual only; no
catching, cutting, tool pickup, or calibrated textile behavior is claimed.
"""
from pathlib import Path
import argparse,copy,json,xml.etree.ElementTree as E
import numpy as np,mujoco,trimesh

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'tasks/yam_catcher_positioning'
PLANT=ROOT/'assets/workcells/strawberry-specimen/surface-study/v4'
ARM=ROOT/'tasks/yam_contact_curriculum/scene.xml';CAD=ROOT/'cad/harvest-tools/rev-b'
def vec(v):return ' '.join(f'{x:.12g}' for x in np.asarray(v).ravel())
def add(p,tag,**kw):return E.SubElement(p,tag,{k:str(v) for k,v in kw.items()})
F=np.array([[0,0,-1],[0,1,0],[1,0,0]])
def local(v):return (np.asarray(v)-[-200,0,-7])@F/1000

def main():
 global OUT
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=OUT);p.add_argument('--comfortable',action='store_true');args=p.parse_args();OUT=args.out.resolve()
 OUT.mkdir(exist_ok=True,parents=True);(OUT/'meshes').mkdir(exist_ok=True)
 root=E.parse(PLANT/'scene.xml').getroot();src=mujoco.MjModel.from_xml_path(str(PLANT/'scene.xml'))
 state=mujoco.MjData(src);z=np.load(PLANT/'initial-state.npz');state.qpos[:]=z['qpos'];mujoco.mj_forward(src,state)
 world=root.find('worldbody');assets=root.find('asset');root.find('actuator').clear()
 for e in list(root.find('contact')):
  if 'probe' in str(e.attrib):root.find('contact').remove(e)
 world.remove(world.find("body[@name='probe']"))
 plant=add(world,'body',name='plant_frame',pos='.25 -.02 .24' if args.comfortable else '.32 .10 .24')
 for b in list(world):
  if b is not plant and b.tag in ['body','geom'] and b.get('name')!='ground':world.remove(b);plant.append(b)
 # Preserve every plant joint. Mask categories: plant=1, robot=2, tool=4.
 for g in plant.iter('geom'):
  if g.get('contype')!='0':g.set('contype','1');g.set('conaffinity','7')
 orig=E.parse(ARM).getroot()
 for a in orig.find('asset'):
  a=copy.deepcopy(a)
  if 'file' in a.attrib:a.set('file',str((ARM.parent/a.get('file')).resolve()))
  if a.get('name') not in {x.get('name') for x in assets}:assets.append(a)
 robot=copy.deepcopy(orig.find('worldbody/body'));robot.set('pos','0 -.30 0');world.append(robot)
 for g in robot.iter('geom'):
  if g.get('contype')!='0':g.set('contype','2');g.set('conaffinity','5')
 for a in orig.find('actuator'):root.find('actuator').append(copy.deepcopy(a))
 equality=root.find('equality')
 if equality is None:equality=add(root,'equality')
 for e in orig.find('equality'):
  if e.tag=='joint':equality.append(copy.deepcopy(e))
 tool=add(world,'body',name='catcher');add(tool,'freejoint',name='catcher_free')
 physical=[];mass_total=0.;first=np.zeros(3);second=np.zeros((3,3));mesh_vertices={}
 design=json.loads((CAD/'design.json').read_text())
 parts=[p for p in design['parts'] if p['group']=='catcher']
 for p in parts:
  geo=trimesh.load(CAD/p['file'],force='mesh');v=geo.vertices.copy();mesh_vertices[p['name']]=v;geo.vertices=local(v)
  geo.density=7800 if 'screw' in p['name'] else 1100
  prop=geo.mass_properties;mass=prop.mass;com=prop.center_mass;inertia=prop.inertia
  mass_total+=mass;first+=mass*com;second+=inertia+mass*((com@com)*np.eye(3)-np.outer(com,com))
  path=OUT/'meshes'/(p['name']+'.stl');geo.export(path);name='catcher_visual_'+p['name']
  add(assets,'mesh',name=name,file=str(path));color=[int(p['color'][i:i+2],16)/255 for i in [1,3,5]]
  add(tool,'geom',name=name,type='mesh',mesh=name,rgba=vec(color+[1]),contype='0',conaffinity='0',mass='0')
 # Nominal textile mass only. Dynamics/shape under fruit load are deferred.
 net=trimesh.load(CAD/'net-pouch.stl',force='mesh');net.vertices=local(net.vertices);path=OUT/'meshes/net.stl';net.export(path)
 add(assets,'mesh',name='catcher_net_visual',file=str(path))
 add(tool,'geom',name='catcher_net_visual',type='mesh',mesh='catcher_net_visual',rgba='.24 .31 .27 1',mass='0',contype='0',conaffinity='0')
 nm=.0015;nc=local([[0,0,-10]])[0];mass_total+=nm;first+=nm*nc;second+=np.eye(3)*nm*.015**2+nm*((nc@nc)*np.eye(3)-np.outer(nc,nc))
 com=first/mass_total;inertia=second-mass_total*((com@com)*np.eye(3)-np.outer(com,com))
 add(tool,'inertial',pos=vec(com),mass=mass_total,fullinertia=vec([inertia[0,0],inertia[1,1],inertia[2,2],inertia[0,1],inertia[0,2],inertia[1,2]]))
 def collision(name,vertices):
  hull=trimesh.convex.convex_hull(local(vertices));add(assets,'mesh',name=name,vertex=vec(hull.vertices),face=' '.join(map(str,hull.faces.ravel())))
  add(tool,'geom',name=name,type='mesh',mesh=name,rgba='0 0 0 0',mass='0',contype='4',conaffinity='3',friction='.8 .003 .0001',condim='4',solref='.002 1')
 vertices=mesh_vertices['catcher_frame'];collision('catcher_handle',vertices[vertices[:,0]<-52])
 for j,(a,b) in enumerate([(-62,-47),(-50,-37),(-40,-28)]):collision('catcher_spine_'+str(j),vertices[(vertices[:,0]>=a)&(vertices[:,0]<=b)])
 # Convex sectors preserve the ring's hole; a single convex hull would seal it.
 ring=np.vstack([vertices[vertices[:,0]>-33],mesh_vertices['net_retaining_ring']]);theta=np.arctan2(ring[:,1],ring[:,0])
 for j in range(24):
  a=-np.pi+(j+.5)*2*np.pi/24;diff=np.arctan2(np.sin(theta-a),np.cos(theta-a));v=ring[abs(diff)<=np.pi/24+.02]
  if len(v)>=4:collision('catcher_rim_'+str(j),v)
 add(tool,'site',name='catcher_center',pos=vec(local([[0,0,3]])[0]),size='.001',rgba='0 0 0 0')
 root.find('option').set('timestep','.0005');root.find('option').set('integrator','implicitfast')
 add(world,'camera',name='overview',pos='.9 -.95 .75',xyaxes='.78 .63 0 -.3 .37 .88')
 E.indent(root);E.ElementTree(root).write(OUT/'scene.xml',encoding='unicode')
 m=mujoco.MjModel.from_xml_path(str(OUT/'scene.xml'));d=mujoco.MjData(m)
 for j in range(src.njnt):
  name=src.joint(j).name
  if name.startswith('probe_'):continue
  dest=m.joint(name).qposadr[0];start=src.jnt_qposadr[j];n={0:7,1:4,2:1,3:1}[int(src.jnt_type[j])];d.qpos[dest:dest+n]=state.qpos[start:start+n]
 qids=np.array([m.joint(f'joint{i}').qposadr[0] for i in range(1,7)]);vids=np.array([m.joint(f'joint{i}').dofadr[0] for i in range(1,7)])
 mujoco.mj_forward(m,d);g=m.geom('berry_secondary_b').id;k=m.geom_dataid[g];verts=m.mesh_vert[m.mesh_vertadr[k]:m.mesh_vertadr[k]+m.mesh_vertnum[k]]
 vv=verts@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g];goal=np.r_[d.xipos[m.body('fruit_secondary_b').id][:2],vv[:,2].min()-.018]
 desired=goal+[0,-.040,-.015];R=np.array([[0,-1,0],[0,0,-1],[1,0,0.]])
 # IK constructs ONE constant initial posture, never commands a rollout.
 from astrafactory.yam_env import rotation_error
 sid=add(robot.find(".//body[@name='gripper']"),'site',name='initial_catcher_center',pos=vec(local([[0,0,3]])[0]),size='.001',rgba='0 0 0 0')
 E.ElementTree(root).write(OUT/'scene.xml',encoding='unicode');old=d.qpos.copy();m=mujoco.MjModel.from_xml_path(str(OUT/'scene.xml'));d=mujoco.MjData(m);d.qpos[:]=old
 sid=m.site('initial_catcher_center').id;jp=np.zeros((3,m.nv));jr=jp.copy();limits=np.array([m.joint(f'joint{i}').range for i in range(1,7)])
 rng=np.random.default_rng(42);best=None;loss=1e9
 for restart in range(40):
  q=rng.uniform(limits[:,0],limits[:,1])
  for _ in range(200):
   d.qpos[qids]=q;mujoco.mj_forward(m,d);normal=d.site_xmat[sid].reshape(3,3)[:,0];err=np.r_[desired-d.site_xpos[sid],.15*(np.array([0,0,1])-normal)]
   if np.linalg.norm(err)<loss:loss=float(np.linalg.norm(err));best=q.copy()
   if loss<1e-5:break
   mujoco.mj_jacSite(m,d,jp,jr,sid);x,y,z=normal;skew=np.array([[0,-z,y],[z,0,-x],[-y,x,0]]);J=np.r_[jp[:,vids],-.15*skew@jr[:,vids]];dq=J.T@np.linalg.solve(J@J.T+np.eye(6)*1e-5,err);q=np.clip(q+np.clip(dq,-.12,.12),limits[:,0]+.001,limits[:,1]-.001)
  if loss<1e-5:break
 if args.comfortable:
  # Offline workspace setup only. Leave room at joint limits and choose a
  # posture with low static holding torque. This is never a rollout controller.
  from scipy.optimize import least_squares
  lo=limits[:,0]+.15;hi=limits[:,1]-.15;candidate=None;rng=np.random.default_rng(15)
  def residual(q):
   d.qpos[qids]=q;mujoco.mj_forward(m,d);normal=d.site_xmat[sid].reshape(3,3)[:,0]
   return np.r_[20*(d.site_xpos[sid]-desired),2*(normal-[0,0,1]),.006*(q-(lo+hi)/2)]
  for _ in range(25):
   result=least_squares(residual,rng.uniform(lo,hi),bounds=(lo,hi),max_nfev=100);residual(result.x)
   error=float(np.linalg.norm(d.site_xpos[sid]-desired));nz=float(d.site_xmat[sid].reshape(3,3)[2,0]);gravity=d.qfrc_bias[vids]
   score=error*100+abs(nz-1)*10+np.max(abs(gravity))*.001
   if candidate is None or score<candidate[0]:candidate=(score,result.x.copy(),error,nz,gravity.copy())
  _,best,loss,nz,gravity=candidate
  assert loss<.001 and nz>.96 and np.max(abs(gravity))<8,(loss,nz,gravity)
 assert loss<.001,loss
 d.qpos[qids]=best
 for j in ['joint7','joint8']:d.qpos[m.joint(j).qposadr[0]]=-.010
 mujoco.mj_forward(m,d);i=m.body('gripper').id;q=m.joint('catcher_free').qposadr[0];d.qpos[q:q+3]=d.xpos[i];d.qpos[q+3:q+7]=d.xquat[i]
 np.savez_compressed(OUT/'initial.npz',qpos=d.qpos)
 (OUT/'build.json').write_text(json.dumps(dict(plant=str(PLANT),CAD=str(CAD),nq=m.nq,nv=m.nv,tool_mass_kg=mass_total,initial_ik_error=loss,target='secondary_b',goal_m=goal.tolist(),initial_joint_positions=best.tolist(),scope='All plant joints retained. Actual CAD visible; rigid ring/handle/spine contact approximations, textile rest shape visual only. Free catcher prepositioned between jaws, held by contact. No pickup or catch claim. Robot self-collision not enabled.'),indent=2)+'\n')
 print((OUT/'build.json').read_text(),flush=True)

if __name__=='__main__':main()
