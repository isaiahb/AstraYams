"""Fixed RGB-camera and encoder adapter for simulated deployment-facing data.

Only the adapter knows MuJoCo. Student policies receive SensorObservation values,
never this rig or the simulator. Camera transforms are fixed at episode reset.
Extrinsics/noise here are engineering assumptions, not hardware calibrations.
"""
from dataclasses import dataclass
import numpy as np
import mujoco
from astrafactory.sensor_contract import simulation_feedback

CAMERA_SPECS=(
 {'name':'front_left','lookat':[.29,-.04,.045],'distance':.38,'azimuth':45.,'elevation':-35.,'fovy':45.},
 {'name':'front_oblique','lookat':[.29,-.04,.045],'distance':.34,'azimuth':135.,'elevation':-35.,'fovy':45.},
)

@dataclass(frozen=True)
class SensorObservation:
    rgb: np.ndarray
    proprio: np.ndarray
    sensor_time_s: float
    image_time_s: float


class FixedCameraRig:
    def __init__(self,model,data,qpos_indices,qvel_indices,size=160,camera_stride=2,seed=0,augment=False):
        self.model=model;self.data=data;self.qpos_indices=np.asarray(qpos_indices);self.qvel_indices=np.asarray(qvel_indices)
        self.size=size;self.camera_stride=camera_stride;self.tick=0;self.cached_rgb=None;self.image_time=None;self.renderer=mujoco.Renderer(model,height=size,width=size);self.cameras=[]
        self.rng=np.random.default_rng(seed+700000);self.augment=augment
        self.visual_sample={'seed':seed,'training_augmentation':augment,'fixed_cameras':[],'camera_hz':25,'control_hz':50,'hardware_assumption':'Two external RGB cameras with fixed calibrated workcell mounts; no hardware connected or calibrated.'}
        for spec in CAMERA_SPECS:
            c=mujoco.MjvCamera();c.type=mujoco.mjtCamera.mjCAMERA_FREE;c.lookat[:]=spec['lookat'];c.distance=spec['distance'];c.azimuth=spec['azimuth'];c.elevation=spec['elevation']
            if augment:
                c.lookat[:]+=self.rng.uniform(-.003,.003,3);c.azimuth+=self.rng.uniform(-1.5,1.5);c.elevation+=self.rng.uniform(-1.5,1.5);c.distance+=self.rng.uniform(-.003,.003)
            self.cameras.append(c);self.visual_sample['fixed_cameras'].append({'name':spec['name'],'lookat_world_m':c.lookat.tolist(),'distance_m':c.distance,'azimuth_deg':c.azimuth,'elevation_deg':c.elevation,'fovy_deg':spec['fovy']})
        self.gain=float(self.rng.uniform(.85,1.15)) if augment else 1.;self.white_balance=self.rng.uniform(.95,1.05,3) if augment else np.ones(3);self.noise_sigma=float(self.rng.uniform(0,2)) if augment else 0.
        self.visual_sample.update(rgb_gain=self.gain,white_balance=self.white_balance.tolist(),noise_sigma_pixel=self.noise_sigma)
        if augment:
            light_gain=self.rng.uniform(.85,1.15,(model.nlight,1));model.light_diffuse[:]=np.clip(model.light_diffuse*light_gain,0,1)
            # RGB-only appearance augmentation, no geometry/contact parameter changes.
            tint=self.rng.uniform(.9,1.1,(model.nmat,3));model.mat_rgba[:,:3]=np.clip(model.mat_rgba[:,:3]*tint,0,1)
            self.visual_sample['light_gain']=light_gain.tolist();self.visual_sample['material_rgb_gain']=tint.tolist()
    def read(self,command_target,previous_action):
        now=float(self.data.time)
        if self.cached_rgb is None or self.tick%self.camera_stride==0:
            images=[]
            for i,camera in enumerate(self.cameras):
                self.model.vis.global_.fovy=CAMERA_SPECS[i]['fovy'];self.renderer.update_scene(self.data,camera=camera);pixels=self.renderer.render().copy()
                if self.augment:
                    pixels=np.clip(pixels.astype(float)*self.gain*self.white_balance+self.rng.normal(0,self.noise_sigma,pixels.shape),0,255).astype(np.uint8)
                images.append(pixels)
                self.visual_sample['fixed_cameras'][i]['rendered_eye_world_m']=np.mean([c.pos for c in self.renderer.scene.camera],axis=0).tolist()
            self.cached_rgb=np.stack(images);self.cached_rgb.setflags(write=False);self.image_time=now
        proprio=simulation_feedback(self.data.qpos[self.qpos_indices],self.data.qvel[self.qvel_indices],command_target,previous_action);proprio.setflags(write=False)
        result=SensorObservation(self.cached_rgb,proprio,now,self.image_time);self.tick+=1;return result
    def close(self):self.renderer.close()


CANONICAL_ARM_Q=np.array([-0.29850640491726016,1.5736120325408245,1.2465021212012741,-1.2436904670777116,-1.3983406417199534e-06,-0.2985000781159127])
VISUAL_RESET_PROFILES={'training':{'xy_m':.018,'shared_yaw_rad':.15,'relative_yaw_rad':.30},'development':{'xy_m':.018,'shared_yaw_rad':.15,'relative_yaw_rad':.30},'rollout_development':{'xy_m':.018,'shared_yaw_rad':.15,'relative_yaw_rad':.30},'final':{'xy_m':.018,'shared_yaw_rad':.15,'relative_yaw_rad':.30}}

def reset_visual_episode(env,seed,profile='training'):
    """visual-reset-v1: fixed robot start independent of randomized objects.

    Canonical q was solved once for world tool pose [.26,-.08,.116], yaw pi.
    It is a literal fixture/start configuration, not recomputed from object pose.
    Object/socket variation is reset-only and never fed to student observations.
    """
    p=VISUAL_RESET_PROFILES[profile];env.specification['curriculum']={'peg_xy_m':p['xy_m'],'socket_xy_m':p['xy_m'],'yaw_rad':p['shared_yaw_rad']};env.reset(seed=seed)
    relative=float(np.random.default_rng(seed+1000000).uniform(-p['relative_yaw_rad'],p['relative_yaw_rad']))
    env.task.goal[3]+=relative;env.model.body_quat[env.task.socket_id]=[np.cos(env.task.goal[3]/2),0,0,np.sin(env.task.goal[3]/2)]
    env.data.qpos[env.qadr[:6]]=CANONICAL_ARM_Q;env.data.qpos[env.qadr[6]]=-.02;env.data.qpos[env.model.joint('joint8').qposadr]=-.02
    env.data.qvel[:]=0.;env.target=env.data.qpos[env.qadr].copy();env.previous_action[:]=0.;mujoco.mj_forward(env.model,env.data);env.reward_function.reset()
    return {'reset_version':'visual-reset-v1','profile':profile,'seed':seed,'fixed_robot_q7':env.data.qpos[env.qadr].tolist(),'realized_peg_position_m':env.task.pick.tolist(),'realized_socket_goal':env.task.goal.tolist(),'relative_socket_yaw_rad':relative,'teacher_preapproach':False}
