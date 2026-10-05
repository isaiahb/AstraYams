from diagnose import *
from scipy.spatial.transform import Rotation
results=[]
rng=np.random.default_rng(12)
for angle in [-45,-25,0,25,45]:
 R=Rotation.from_euler('z',angle,degrees=True).as_matrix()@env.RC;e.arms['cut']['R']=R;arm=e.arms['cut'];best=None
 for k in range(16):
  q0=rng.uniform(arm['limits'][:,0]+.01,arm['limits'][:,1]-.01);q,err=e.ik('cut',np.array(c['targets'][0])+[-.045,0,0],q0,180)
  if err>.001:continue
  initial=q.copy();errors=[]
  # Follow actual approach and retreat goals; do not merely check reset.
  points=[]
  for target in c['targets']:
   t=np.array(target)
   points += [t+[-.045,0,0],t,t+[-.075,0,.035]]
  prior=np.array(c['targets'][0])+[-.045,0,0]
  for goal in points:
   for u in np.linspace(0,1,8):q,loss=e.ik('cut',prior*(1-u)+goal*u,q,60);errors.append(loss)
   prior=goal
  score=max(errors)
  if best is None or score<best['max_residual']:best=dict(angle=angle,initial_q=initial.tolist(),max_residual=score)
  if score<.0001:break
 results.append(best);print(best,flush=True)
(P/'preflight.json').write_text(json.dumps(results,indent=2))
b=e.model.body('catcher').id;print('camera rel cup',e.data.xmat[b].reshape(3,3).T@(e.data.cam_xpos[e.model.camera('catch_wrist_d405').id]-e.data.site_xpos[e.model.site('catcher_center').id]))
