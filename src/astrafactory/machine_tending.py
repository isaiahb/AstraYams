"""Two-stock machine tending with a physically actuated contact vise.

Machine commands are an explicit scripted interface, separate from robotaction7.
No object attachments or runtime position assignments are used.
"""
import numpy as np
import mujoco
from astrafactory.contact_env import ContactEnv
from astrafactory.yam_env import yaw_matrix,rotation_error


def _contacts(e,part):
    ids={'left':e.model.body('tip_left').id,'right':e.model.body('tip_right').id};out={'left':0.,'right':0.,'vise_fixed':0.,'vise_moving':0.,'other':0.}
    def below(body,root):
        while body:
            if body==root:return True
            body=int(e.model.body_parentid[body])
        return body==root
    for i,c in enumerate(e.data.contact):
        a,b=[int(e.model.geom_bodyid[g]) for g in c.geom]
        other=int(c.geom2) if below(a,part) else int(c.geom1) if below(b,part) else None
        if other is None:continue
        body=int(e.model.geom_bodyid[other]);name=e.model.geom(other).name or '';key='left' if below(body,ids['left']) else 'right' if below(body,ids['right']) else 'vise_fixed' if name=='vise_fixed_jaw' else 'vise_moving' if name=='vise_moving_jaw' else 'other'
        force=np.zeros(6);mujoco.mj_contactForce(e.model,e.data,i,force);out[key]+=float(np.linalg.norm(force[:3]))
    return out


def active_contacts(env):
    f=_contacts(env,env.task.peg_body);return np.array([f['left'],f['right'],f['vise_fixed']+f['vise_moving']+f['other']])


class MachineTendingEnv(ContactEnv):
    def __init__(self,task_dir='tasks/yam_machine_tending',render_mode=None):
        super().__init__(task_dir,render_mode);j=self.model.joint('vise_joint');self.vise_qadr=int(self.model.jnt_qposadr[j.id]);self.vise_vadr=int(self.model.jnt_dofadr[j.id]);self.vise_aid=self.model.actuator('vise_motor').id;self.vise_target_gap=.0125
    @property
    def vise_opening(self):return float(.014+self.data.qpos[self.vise_qadr])
    def command_vise(self,opening_target):
        if not np.isfinite(opening_target) or not .012<=opening_target<=.040:raise ValueError('Vise targetgap must be .012–.040m')
        self.vise_target_gap=float(opening_target)
    def step(self,action):
        action=np.asarray(action,dtype=float)
        if action.shape!=(7,) or not np.isfinite(action).all():raise ValueError('Robot action must contain7 finite values')
        action=np.clip(action,-1,1);self.target=np.clip(self.target+action*self.scales,self.limits[:,0],self.limits[:,1]);peak=0.
        for _ in range(self.frame_skip):
            control=self.kp*(self.target-self.data.qpos[self.qadr])-self.kd*self.data.qvel[self.vadr]+self.data.qfrc_bias[self.vadr];bounds=self.model.actuator_ctrlrange[self.aids];self.data.ctrl[self.aids]=np.clip(control,bounds[:,0],bounds[:,1])
            self.data.ctrl[self.vise_aid]=np.clip(3000*(self.vise_target_gap-self.vise_opening)-30*self.data.qvel[self.vise_vadr],-20,20)
            rawbody=self.task.parts['raw']['body'];self.data.xfrc_applied[rawbody,:]=0.
            if self.task.retention_stage==1:self.data.xfrc_applied[rawbody,0]=1.
            mujoco.mj_step(self.model,self.data);load=0.
            for i in range(self.data.ncon):
                f=np.zeros(6);mujoco.mj_contactForce(self.model,self.data,i,f);load+=np.linalg.norm(f[:3])
            peak=max(peak,float(load))
        self.episode_peak_force=max(self.episode_peak_force,peak);self.steps+=1;info=self.task.evaluate(peak);reward=self.reward_function(action,info);self.previous_action=action.copy();finite=np.isfinite(self.data.qpos).all() and np.isfinite(self.data.qvel).all();unsafe=peak>self.specification['abort_contact_force_n'];done=bool(info['is_success'] or unsafe or not finite);trunc=bool(self.steps>=self.horizon and not done);info.update(task_id=self.specification['id'],sim_time=float(self.data.time),peak_contact_force_n=peak,episode_peak_force_n=self.episode_peak_force,reason='success' if info['is_success'] else 'force_limit' if unsafe else 'nonfinite' if not finite else 'timeout' if trunc else None);return self._observation(),float(reward),done,trunc,info


class MachineTendingTask:
    def __init__(self,env):
        self.env=env;self.sid=env.model.site('tool_tip').id;self.parts={name:{'body':env.model.body(body).id,'site':env.model.site(site).id,'joint':env.model.joint(joint).id} for name,body,site,joint in [('raw','free_peg','peg_tip','peg_free'),('finished','finished_stock','finished_tip','finished_free')]};self.output_center=np.array([.24,.10,.004]);self.seat_position=np.array([.32,0,.020]);self.desired_rotation=yaw_matrix(np.pi);self.force=0.;self.stage=0;self.hold=0;self.was_lifted=False;self.raw_lifted=False;self.finished_lifted=False;self.finished_deposited=False;self.vise_opened=False;self.retention_stage=0;self.retention_pulse_steps=0;self.retention_completed=False;self.select_part('finished')
    def select_part(self,name):
        if name not in self.parts:raise ValueError(name)
        p=self.parts[name];self.part_name=name;self.pid=p['site'];self.peg_body=p['body'];self.peg_joint=p['joint'];self.pa=int(self.env.model.jnt_qposadr[self.peg_joint]);self.pick=self.env.data.site_xpos[self.pid].copy();self.goal=np.r_[self.output_center if name=='finished' else self.seat_position,np.pi]
    def reset(self,rng,options):
        if options:raise ValueError('No runtime state override in scored task')
        e=self.env
        for name,p in self.parts.items():
            pos=self.seat_position+np.array([0,0,.0001]) if name=='finished' else np.r_[np.array([.25,-.10])+rng.uniform(-.010,.010,2),.0041];pa=int(e.model.jnt_qposadr[p['joint']]);e.data.qpos[pa:pa+7]=np.r_[pos,[0,0,0,1]]
        e.data.qpos[e.qadr[:6]]=e.ik(np.array([.32,0,.135]),yaw_matrix(np.pi),initial=np.array([0,1.4,1.4,0,0,0]),restarts=12);e.data.qpos[e.qadr[6]]=-.02;e.data.qpos[e.model.joint('joint8').qposadr]=-.02;e.data.qpos[e.vise_qadr]=0.;e.vise_target_gap=.0125
        self.force=0.;self.stage=0;self.hold=0;self.was_lifted=False;self.raw_lifted=False;self.finished_lifted=False;self.finished_deposited=False;self.vise_opened=False;self.retention_stage=0;self.retention_pulse_steps=0;self.retention_completed=False;mujoco.mj_forward(e.model,e.data);self.select_part('finished');self.desired=e.data.site_xpos[self.sid].copy()
    def error(self):
        e=self.env;return np.r_[self.goal[:3]-e.data.site_xpos[self.pid],rotation_error(self.desired_rotation,e.data.site_xmat[self.pid].reshape(3,3))]
    def distance(self):return float(np.linalg.norm(self.error()[:3])+.02*np.linalg.norm(self.error()[3:]))
    def observe(self):
        e=self.env;return np.r_[e.data.qpos[e.qadr],e.data.qvel[e.vadr],e.target,self.error(),e.previous_action,e.data.qpos[self.pa:self.pa+7],self.force]
    def evaluate(self,force):
        e=self.env;self.force=force;raw=self.parts['raw'];fin=self.parts['finished'];rp=e.data.site_xpos[raw['site']];fp=e.data.site_xpos[fin['site']];rr=e.data.site_xmat[raw['site']].reshape(3,3);fr=e.data.site_xmat[fin['site']].reshape(3,3);rc=_contacts(e,raw['body']);fc=_contacts(e,fin['body']);self.vise_opened|=e.vise_opening>.030
        self.finished_lifted|=bool(fp[2]>.040 and fc['left']>.02 and fc['right']>.02)
        corners=np.array([[x,y,z] for x in [-.009,.009] for y in [-.007,.007] for z in [0,.070]])@fr.T+fp;contained=bool(np.all(np.abs(corners[:,:2]-self.output_center[:2])<.036) and corners[:,2].min()>.002 and corners[:,2].max()<.10);fva=int(e.model.jnt_dofadr[fin['joint']]);finished_ok=contained and np.linalg.norm(e.data.qvel[fva:fva+3])<.02 and fc['left']+fc['right']<.05
        self.finished_deposited|=bool(self.vise_opened and self.finished_lifted and finished_ok);self.raw_lifted|=bool(self.finished_deposited and rp[2]>.025 and rc['left']>.02 and rc['right']>.02)
        rva=int(e.model.jnt_dofadr[raw['joint']]);rvel=float(np.linalg.norm(e.data.qvel[rva:rva+3]));rot=float(np.linalg.norm(rotation_error(self.desired_rotation,rr)));xy=float(np.linalg.norm(rp[:2]-self.seat_position[:2]));seated=xy<.0015 and abs(rp[2]-.020)<.0015 and rot<np.deg2rad(3) and rvel<.01
        bilateral=rc['vise_fixed']>1 and rc['vise_moving']>1;released=rc['left']+rc['right']<.05 and e.data.qpos[e.qadr[6]]<-.015;clear=e.data.site_xpos[self.sid,2]>.13
        valid=self.finished_deposited and finished_ok and self.raw_lifted and seated and bilateral and released and clear and force<80;
        if self.retention_stage==0 and valid:self.retention_stage=1;self.retention_pulse_steps=0
        elif self.retention_stage==1:
            self.retention_pulse_steps+=1
            if self.retention_pulse_steps>=15:self.retention_stage=2;self.retention_completed=True;e.data.xfrc_applied[raw['body'],:]=0.
        self.hold=self.hold+1 if valid and self.retention_stage==2 else 0
        active=rc if self.part_name=='raw' else fc;z=float(e.data.site_xpos[self.pid,2]);self.was_lifted=self.raw_lifted if self.part_name=='raw' else self.finished_lifted
        return {'is_success':self.hold>=50 and self.retention_completed,'retention_stage':self.retention_stage,'retention_pulse_steps':self.retention_pulse_steps,'retention_completed':self.retention_completed,'finished_in_output':finished_ok,'finished_deposited':self.finished_deposited,'finished_lifted':self.finished_lifted,'raw_lifted':self.raw_lifted,'raw_seated':bool(seated),'raw_xy_error_m':xy,'raw_rotation_error_rad':rot,'vise_bilateral_contact':bilateral,'vise_contact_forces_n':{k:rc[k] for k in ['vise_fixed','vise_moving']},'gripper_released':bool(released),'tool_clear':bool(clear),'vise_opening_m':e.vise_opening,'vise_target_gap_m':e.vise_target_gap,'hold_steps':self.hold,'active_part':self.part_name,'left_contact':active['left']>.02,'right_contact':active['right']>.02,'grasp_contacts':active['left']>.02 and active['right']>.02,'was_lifted':self.was_lifted,'peg_z_m':z,'tip_z_m':z,'xy_error_m':float(np.linalg.norm(self.error()[:2])),'orientation_error_rad':float(np.linalg.norm(self.error()[3:])),'peg_speed_m_s':float(np.linalg.norm(e.data.qvel[int(e.model.jnt_dofadr[self.peg_joint]):int(e.model.jnt_dofadr[self.peg_joint])+3])),'stage':self.stage}
