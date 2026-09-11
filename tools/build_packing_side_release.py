"""V10 side-actuated net release. Keep its floor above the container bottom.

Starts from V9's preserved contact bench. Offline IK provides commissioning
setpoints, and only finite-torque robot controls move during a trial.
"""
from pathlib import Path
import json,shutil,math
import xml.etree.ElementTree as E
import cadquery as cq
import mujoco as mj
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation
from scipy.optimize import least_squares
from packing_gate_cad import parts
from build_single_pack import vec
ROOT=Path(__file__).resolve().parents[1];OLD=ROOT/'runs/tower-lift-v9';RUN=ROOT/'runs/tower-lift-v10';B=RUN/'gate-bench'
NAMES=['shoulder_pan','shoulder_lift','elbow_flex','wrist_flex','wrist_roll']

def main():
 B.mkdir(parents=True,exist_ok=True);shutil.copytree(OLD/'cad',RUN/'cad',dirs_exist_ok=True)
 m=mj.MjModel.from_xml_path(str(OLD/'so101/scene.xml'));d=mj.MjData(m);d.qpos[:]=np.load(OLD/'so101/initial.npz')['qpos']
 ids=[m.joint('right_'+n).qposadr[0] for n in NAMES];lo=[m.joint('right_'+n).range[0]+.06 for n in NAMES];hi=[m.joint('right_'+n).range[1]-.06 for n in NAMES];sid=m.site('packing_net_center').id
 seed=json.loads((OLD/'gate-bench/build.json').read_text())['low_access_joint_pose']
 def solve(goal,start):
  def fun(q):
   d.qpos[ids]=q;mj.mj_kinematics(m,d)
   return np.r_[100*(d.site_xpos[sid]-goal),3*(d.site_xmat[sid].reshape(3,3)[:,2]-[0,0,1]),.0001*(q-start)]
  r=least_squares(fun,np.clip(start,lo,hi),bounds=(lo,hi),max_nfev=180);fun(r.x);mj.mj_forward(m,d)
  return dict(q=r.x.tolist(),pos=d.site_xpos[sid].copy().tolist(),quat=d.xquat[m.body('right_packing_net').id].copy().tolist(),error_mm=float(np.linalg.norm(d.site_xpos[sid]-goal)*1000),tilt_deg=float(np.rad2deg(np.arccos(d.site_xmat[sid].reshape(3,3)[2,2]))))
 end=solve(np.array([-.195,.171,.608]),np.array(seed));R=Rotation.from_quat(np.array(end['quat'])[[1,2,3,0]]).as_matrix();endpos=np.array(end['pos'])
 # End target: lever opens to 80 degrees. Cam is lateral; the arm advances
 # along the net's X direction, without plunging the net into the container.
 theta=np.deg2rad(80);lever_point=np.array([-.040,0,-.005])+Rotation.from_euler('y',theta-np.pi/2).apply([-.040,.070,0])
 cam=endpos+R@lever_point+R@np.array([.0085,0,0])
 approach=[];start=np.array(end['q'])
 for distance in [.052,.040,.030,.020,.010,0]:
  goal=endpos-R[:,0]*distance;record=solve(goal,start);start=np.array(record['q']);record['distance_m']=distance;approach.append(record)
 root=E.parse(OLD/'gate-bench/scene.xml').getroot();deck=root.find(".//body[@name='pack_deck']")
 # Fixed deck position is unchanged from V9.
 base=mj.MjModel.from_xml_path(str(OLD/'gate-bench/scene.xml'));bd=mj.MjData(base);bd.qpos[:]=np.load(OLD/'gate-bench/initial.npz')['qpos'];mj.mj_forward(base,bd);deckpos=bd.xpos[base.body('pack_deck').id]
 shapes=parts((cam[2]-(deckpos[2]+.008))*1000)
 for name in ['gate_roller_post']:
  cq.exporters.export(shapes[name],str(RUN/'cad'/(name+'.step')));cq.exporters.export(shapes[name],str(RUN/'cad'/(name+'.stl')),tolerance=.08)
  root.find("asset/mesh[@name='"+name+"']").set('file',str(RUN/'cad'/(name+'.stl')))
 trigger=root.find(".//body[@name='right_gate_trigger']");q=Rotation.from_euler('y',-90,degrees=True).as_quat();trigger.set('quat',vec(q[[3,0,1,2]]))
 for name in ['pack_gate_roller_foot','pack_gate_roller_post','pack_gate_roller']:
  b=root.find(".//body[@name='"+name+"']");p=cam-deckpos
  if name.endswith('foot'):p=p.copy();p[0]-=.015;p[2]=.004
  if name.endswith('post'):p=p.copy();p[2]=.008
  b.set('pos',vec(p))
  if name.endswith('roller'):q=Rotation.from_matrix(R).as_quat();b.set('quat',vec(q[[3,0,1,2]]))
  if name.endswith('post'):
   mesh=trimesh.load(RUN/'cad/gate_roller_post.stl',force='mesh');mesh.apply_scale(.001);mesh.density=2700;I=mesh.moment_inertia;ii=b.find('inertial');ii.set('mass',str(mesh.mass));ii.set('pos',vec(mesh.center_mass));ii.set('fullinertia',vec([I[0,0],I[1,1],I[2,2],I[0,1],I[0,2],I[1,2]]))
 E.indent(root);E.ElementTree(root).write(B/'scene.xml',encoding='unicode')
 a=mj.MjModel.from_xml_path(str(B/'scene.xml'));ad=mj.MjData(a);initial=np.load(OLD/'gate-bench/initial.npz');ad.qpos[:]=initial['qpos'];ad.ctrl[:]=initial['ctrl']
 left=json.loads((OLD/'gate-bench/clear-cutter-pose.json').read_text())['q'];qstart=approach[0]
 for side,values in [('left',left),('right',qstart['q'])]:
  for n,q in zip(NAMES,values):ad.qpos[a.joint(side+'_'+n).qposadr[0]]=q;ad.ctrl[a.actuator(side+'_'+n).id]=q
 j=a.joint('right_net_free').qposadr[0];ad.qpos[j:j+7]=[*qstart['pos'],*qstart['quat']]
 j=a.joint('packing_berry_free').qposadr[0];ad.qpos[j:j+7]=[*np.array(qstart['pos'])+[0,0,.055],1,0,0,0]
 mj.mj_forward(a,ad);np.savez_compressed(B/'initial.npz',qpos=ad.qpos,ctrl=ad.ctrl)
 way=[dict(time_s=0,left=left,right=qstart['q']),dict(time_s=1,left=left,right=qstart['q'])]
 for i,r in enumerate(approach[1:]):way.append(dict(time_s=2+i,left=left,right=r['q']))
 way.append(dict(time_s=8,left=left,right=approach[-1]['q']))
 for i,r in enumerate(reversed(approach[:-1])):way.append(dict(time_s=9+i,left=left,right=r['q']))
 way.append(dict(time_s=14,left=left,right=qstart['q']))
 (B/'side-plan.json').write_text(json.dumps(dict(scope=__doc__,waypoints=way),indent=2)+'\n')
 report=dict(scope=__doc__,approach=approach,end_pose=end,cam_center_m=cam.tolist(),lever_clock_deg=-90,nominal_gate_end_angle_deg=80,source='tower-lift-v9',new_cad_instances=json.loads((OLD/'gate-bench/build.json').read_text())['new_cad_instances'],release_ready=False)
 (B/'build.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
