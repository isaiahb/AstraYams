"""Reconstruct observed side-braced rig; retain uncertain scale and interfaces.

The photographs establish topology, not supplier part numbers or load ratings.
Rig-only and proposed dual-arm payloads are separate physical models.
"""
import numpy as np
import cadquery as cq
from scipy.spatial.transform import Rotation


def cad(cfg,profile):
    f=cfg['frame'];s=f['profile_m']*1000;H=f['height_m']*1000;W=f['width_m']*1000;D=f['depth_m']*1000;Z=f['working_crossbeam_height_m']*1000
    brace=np.hypot(D/2-25,f['brace_attachment_height_m']*1000-s/2)
    p={'upright':profile(H),'crossbar':profile(W-s),'guide':profile(Z-2*s),'foot':profile(D),'side_brace':profile(brace)}
    plate=cq.Workplane('XY').box(f['carriage_width_m']*1000,6,f['carriage_plate_height_m']*1000).edges('|Y').fillet(6)
    for x in [-102,-85,-38,0,38,85,102]:
        for z in [-40,40]:plate=plate.cut(cq.Workplane('XZ').center(x,z).circle(2.6).extrude(8,both=True))
    p['carriage_plate']=plate
    block=cq.Workplane('XY').box(50,56,30).translate((0,7,0)).edges('|Z').fillet(3)
    block=block.cut(cq.Workplane('XY').rect(s+.6,s+.6).extrude(20,both=True))
    for x in [-18,18]:block=block.cut(cq.Workplane('XZ').center(x,0).circle(2).extrude(50,both=True))
    p['guide_block']=block
    tri=cq.Workplane('XY').polyline([(0,0),(42,0),(0,42)]).close().extrude(3)
    for x,y in [(8,8),(28,8),(8,28)]:tri=tri.cut(cq.Workplane('XY').center(x,y).circle(2.6).extrude(4))
    p['corner_plate']=tri
    p['bolt_head']=cq.Workplane('XY').polygon(6,7).extrude(3).cut(cq.Workplane('XY').polygon(6,3).extrude(1.2).translate((0,0,1.8)))
    # Envelope of the round black component seen in the photos. Purpose unknown.
    radius=f['payload_diameter_m']*500;thick=f['payload_thickness_m']*1000
    disk=cq.Workplane('XY').circle(radius).circle(15).extrude(thick).edges('%Circle').fillet(5)
    for a in np.arange(0,360,45):
        recess=cq.Workplane('XY').box(46,5,2).edges('|Z').fillet(2).translate((radius*.62,0,thick-.6)).rotate((0,0,0),(0,0,1),float(a))
        disk=disk.cut(recess)
    p['circular_payload']=disk
    p['payload_hub']=cq.Workplane('XY').circle(25).circle(7).extrude(43)
    # Unmeasured mounting interpretation: a through-shaft and spacer make the
    # payload-to-faceplate load path explicit instead of leaving a visual gap.
    p['payload_shaft']=cq.Workplane('XY').circle(7).extrude(138)
    p['payload_spacer']=cq.Workplane('XY').circle(14).circle(7).extrude(81)
    # The proposed bridge is independent of the photographed test payload.
    p['arm_bridge']=cq.Workplane('XY').box(560,190,8).edges('|Z').fillet(7)
    for x in [-240,-170,170,240]:
        for y in [-45,15]:p['arm_bridge']=p['arm_bridge'].cut(cq.Workplane('XY').center(x,y).circle(3.3).extrude(10,both=True))
    upright=cq.Workplane('XY').box(40,8,86).translate((0,0,0))
    foot=cq.Workplane('XY').box(40,102,8).translate((0,47,39))
    support=upright.union(foot)
    for z in [-26,26]:support=support.cut(cq.Workplane('XZ').center(0,z).circle(3.3).extrude(10,both=True))
    p['bridge_bracket']=support
    if f.get('arm_mount')=='compact_so101':
        # A compact mounting study attached to the observed faceplate. The
        # existing base clamp interface still needs its hardware/fit verified.
        p['arm_bridge']=cq.Workplane('XY').box(360,130,6).edges('|Z').fillet(6)
        for x in [-153,-87,87,153]:
            for y in [-38,38]:
                p['arm_bridge']=p['arm_bridge'].cut(cq.Workplane('XY').center(x,y).slot2D(20,5.5,90).extrude(8,both=True))
        support=cq.Workplane('XY').box(40,6,70)
        support=support.union(cq.Workplane('XY').box(40,114,6).translate((0,54,32)))
        for z in [-25,25]:support=support.cut(cq.Workplane('XZ').center(0,z).circle(2.6).extrude(8,both=True))
        p['bridge_bracket']=support
        p['bridge_web']=cq.Workplane('YZ').polyline([(0,0),(85,0),(0,-60)]).close().extrude(4,both=True)
    p['motor_body']=cq.Workplane('XY').box(57,45,45).edges('|X').fillet(3)
    p['gearhead']=cq.Workplane('XY').box(35,42,42).edges('|X').fillet(3)
    p['motor_foot']=cq.Workplane('XY').box(105,54,4).edges('|Z').fillet(3)
    p['belt_clamp']=cq.Workplane('XY').box(26,8,22).edges('|Y').fillet(2)
    if f.get('counterweighted'):
        from lift_counterweight import cad as counter_cad
        p.update(counter_cad(cfg,p))
        for name in ['payload_shaft','payload_spacer']:p.pop(name)
    return p


def frame(root,world,cfg,kind,piece,add,vec,quat,append_robot):
    f=cfg['frame'];s=f['profile_m'];W=f['width_m'];H=f['height_m'];D=f['depth_m'];Z=f['working_crossbeam_height_m'];X=(W-s)/2
    chassis=add(world,'body',name='lift_frame')
    def beam(name,part,a,b):
        a=np.array(a);b=np.array(b);v=b-a;L=np.linalg.norm(v)
        rot=Rotation.align_vectors([v/L],[[0,0,1]])[0]
        return piece(chassis,name,part,a,rot,box=([s,s,L],[0,0,L/2]))
    for side,x in enumerate([-X,X]):
        beam(f'outer_post_{side}','upright',[x,0,0],[x,0,H])
        beam(f'floor_rail_{side}','foot',[x,-D/2,s/2],[x,D/2,s/2])
        for end,sign in enumerate([-1,1]):
            a=[x,0,f['brace_attachment_height_m']];b=[x,sign*(D/2-.025),s/2]
            beam(f'side_brace_{side}_{end}','side_brace',a,b)
            # Visible connector plates lie in the YZ side plane.
            for loc,label in [(a,'top'),(b,'foot')]:
                dx=np.array([0,0,-1 if label=='top' else 1]);dy=np.array([0,sign if label=='top' else -sign,0])
                r=Rotation.from_matrix(np.column_stack([dx,dy,np.cross(dx,dy)]))
                pos=np.array(loc);pos[0]+=(-1 if side==0 else 1)*.012
                piece(chassis,f'brace_joint_{side}_{end}_{label}','corner_plate',pos,r,color='dark')
    for label,y,z in [('bottom',0,s/2),('front',D/2-s/2,s/2),('rear',-D/2+s/2,s/2),('working',0,Z)]:
        beam('crossbar_'+label,'crossbar',[-X,y,z],[X,y,z])
    for i,x in enumerate([-f['guide_spacing_m']/2,f['guide_spacing_m']/2]):
        beam(f'linear_guide_{i}','guide',[x,0,s],[x,0,Z-s])
    # Small black gussets at each working/bottom crossbeam intersection.
    for i,x in enumerate([-X,-f['guide_spacing_m']/2,f['guide_spacing_m']/2,X]):
        for label,z in [('low',.02),('high',Z-.010)]:
            dx=np.array([1 if x<0 else -1,0,0]);dy=np.array([0,0,1 if label=='low' else -1])
            r=Rotation.from_matrix(np.column_stack([dx,dy,np.cross(dx,dy)]))
            piece(chassis,f'beam_corner_{i}_{label}','corner_plate',[x,.013,z],r,color='dark')
    piece(chassis,'drive_motor_foot','motor_foot',[.051,0,Z+.012],color='metal')
    piece(chassis,'drive_motor_body','motor_body',[.080,0,Z+.037],color='dark',box=([.057,.045,.045],[0,0,0]))
    piece(chassis,'drive_gearhead','gearhead',[.034,0,Z+.037],color='metal',box=([.035,.042,.042],[0,0,0]))
    for i,z in enumerate([.045,Z+.037]):
        pulley=piece(chassis,f'drive_pulley_{i}','pulley',[0,0,z],Rotation.from_euler('y',90,degrees=True),color='dark')
        if f.get('counterweighted'):
            add(pulley,'joint',name=f'belt_pulley_{i}',type='hinge',axis='0 0 1',limited='false',damping='.0002')
            add(pulley,'inertial',pos='0 0 .006',mass='.06',diaginertia='.000008 .000008 .000012')
            piece(pulley,f'drive_pulley_mark_{i}','pulley_marker',[0,0,.012],color='accent')
            r=f['belt_pitch_radius_m']
            add(root.find('equality'),'joint',name=f'belt_pulley_coupling_{i}',joint1=f'belt_pulley_{i}',joint2='lift_z',polycoef=vec([-f['carriage_initial_height_m']/r,1/r,0,0,0]),solref='.003 1',solimp='.999 .999 .001')
            piece(chassis,f'belt_wrap_{i}','belt_wrap_bottom' if i==0 else 'belt_wrap_top',[0,0,z],Rotation.from_euler('y',90,degrees=True),color='dark')
    belt_r=f['belt_pitch_radius_m'] if f.get('counterweighted') else .019
    for i,y in enumerate([-belt_r,belt_r]):
        add(chassis,'geom',name=f'belt_{i}',type='box',size=vec([.005,.0006,(Z+.037-.045)/2]),pos=vec([.006,y,(Z+.037+.045)/2]),rgba='.07 .09 .10 1',contype='0',conaffinity='0')
    carriage=add(world,'body',name='lift_carriage')
    add(carriage,'joint',name='lift_z',type='slide',axis='0 0 1',range=vec(f['lift_range_m']),damping='20',armature='.4')
    add(carriage,'inertial',mass=f['carriage_mass_kg'],pos='0 0 0',diaginertia='.035 .035 .02')
    for i,x in enumerate([-f['guide_spacing_m']/2,f['guide_spacing_m']/2]):
        for j,z in enumerate([-.045,.045]):
            block=piece(carriage,f'carriage_guide_block_{i}_{j}','guide_block',[x,0,z],color='accent')
            # Contact envelopes around each rail keep the open rail channel.
            for k,(a,b) in enumerate([([-.020,0,0],[.004,.035,.03]),([.020,0,0],[.004,.035,.03]),([0,.025,0],[.032,.009,.03])]):
                g=add(block,'geom',type='box',pos=vec(a),size=vec(np.array(b)/2),rgba='0 0 0 0',contype='4',conaffinity='3')
                if f.get('counterweighted'):g.set('mass','0')
    plate=piece(carriage,'carriage_faceplate','carriage_plate',[0,.039,0],color='dark',box=([f['carriage_width_m'],.006,f['carriage_plate_height_m']],[0,0,0]))
    for x in [-.102,-.085,-.038,.038,.085,.102]:
        for z in [-.04,.04]:piece(carriage,f'plate_bolt_{x}_{z}','bolt_head',[x,.045,z],Rotation.from_euler('x',-90,degrees=True),color='metal')
    piece(carriage,'carriage_belt_clamp','belt_clamp',[.006,.029 if f.get('counterweighted') else .026,.067],color='dark',box=([.026,.022 if f.get('counterweighted') else .008,.022],[0,0,0]))
    if kind=='rig' and not f.get('counterweighted'):
        disk=piece(carriage,'circular_payload','circular_payload',[0,-.045,0],Rotation.from_euler('x',90,degrees=True),color='dark')
        add(disk,'geom',type='cylinder',size=vec([f['payload_diameter_m']/2,f['payload_thickness_m']/2]),pos=vec([0,0,f['payload_thickness_m']/2]),rgba='0 0 0 0',contype='4',conaffinity='3')
        piece(carriage,'payload_hub','payload_hub',[0,-.052,0],Rotation.from_euler('x',90,degrees=True),color='accent')
        piece(carriage,'payload_shaft','payload_shaft',[0,.039,0],Rotation.from_euler('x',90,degrees=True),color='metal')
        piece(carriage,'payload_spacer','payload_spacer',[0,.036,0],Rotation.from_euler('x',90,degrees=True),color='accent')
    elif kind=='so101' and f.get('arm_mount')=='stacked_direct_so101':
        from lift_stack import mount
        mount(root,world,carriage,cfg,add,vec,quat,append_robot)
    elif kind!='rig':
        compact=f.get('arm_mount')=='compact_so101' and kind=='so101'
        bridgepos=[0,.116,.064] if compact else [0,.130,.082]
        piece(carriage,'proposed_arm_bridge','arm_bridge',bridgepos,color='metal',box=([.36,.13,.006] if compact else [.56,.19,.008],[0,0,0]))
        for i,x in enumerate([-.085,.085] if compact else [-.065,.065]):
            piece(carriage,f'proposed_bridge_bracket_{i}','bridge_bracket',[x,.045,.026] if compact else [x,.047,.039],color='dark')
            if compact:piece(carriage,f'proposed_bridge_web_{i}','bridge_web',[x,.051,.055],color='dark')
        for side,sign in [('left',-1),('right',1)]:
            rc=cfg['robots'][kind]
            if not compact:piece(carriage,'proposed_'+side+'_adapter','adapter',[sign*rc['base_spacing_m']/2,rc['base_y_m'],.090],color='accent')
            append_robot(root,carriage,kind,side,cfg)
            # Base origins in source files differ; relocate only the known root
            # appended last (adapter is already a separate explicit solid).
            rootbody=list(carriage)[-1]
            rootbody.set('pos',vec([sign*rc['base_spacing_m']/2,rc['base_y_m'],.0694 if compact else .094]))
    add(root.find('actuator'),'position',name='lift_motor',joint='lift_z',kp='8000',kv='180',forcerange=vec([-f['lift_force_limit_N'],f['lift_force_limit_N']]),ctrlrange=vec(f['lift_range_m']))
    if f.get('counterweighted'):
        from lift_counterweight import assemble
        assemble(root,world,cfg,piece,add,vec)
    return carriage
