"""Opposed front/rear sliders, coupled by an ideal taut 1:1 belt.

Opposite travel is user-confirmed. Mass, ratio, hidden guides and attachment
details remain assumptions. There is no actuator on the counterweight.
"""
import cadquery as cq
from scipy.spatial.transform import Rotation


def cad(cfg, parts):
    # Leave a rear channel in the front shoe. Rear slider tongues use the back
    # extrusion slot, allowing two carriers to pass at the same elevation.
    front = parts['guide_block'].cut(cq.Workplane('XY').box(20.6, 80, 60).translate((0, -40, 0)))
    rear = cq.Workplane('XY').box(50, 23, 30).edges('|Z').fillet(2).translate((0, -33.5, 0))
    tongue = cq.Workplane('XY').box(5.4, 17, 30).translate((0, -13.5, 0))
    r=cfg['frame']['belt_pitch_radius_m']*1000
    wrap=cq.Workplane('XY').circle(r+.6).circle(r).extrude(10).translate((0,0,1))
    half=cq.Workplane('XY').box(2*r,4*r,30).translate((r,0,0))
    return dict(guide_block=front, counter_guide_shoe=rear.union(tongue),
                counter_backplate=parts['carriage_plate'],
                counter_shaft=cq.Workplane('XY').circle(7).extrude(90),
                counter_spacer=cq.Workplane('XY').circle(14).circle(7).extrude(33),
                belt_clamp=cq.Workplane('XY').box(26,22,22).edges('|Y').fillet(2),
                belt_wrap_top=wrap.cut(half),belt_wrap_bottom=wrap.intersect(half),
                pulley_marker=cq.Workplane('XY').box(15,2,.6).translate((10,0,0)))


def assemble(root, world, cfg, piece, add, vec):
    f=cfg['frame'];mass=f['counterweight_mass_kg'];radius=f['payload_diameter_m']/2;thick=f['payload_thickness_m']
    rear=add(world,'body',name='counterweight_carriage')
    add(rear,'joint',name='counterweight_z',type='slide',axis='0 0 1',range=vec(f['counterweight_range_m']),damping=f['counterweight_damping_N_s_m'])
    transverse=mass*(3*radius**2+thick**2)/12
    add(rear,'inertial',mass=mass,pos='0 -.0975 0',diaginertia=vec([transverse,mass*radius**2/2,transverse]))
    # All following mass is included in the explicit carrier mass prior above.
    def solid(name,part,pos,rot=None,color='dark',box=None):
        b=piece(rear,name,part,pos,rot,color=color,box=box)
        for g in b.findall('geom'):
            if g.get('contype')!='0':g.set('contype','8');g.set('conaffinity','7');g.set('mass','0')
        return b
    solid('counterweight_backplate','counter_backplate',[0,-.039,0],box=([f['carriage_width_m'],.006,f['carriage_plate_height_m']],[0,0,0]))
    for i,x in enumerate([-f['guide_spacing_m']/2,f['guide_spacing_m']/2]):
        for j,z in enumerate([-.045,.045]):
            solid(f'counterweight_guide_{i}_{j}','counter_guide_shoe',[x,0,z],color='accent',box=([.050,.023,.030],[0,-.0335,0]))
    rot=Rotation.from_euler('x',90,degrees=True)
    disk=solid('counterweight_disk','circular_payload',[0,-.075,0],rot)
    add(disk,'geom',name='counterweight_disk_contact',type='cylinder',size=vec([radius,thick/2]),pos=vec([0,0,thick/2]),rgba='0 0 0 0',contype='8',conaffinity='7',mass='0')
    solid('counterweight_hub','payload_hub',[0,-.082,0],rot,color='accent')
    solid('counterweight_shaft','counter_shaft',[0,-.036,0],rot,color='metal')
    solid('counterweight_spacer','counter_spacer',[0,-.042,0],rot,color='accent')
    solid('counterweight_belt_clamp','belt_clamp',[.006,-.029,.067],box=([.026,.022,.022],[0,0,0]))
    height_sum=f['carriage_initial_height_m']+f['counterweight_initial_height_m']
    # Joint references are zero. Thus q_rear = height_sum - q_front.
    # Equality constraint forces transfer gravity and inertia between sliders.
    add(root.find('equality'),'joint',name='counterweight_belt',joint1='counterweight_z',joint2='lift_z',polycoef=vec([height_sum,-1,0,0,0]),solref='.003 1',solimp='.999 .999 .001')
