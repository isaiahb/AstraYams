"""Two standard YAM grippers hold independent free tools through contact.
Scripted commissioning is separate from learning. Approximate work-based stem cut.
"""
import sys,copy,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from harvest import *
HERE=Path(__file__).resolve().parent
CUT=np.array([.35,-.09,.35]); BASKET=np.array([.43,-.23,.01])
RC=np.array([[0,0,-1],[0,-1,0],[-1,0,0.]])
RH=np.array([[0,0,1],[0,1,0],[-1,0,0.]])

def build_scene():
    spec={**BASE,'anchor':[.35,-.09,.43],'stem_length':.075,'cutting_work_j':.00008}
    root=ET.parse(build(spec,HERE/'source')).getroot();world=root.find('worldbody');asset=root.find('asset');act=root.find('actuator');eq=root.find('equality')
    world.remove(world.find("body[@name='base']"));act.clear()
    for g in list(world.findall('geom')):
        if g.get('name') in ('bench','ground') or g.get('name','').startswith('neighbor'):world.remove(g)
    src=SOURCE/'tasks/yam_contact_curriculum/scene.xml';original=ET.parse(src).getroot()
    for side,pos,yaw,bit,fbit,other in [('cut',[0,-.12,0],0,2,4,8|16|64),('catch',[.70,-.12,0],np.pi,8,16,2|4|32)]:
        body=copy.deepcopy(original.find('worldbody/body'));body.set('pos',vec(pos));body.set('euler',f'0 0 {yaw}')
        for e in body.iter():
            if 'name' in e.attrib:e.set('name',side+'_'+e.get('name'))
        for g in body.iter('geom'):
            finger='finger_' in g.get('name','')
            visual=g.get('contype')=='0'
            g.set('contype','0' if visual else str(fbit if finger else bit))
            g.set('conaffinity','0' if visual else str(1|other|(32 if side=='cut' else 64) if finger else 1|other))
            if not finger:g.set('material','studio_dark' if g.get('mesh') in ['base','link1','link4','link5','gripper','tip_left','tip_right'] else 'studio_arm')
        body.find(".//site").set('pos','0 0 -.235')
        world.append(body)
        for i in range(1,7):sub(act,'motor',name=f'{side}_motor{i}',joint=f'{side}_joint{i}',ctrlrange='-10 10')
        sub(act,'motor',name=f'{side}_grip',joint=f'{side}_joint7',ctrlrange='-30 30')
        sub(eq,'joint',name=side+'_mimic',joint1=side+'_joint8',joint2=side+'_joint7',polycoef='0 1 0 0 0',solref='.002 1')
    asset.find("material[@name='studio_arm']").set('rgba','.70 .72 .71 1')
    for name,color in [('basket','.23 .36 .24 1'),('floor','.68 .70 .65 1'),('pad','.12 .17 .16 1'),('white','.42 .47 .46 1')]:sub(asset,'material',name=name,rgba=color,specular='.25',shininess='.35')
    # Free handles fit between the unmodified fingers. No equality/weld to robot.
    for name,bit,gripbit in [('cutter',32,4),('catcher',64,16)]:
        b=sub(world,'body',name=name,pos='0 0 1');sub(b,'freejoint',name=name+'_free')
        sub(b,'geom',name=name+'_handle',type='box',size='.025 .009 .030',material='pad',mass='.04',contype=bit,conaffinity=1|gripbit,friction='2.0 .08 .005',condim='6',solref='.002 1')
        # local -Z extends forward from grip; shoulder marks insertion depth.
        sub(b,'geom',name=name+'_shoulder',type='box',pos='0 0 -.03',size='.017 .017 .005',material='tool',mass='.012',contype=bit,conaffinity=1|128)
        sub(b,'geom',name=name+'_shaft',type='box',pos=('0 0 -.066' if name=='cutter' else '0 0 -.047'),size=('.009 .010 .032' if name=='cutter' else '.009 .010 .013'),material='tool',mass='.025',contype=bit,conaffinity=1|128)
        sub(b,'site',name=name+'_center',pos='0 0 -.11',size='.002',rgba='0 0 0 0')
        if name=='cutter':
            # Opposed powered blades, native tool frame. Local X is world vertical.
            for side,sgn in [('left',1),('right',-1)]:
                blade=sub(b,'body',name='shear_'+side,pos=vec([0,sgn*.022,-.11]))
                sub(blade,'joint',name='shear_'+side,type='slide',axis=vec([0,-sgn,0]),range='0 .022',damping='.8',armature='.0001')
                sub(blade,'geom',name='shear_'+side,type='box',size='.0025 .0009 .026',material='steel',mass='.016',contype=32,conaffinity=128|1)
                sub(act,'position',name='shear_'+side,joint='shear_'+side,kp='1400',kv='4',ctrlrange='0 .022',forcerange='-25 25')
        else:
            # At RH local -X is world up. Center site is floor height.
            for j in range(24):
                a=2*np.pi*j/24;y=.041*np.cos(a);z=-.11+.041*np.sin(a)
                sub(b,'geom',name=f'cup_wall_{j}',type='box',pos=vec([-.021,y,z]),size=vec([.023,.003,.041*np.tan(np.pi/24)+.001]),euler=vec([a,0,0]),material='tool',mass='.0015',contype=64,conaffinity=128|1,solref='.015 1')
            for suffix,sgn in [('',1),('_b',-1)]:
                gate=sub(b,'body',name='cup_gate'+suffix)
                sub(gate,'joint',name='cup_gate'+suffix,type='slide',axis=vec([0,sgn,0]),range='0 .065',damping='.4',armature='.0002')
                sub(gate,'geom',name='cup_floor'+suffix,type='box',pos=vec([0,sgn*.021,-.11]),size='.003 .021 .042',material='liner',mass='.0125',contype=64,conaffinity=128|1,solref='.010 1',friction='.15 .001 .0001')
                sub(act,'position',name='gate'+suffix,joint='cup_gate'+suffix,kp='500',kv='4',ctrlrange='0 .065',forcerange='-15 15')
            for z in [-.157,-.063]:
                sub(b,'geom',name='gate_rail_'+str(abs(int(z*1000))),type='capsule',fromto=vec([.007,-.09,z,.007,.09,z]),size='.0025',material='steel',mass='.014',contype=64,conaffinity=128|1)
            sub(b,'geom',name='gate_drive_envelope',type='box',pos='.019 0 -.048',size='.014 .022 .016',material='tool',mass='.035',contype=64,conaffinity=1|128)
    # fruit collision with tools, fingers and basket, cut stem with cutter only.
    root.find(".//geom[@name='cut_stem']").set('contype','128');root.find(".//geom[@name='cut_stem']").set('conaffinity','32')
    root.find(".//geom[@name='berry_collision']").set('contype','128');root.find(".//geom[@name='berry_collision']").set('conaffinity',str(1|32|64))
    for g in root.findall(".//geom"):
        if g.get('name','').startswith('stem_'):g.set('conaffinity','32')
    # Basket: open container, solid contact backing with slatted visible walls.
    basket=sub(world,'body',name='basket',pos=vec(BASKET))
    sub(basket,'geom',name='basket_floor',type='box',pos='0 0 -.003',size='.105 .080 .006',material='liner',contype='1',conaffinity='255',solref='.02 1')
    for axis in [0,1]:
        for sign in [-1,1]:
            p=[0,0,.038];p[axis]=sign*[.105,.08][axis];s=[.109,.084,.038];s[axis]=.004
            sub(basket,'geom',name=f'basket_wall_{axis}_{sign}',type='box',pos=vec(p),size=vec(s),rgba='0 0 0 0',group='3',contype='1',conaffinity='255')
            for j in range(4):
                p[2]=.011+j*.019;s[2]=.004
                sub(basket,'geom',type='box',pos=vec(p),size=vec(s),material='basket',contype='0',conaffinity='0')
    sub(world,'geom',name='table',type='box',pos='.35 -.03 -.035',size='.65 .48 .035',material='white',contype='1',conaffinity='255')
    sub(world,'geom',name='ground',type='plane',pos='0 0 -.75',size='5 5 .1',material='floor',contype='1',conaffinity='255')
    for x in [-.22,.92]:
        for y in [-.43,.35]:sub(world,'geom',type='box',pos=vec([x,y,-.39]),size='.023 .023 .36',material='rail',contype='0',conaffinity='0')
    # Greenhouse arches and repeated crop rows give spatial context without fake backdrop.
    for x in np.linspace(-2,2,7):
        for y in [-1.2,1.5]:sub(world,'geom',type='capsule',fromto=vec([x,y,-.75,x,y,1.6]),size='.012',material='rail',contype='0',conaffinity='0')
        sub(world,'geom',type='capsule',fromto=vec([x,-1.2,1.6,x,.15,2]),size='.012',material='rail',contype='0',conaffinity='0')
        sub(world,'geom',type='capsule',fromto=vec([x,.15,2,x,1.5,1.6]),size='.012',material='rail',contype='0',conaffinity='0')
    # Raise and offset decorative crop trough beyond arm workspace.
    for g in world.findall('geom'):
        if g.get('material')=='soil':g.set('pos','.4 .27 .43')
        if g.get('pos')=='.40 .18 .19':
            g.set('pos','.40 .27 .385');g.set('name','crop_trough')
        if g.get('material')=='leaf':
            p=np.fromstring(g.get('pos'),sep=' ');p[1]+=.10;p[2]+=.17;g.set('pos',vec(p))
    # Serrated, curved leaf surfaces; decorative foliage is deliberately non-contact.
    vv=[[0,0,.003]];ff=[]
    for j in range(40):
        t=2*np.pi*j/40;r=1 if j%2==0 else .87
        vv.append([.046*np.cos(t)*r,.024*np.sin(t)*r,.007*np.cos(t)**2])
    for j in range(40):ff.append([0,j+1,(j+1)%40+1])
    sub(asset,'mesh',name='serrated_leaf',vertex=vec(np.ravel(vv)),face=' '.join(map(str,np.ravel(ff))))
    for j in range(12):
        x=.07+j*.057
        for k in range(3):
            p=[x,.27+(k-1)*.026,.465+.018*np.sin(j*1.3+k)]
            sub(world,'geom',type='mesh',mesh='serrated_leaf',pos=vec(p),euler=vec([.25*np.sin(j),.35*np.cos(j+k),j*2.2+k*2]),material='leaf',contype='0',conaffinity='0')
            sub(world,'geom',type='capsule',fromto=vec([x,.27,.43,*p]),size='.0013',material='stem',contype='0',conaffinity='0')
    for j,x in enumerate([.11,.17,.52,.60,.68]):
        z=.36+.018*np.sin(j)
        # Hang the background fruit clear of the front wall (y=.195).
        sub(world,'geom',name=f'crop_fruit_{j}',type='mesh',mesh='strawberry_mesh',pos=vec([x,.145,z]),material='fruit',contype='0',conaffinity='0')
        # Route over the rim, then down outside; no stem through the wall.
        sub(world,'geom',name=f'crop_stem_over_{j}',type='capsule',fromto=vec([x,.27,.45,x,.145,.45]),size='.0014',material='stem',contype='0',conaffinity='0')
        sub(world,'geom',name=f'crop_stem_drop_{j}',type='capsule',fromto=vec([x,.145,.45,x,.145,z+.027]),size='.0014',material='stem',contype='0',conaffinity='0')
    for g in world.findall('geom'):
        if g.get('fromto') in ['0.12 .18 0 0.12 .18 .23','0.68 .18 0 0.68 .18 .23']:
            x=float(g.get('fromto').split()[0]);g.set('fromto',vec([x,.27,0,x,.27,.34]))
    root.find('visual/global').set('offwidth','1600');root.find('visual/global').set('offheight','1000')
    root.find('visual/headlight').set('diffuse','.15 .15 .15');root.find('visual/headlight').set('ambient','.22 .22 .22')
    for light in world.findall('light'):
        light.set('diffuse','.45 .45 .42' if light.get('name')=='studio_key' else '.23 .25 .27')
    root.find('option').set('iterations','100');root.find('option').set('noslip_iterations','8')
    # Three physical fruits, distinct stems/free joints and independently severable welds.
    for j in [1,2]:
        for original_name in ['stem_0','fruit']:
            obj=copy.deepcopy(world.find("body[@name='"+original_name+"']"))
            pos=np.fromstring(obj.get('pos'),sep=' ');pos[1]+=.09*j;obj.set('pos',vec(pos))
            for el in obj.iter():
                if 'name' in el.attrib:el.set('name',el.get('name')+'_'+str(j))
            world.append(obj)
        sub(eq,'weld',name='stem_integrity_'+str(j),body1='stem_0_'+str(j),body2='fruit_'+str(j),solref='.004 1')
    for g in root.iter('geom'):
        if g.get('name','').startswith('berry_collision'):
            g.set('conaffinity',str(1|4|16|32|64|128))
    # Official I2RT linear_4310 D405 camera assembly and optical-frame transform.
    official=ET.parse(HERE/'references/yam_station_linear_4310_d405.xml').getroot()
    sub(asset,'mesh',name='d405_wrist_linear_4310',file=str(HERE/'references/d405_wrist_linear_4310.stl'))
    for side in ['cut','catch']:
        camera=copy.deepcopy(official.find(".//body[@name='left_camera']"));camera.set('name',side+'_d405_optical')
        inertial=camera.find('inertial');scale=.09/float(inertial.get('mass'));inertial.set('mass','.09');inertial.set('diaginertia',vec(np.fromstring(inertial.get('diaginertia'),sep=' ')*scale))
        geom=camera.find('geom');geom.set('name',side+'_camera_mount');geom.set('material','studio_dark');geom.set('contype','2' if side=='cut' else '8');geom.set('conaffinity',str(1|128))
        # ROS optical +Z forward -> MuJoCo camera -Z forward, +Y up.
        fx=1280/(2*np.tan(np.radians(87/2)));fy=720/(2*np.tan(np.radians(58/2)))
        sub(camera,'camera',name=side+'_wrist_d405',quat='0 1 0 0',resolution='1280 720',sensorsize='.00128 .00072',focalpixel=vec([fx,fy]),principalpixel='0 0')
        world.find(".//body[@name='"+side+"_gripper']").append(camera)
    ET.indent(root);path=HERE/'scene.xml';path.write_text(ET.tostring(root,encoding='unicode'));return path

class MultiEnv(gym.Env):
    metadata={'render_modes':['rgb_array'],'render_fps':25}
    def __init__(self,render_mode=None):
        self.active=0;self.completed=[];self.joint_target_step=.0135;self.render_mode=render_mode;self.model=mujoco.MjModel.from_xml_path(str(build_scene()));self.data=mujoco.MjData(self.model);self.scratch=mujoco.MjData(self.model)
        self.arms={}
        for side,R in [('cut',RC),('catch',RH)]:
            self.arms[side]=dict(q=np.array([self.model.joint(f'{side}_joint{i}').qposadr[0] for i in range(1,7)]),v=np.array([self.model.joint(f'{side}_joint{i}').dofadr[0] for i in range(1,7)]),limits=np.array([self.model.joint(f'{side}_joint{i}').range for i in range(1,7)]),site=self.model.site(side+'_tool_tip').id,R=R,act=np.array([self.model.actuator(f'{side}_motor{i}').id for i in range(1,7)]))
        self.jp=np.zeros((3,self.model.nv));self.jr=self.jp.copy();self.renderer=None
        self.action_space=spaces.Box(-1,1,(8,),dtype=np.float32);self.observation_space=spaces.Box(-np.inf,np.inf,(43,),dtype=np.float32)
    def part(self,name):return name if self.active==0 else name+'_'+str(self.active)
    def target_cut(self):return CUT+np.array([0,.09*self.active,0])
    def ik(self,side,p,q,iterations=30):
        arm=self.arms[side];s=self.scratch;s.qpos[:]=self.data.qpos;q=q.copy()
        for _ in range(iterations):
            s.qpos[arm['q']]=q;mujoco.mj_forward(self.model,s)
            er=np.r_[p-s.site_xpos[arm['site']],.17*rot_error(arm['R'],s.site_xmat[arm['site']].reshape(3,3))]
            if np.linalg.norm(er)<1e-5:break
            mujoco.mj_jacSite(self.model,s,self.jp,self.jr,arm['site']);J=np.r_[self.jp[:,arm['v']],.17*self.jr[:,arm['v']]]
            dq=J.T@np.linalg.solve(J@J.T+np.eye(6)*2e-5,er);q=np.clip(q+np.clip(dq,-.10,.10),arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
        return q,float(np.linalg.norm(er))
    def reset(self,seed=None,options=None):
        super().reset(seed=seed);self.active=0;self.completed=[];self.cycle_start=0.;self.return_origin=None;mujoco.mj_resetData(self.model,self.data);self.steps=0;self.severed=False;self.work=0.;self.damage=0.;self.cut_time=None;self.peak_force=0.;self.basket_frames=0;self.phase='seat gripper-held tools';self.blade=0.;self.gate=0.;self.trace=[]
        for ax in ['x','y']:self.data.qpos[self.model.joint('stem_0_'+ax).qposadr]=self.np_random.uniform(-.02,.02)
        self.desired={'cut':CUT+[-.045,0,0],'catch':CUT+[0,0,-.098]}
        errors={}
        for side in ['cut','catch']:
            arm=self.arms[side];best=None;loss=1e9
            rng=np.random.default_rng(12)
            for k in range(20):
                q0=rng.uniform(arm['limits'][:,0],arm['limits'][:,1]);q,e=self.ik(side,self.desired[side],q0,220)
                if e<loss:best=q;loss=e
                if loss<1e-4:break
            self.data.qpos[arm['q']]=best;arm['target']=best.copy();errors[side]=loss
            for i in [7,8]:self.data.qpos[self.model.joint(f'{side}_joint{i}').qposadr]=-.013
        mujoco.mj_forward(self.model,self.data)
        for side,name in [('cut','cutter'),('catch','catcher')]:
            g=self.model.body(side+'_gripper').id;R=self.data.xmat[g].reshape(3,3);p=self.data.xpos[g]+R@np.array([0,0,-.125]);q=np.zeros(4);mujoco.mju_mat2Quat(q,R.ravel());a=self.model.joint(name+'_free').qposadr[0];self.data.qpos[a:a+7]=np.r_[p,q]
        mujoco.mj_forward(self.model,self.data);self.last_blade=0.;self.errors=errors
        return self.observe(),{'reset_ik_error_m':errors}
    def observe(self):
        d=self.data;m=self.model
        return np.r_[d.qpos[self.arms['cut']['q']],d.qpos[self.arms['catch']['q']],d.qvel[self.arms['cut']['v']],d.qvel[self.arms['catch']['v']],d.site_xpos[m.site(self.part('cut_site')).id],d.site_xpos[m.site('cutter_center').id],d.site_xpos[m.site('catcher_center').id],self.fruit_position(),BASKET,float(self.severed),self.damage,self.blade,self.gate].astype(np.float32)
    def fruit_position(self):
        b=self.model.body(self.part('fruit')).id;return self.data.xpos[b]+self.data.xmat[b].reshape(3,3)@np.array([0,0,-.047])
    def step(self,action):
        a=np.clip(np.asarray(action),-1,1)
        for i,side in enumerate(['cut','catch']):
            self.desired[side]+=a[i*3:i*3+3]*.002;arm=self.arms[side];qnext,_=self.ik(side,self.desired[side],arm['target'],12);arm['target']+=np.clip(qnext-arm['target'],-self.joint_target_step,self.joint_target_step)
        self.blade=float(np.clip(self.blade+a[6]*.001,0,.022));self.gate=float(np.clip(self.gate+a[7]*.001,0,.065))
        bladeids=[self.model.geom('shear_'+s).id for s in ['left','right']];cutid=self.model.geom(self.part('cut_stem')).id
        grasp={'cutter':set(),'catcher':set()};basket_contact=False;cup_contact=False;arm_contact=0
        for _ in range(10):
            for side,arm in self.arms.items():
                self.data.ctrl[arm['act']]=np.clip(180*(arm['target']-self.data.qpos[arm['q']])-14*self.data.qvel[arm['v']]+self.data.qfrc_bias[arm['v']],-10,10)
                self.data.ctrl[self.model.actuator(side+'_grip').id]=25
            for s in ['left','right']:self.data.ctrl[self.model.actuator('shear_'+s).id]=self.blade
            self.data.ctrl[self.model.actuator('gate').id]=self.gate
            self.data.ctrl[self.model.actuator('gate_b').id]=self.gate
            mujoco.mj_step(self.model,self.data);forces=[0.,0.]
            for k,c in enumerate(self.data.contact):
                ids=set(map(int,c.geom));names=[self.model.geom(int(g)).name or '' for g in c.geom];f=np.zeros(6);mujoco.mj_contactForce(self.model,self.data,k,f)
                for bi,b in enumerate(bladeids):
                    if b in ids and cutid in ids:forces[bi]+=abs(f[0])
                if self.part('berry_collision') in names:
                    if any(n.startswith('cup_') for n in names):cup_contact=True;self.peak_force=max(self.peak_force,float(abs(f[0])))
                    if any(n.startswith('basket_') for n in names):basket_contact=True
                for tool,side in [('cutter','cut'),('catcher','catch')]:
                    if tool+'_handle' in names:
                        for finger in ['left','right']:
                            if any(n.startswith(side+'_finger_'+finger) for n in names) and abs(f[0])>.01:grasp[tool].add(finger)
                if any(n.startswith('cut_yam') for n in names) and any(n.startswith('catch_yam') for n in names):arm_contact+=1
            qsum=sum(float(self.data.qpos[self.model.joint('shear_'+s).qposadr][0]) for s in ['left','right']);closing=max(0,qsum-self.last_blade);self.last_blade=qsum
            if not self.severed and min(forces)>.02:
                self.work+=min(forces)*closing;self.damage=min(1,self.work/.00008)
                if self.damage>=1:self.severed=True;self.cut_time=float(self.data.time);self.data.eq_active[self.model.equality(self.part('stem_integrity')).id]=0
        self.steps+=1;p=self.fruit_position();inside=abs(p[0]-BASKET[0])<.095 and abs(p[1]-BASKET[1])<.070 and BASKET[2]+.008<p[2]<BASKET[2]+.080
        self.basket_frames=self.basket_frames+1 if self.severed and inside and basket_contact else 0
        info=dict(time=float(self.data.time),phase=self.phase,severed=self.severed,damage=self.damage,cut_time=self.cut_time,cup_contact=cup_contact,basket_contact=basket_contact,is_success=self.basket_frames>=25,fruit_position=p.tolist(),cutter_position=self.data.site_xpos[self.model.site('cutter_center').id].tolist(),catcher_position=self.data.site_xpos[self.model.site('catcher_center').id].tolist(),grasp_contacts={k:len(v) for k,v in grasp.items()},peak_catch_force_n=self.peak_force,arm_arm_contacts=arm_contact)
        info['active_berry']=self.active;info['berry_success']=info['is_success']
        if info['berry_success'] and self.active not in self.completed:
            self.completed.append(self.active)
            if self.active<2:
                self.active+=1;self.cycle_start=float(self.data.time);self.return_origin={k:v.copy() for k,v in self.desired.items()};self.severed=False;self.damage=0.;self.work=0.;self.cut_time=None;self.basket_frames=0
        info['collected_count']=len(self.completed);info['is_success']=len(self.completed)==3
        info['all_fruit_positions']=[]
        for j in range(3):
            bid=self.model.body('fruit'+('' if j==0 else '_'+str(j))).id
            info['all_fruit_positions'].append((self.data.xpos[bid]+self.data.xmat[bid].reshape(3,3)@np.array([0,0,-.047])).tolist())
        self.trace.append(info)
        return self.observe(),float(info['berry_success'])*10+self.damage, bool(info['is_success']),self.steps>=3500,info
    def render(self):
        if self.renderer is None:self.renderer=mujoco.Renderer(self.model,720,1200)
        cam=mujoco.MjvCamera();cam.lookat[:]=[.35,0,.22];cam.distance=1.45;cam.azimuth=90;cam.elevation=-18
        self.renderer.update_scene(self.data,camera=cam);return self.renderer.render().copy()
    def close(self):
        if self.renderer:self.renderer.close();self.renderer=None
