"""Two direct-mounted SO-101 carriages on the front run of the same belt.

Plate separation is a layout parameter. Each plate has its own slide/guide
and belt clamp; the ideal belt constrains equal front travel, without a shelf.
"""
import copy
from scipy.spatial.transform import Rotation


def mount(root, world, upper, cfg, add, vec, quat, append_robot):
    f=cfg['frame'];gap=f['vertical_carriage_spacing_m']
    lower=copy.deepcopy(upper)
    for node in lower.iter():
        if 'name' in node.attrib:node.set('name','lower_'+node.get('name'))
    lower.set('name','lower_lift_carriage')
    j=lower.find('joint');j.set('name','lower_lift_z')
    j.set('range',vec([z-gap for z in f['lift_range_m']]))
    lower.find('inertial').set('mass',str(f['lower_carriage_mass_kg']))
    world.append(lower)
    # Both clamps are on the front belt strand. The passive lower slider has
    # no second actuator: its constraint contributes mass/load to the one drive.
    add(root.find('equality'),'joint',name='front_carriage_belt',
        joint1='lower_lift_z',joint2='lift_z',polycoef=vec([-gap,1,0,0,0]),
        solref='.003 1',solimp='.999 .999 .001')
    # Base +Z stays out of the plate. Roll the whole mount about that normal;
    # 180 degrees reverses the V6 upside-down installation without changing
    # joint calibration or just posing the links to disguise the mounting.
    rot=(Rotation.from_euler('y',f.get('so101_mount_roll_deg',0),degrees=True)
         *Rotation.from_euler('x',-90,degrees=True)
         *Rotation.from_euler('z',-90,degrees=True))
    for side,carriage,plate_name in [('left',upper,'carriage_faceplate'),
                                      ('right',lower,'lower_carriage_faceplate')]:
        plate=carriage.find(f"body[@name='{plate_name}']")
        append_robot(root,plate,'so101',side,cfg)
        robot=plate.find(f"body[@name='{side}_base']")
        # The stock mesh mounting plane is base-local Z=-2.4 mm. Plate face
        # is local Y=+3 mm. These faces coincide; no spacer, adapter or platform.
        robot.set('pos',vec([0,.003+.0024,f['so101_base_center_offset_m']]))
        robot.set('quat',quat(rot))
