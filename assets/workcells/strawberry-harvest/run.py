from env_multi import *

def controller(e):
    t=e.data.time-e.cycle_start;cut=e.data.site_xpos[e.model.site(e.part('cut_site')).id].copy();nom=e.target_cut();blade=-1;gate=-1
    c=nom+[-.045,0,0];h=nom+[0,0,-.098]
    # Return above the emptied front crop slots, then approach the next fruit.
    returning=e.active>0 and t<4.5
    if returning:
        u=np.clip(t/4.5,0,1);u=u*u*(3-2*u);c=e.return_origin['cut']*(1-u)+c*u;h=e.return_origin['catch']*(1-u)+h*u;e.phase='return / close cup / next strawberry'
    elif not e.severed:
        e.phase='align catcher / cut strawberry';c=cut;h=cut+[0,0,-.098]
        if t>(5.2 if e.active else .9) and np.linalg.norm(e.data.site_xpos[e.model.site('catcher_center').id]-h)<.006:blade=1
    else:
        dt=e.data.time-e.cut_time;c=nom+[-.075,0,.035];blade=-1
        if dt<.5:e.phase='catch strawberry';h=nom+[0,0,-.098]
        elif dt<4.5:
            e.phase='carry strawberry to basket';u=np.clip((dt-.5)/4.,0,1);u=u*u*(3-2*u);h=(nom+[0,0,-.098])*(1-u)+(BASKET+[0,0,.23])*u
        elif dt<5.4:
            e.phase='lower cup over basket';u=np.clip((dt-4.5)/.9,0,1);h=BASKET+[0,0,.23-.05*u]
        else:
            e.phase='open cup / add to collection';h=BASKET+[0,0,.18]
            if np.linalg.norm(e.data.site_xpos[e.model.site('catcher_center').id]-h)<.012:gate=1
    # Compensate measured tool-to-gripper deflection; tools remain free bodies.
    offset=e.data.site_xpos[e.arms['catch']['site']]-e.data.site_xpos[e.model.site('catcher_center').id]
    e.cup_bias=.92*getattr(e,'cup_bias',np.zeros(3))+.08*np.clip(offset,-.035,.035)
    h=h+e.cup_bias
    return np.r_[np.clip((c-e.desired['cut'])/.002,-1,1),np.clip((h-e.desired['catch'])/.002,-1,1),blade,gate].astype(np.float32)

if __name__=='__main__':
 from PIL import Image
 e=MultiEnv();print(e.reset(seed=1)[1],flush=True);actions=[];qs=[];events=[];old=0
 for i in range(2600):
  a=controller(e);_,_,done,trunc,info=e.step(a);actions.append(a);qs.append(e.data.qpos.copy())
  if i%200==0 or info['collected_count']!=old:print(info,flush=True)
  if info['collected_count']!=old:events.append(info);old=info['collected_count']
  if done or trunc:break
 np.savez_compressed(HERE/'rollout.npz',actions=actions,qpos=qs);(HERE/'trace.json').write_text(json.dumps(e.trace,indent=2));(HERE/'events.json').write_text(json.dumps(events,indent=2));print('FINAL',info,flush=True);e.close()
