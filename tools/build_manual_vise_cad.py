#!/usr/bin/env python3
"""Manual screw-vise CAD variant; no powered assets or simulation files changed.

Author solids in mm. Export body-local STL in metres and a mm STEP assembly.
"""
from pathlib import Path
import argparse,hashlib,json,math
import cadquery as cq
from build_machine_fixture_cad import box,cylinder_y,screw,tray,COLORS,ROOT

OUT=ROOT/'assets/workcells/manual_vise_cad'
FRAMES_MM={'world':(0,0,0),'vise':(320,0,0),'vise_slider':(320,13,30),
           'manual_screw':(320,135,55),'manual_grip_sleeve':(355,157,55),'free_peg':(250,-100,4.1),'finished_stock':(320,0,20.1)}


def build(pedestal_height_mm=40):
    if not 0 <= pedestal_height_mm <= 100: raise ValueError('Pedestal height must be 0–100 mm')
    frames=dict(FRAMES_MM)
    for body in ['vise','vise_slider','manual_screw','manual_grip_sleeve','finished_stock']:
        x,y,z=frames[body];frames[body]=(x,y,z+pedestal_height_mm)
    lift=pedestal_height_mm/1000
    OUT.mkdir(parents=True,exist_ok=True);objects=[];assembly=cq.Assembly(name='Manual_screw_vise_design_reference')
    def add(name,body,shape,color='steel'):
        solid=shape.val();assert solid.isValid(),name
        file=OUT/(name+'.stl');solid.scale(.001).exportStl(str(file),tolerance=.0001,angularTolerance=.20,relative=False)
        b=solid.BoundingBox();objects.append({'name':name,'body':body,'filename':file.name,'mesh_path':str(file.relative_to(ROOT)),
          'units':'m','origin':'body-local, baked vertices','position':[0,0,0],'quaternion':[1,0,0,0],'color':COLORS[color],
          'bounds_m':{'min':[b.xmin/1000,b.ymin/1000,b.zmin/1000],'max':[b.xmax/1000,b.ymax/1000,b.zmax/1000]},
          'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
        loc=cq.Location(cq.Vector(*frames[body]),cq.Vector(0,0,1),180 if body in ('free_peg','finished_stock') else 0)
        assembly.add(shape,name=name,loc=loc,color=cq.Color(*COLORS[color]))
    if pedestal_height_mm:
        pedestal=box(104,185,pedestal_height_mm,(320,47.5,pedestal_height_mm/2),2)
        for x in [280,360]:
            for y in [-27,120]:pedestal=pedestal.cut(cq.Workplane('XY').center(x,y).circle(3).extrude(pedestal_height_mm+1))
        add('fixed_vise_pedestal','world',pedestal,'cast')
    base=box(90,175,12,(0,47.5,6),1.2)
    for x in [-35,35]:
        for y in [-29,65,121]:
            base=base.cut(cq.Workplane('XY').center(x,y).circle(2.6).extrude(15))
            base=base.cut(cq.Workplane('XY').center(x,y).circle(4.3).extrude(4).translate((0,0,8)))
            add(f'mount_screw_{x}_{y}','vise',screw((x,y,8.1),6.5),'dark')
    add('manual_vise_base','vise',base,'cast')
    add('contact_base_riser','vise',box(90,80,4,(0,0,14),.4),'cast')
    add('precision_seat','vise',box(28,22,4,(0,0,18),.15),'bright')
    add('fixed_carrier','vise',box(50,9,20,(0,-14.5,30),.5),'cast')
    add('fixed_replaceable_plate','vise',box(50,3,20,(0,-8.5,30),.15),'steel')
    add('moving_carrier','vise_slider',box(50,9,20,(0,1.5,0),.5),'cast')
    add('moving_replaceable_plate','vise_slider',box(50,3,20,(0,-4.5,0),.15),'steel')
    for x in [-14,14]:add('endstop_'+str(x),'vise',box(6,50,20,(x,0,30),.2),'steel')
    for x in [-35,35]:
        add('guide_rail_'+str(x),'vise',cylinder_y(3.5,102,(x,71,24)),'bright')
        bearing=box(13,20,13,(x,0,-6),.7).cut(cylinder_y(3.55,24,(x,12,-6)))
        add('jaw_bearing_'+str(x),'vise_slider',bearing,'cast')
    # Raised nut bridge keeps the 35 mm crank sweep above the worktop.
    # Bridge extends behind the jaw; first gripper collision clearance is not certified.
    bridge=box(22,14,38,(0,13,13),1).cut(cylinder_y(4.05,18,(0,22,25)))
    add('translating_nut_bridge','vise_slider',bridge,'cast')
    nut=cylinder_y(7,12,(0,19,25)).cut(cylinder_y(3.7,14,(0,20,25)))
    add('leadscrew_nut','vise_slider',nut,'blue')
    # Rear supports: stationary bearing blocks capture the shaft axially.
    for y in [95,119]:
        support=box(28,10,48,(0,y,36),1).cut(cylinder_y(4.05,14,(0,y+7,55)))
        add('fixed_thrust_support_'+str(y),'vise',support,'cast')
        bearing=cylinder_y(7,2,(0,y+6,55)).cut(cylinder_y(4.02,3,(0,y+6.5,55)))
        add('thrust_bearing_'+str(y),'vise',bearing,'dark')
    # Rotating shaft is exported at manual_screw origin; rotation is around local +Y.
    add('lead_screw_shaft','manual_screw',cylinder_y(3.3,122,(0,0,0)),'bright')
    # Real helical CAD ridge, 2 mm pitch, with a rounded triangular reference profile.
    # Construct along Z then rotate to Y; profile is illustrative, not a thread standard.
    helix=cq.Wire.makeHelix(2,82,3.3)
    ridge=cq.Workplane('XZ').moveTo(3.25,-.55).lineTo(4,0).lineTo(3.25,.55).close().sweep(cq.Workplane(obj=helix),isFrenet=True)
    ridge=ridge.rotate((0,0,0),(1,0,0),90).translate((0,-40,0))
    add('helical_thread_pitch_2mm','manual_screw',ridge,'steel')
    for y in [-45,-11]:add('shaft_thrust_collar_'+str(y),'manual_screw',cylinder_y(6,3,(0,y,0)),'bright')
    hub=cylinder_y(8,10,(0,5,0));add('manual_crank_hub','manual_screw',hub,'cast')
    lever=box(35,6,9,(17.5,7,0),1.4).union(cylinder_y(7,6,(35,10,0)))
    add('radial_crank_lever','manual_screw',lever,'blue')
    # Cylindrical grasp pin, 24 mm long and 8 mm diameter. Surface need not be phase-tracked.
    grip=cylinder_y(4,24,(35,34,0)).edges().fillet(.6).cut(cylinder_y(2.05,26,(35,35,0)))
    add('fixed_crank_pin_axle','manual_screw',cylinder_y(1.8,24,(35,34,0)),'bright')
    add('robot_grasp_pin','manual_grip_sleeve',grip.translate((-35,-22,0)),'dark')
    add('grasp_pin_endcap','manual_grip_sleeve',cylinder_y(5,2,(0,14,0)),'bright')
    for name,at in [('raw',(250,-100,0)),('output',(240,100,0))]:add(name+'_tray','world',tray().translate(at),'tray')
    table=box(930,850,24,(335,225,-12),3)
    for y in [-165,-130,580,615]:table=table.cut(cq.Workplane('XY').center(335,y).slot2D(880,3).extrude(-2))
    add('tooling_table','world',table,'cast')
    add('raw_stock','free_peg',box(18,14,70,(0,0,35)))
    add('finished_stock','finished_stock',box(18,14,70,(0,0,35)))
    assembly.save(str(OUT/'manual_vise_assembly.step'))
    spec={'schema_version':1,'status':'proposed mechanical simulation/design reference, not hardware validated',
      'units':'SI unless explicitly labelled','pedestal':{'height_m':lift,'fixed_world_bounds_m':[[.268,-.045,0],[.372,.140,lift]],'collision_proposal':'Add one fixed support under the entire lifted vise in the new task; no alteration of powered task.','seat_world_m':[.320,0,.020+lift]},'lead_screw':{'pitch_m_per_rev':.002,'major_diameter_m':.008,'mean_diameter_assumption_m':.007,
       'axis_world':[0,1,0],'handle_origin_world_m':[.320,.135,.055+lift],'nut_attached_to':'vise_slider','shaft_body':'manual_screw',
       'arrangement':'Axially fixed rotating screw in two fixed thrust-bearing supports; anti-rotation nut translates with jaw on two guide rails.',
       'coupling':'jaw_q_m = initial_jaw_q_m + 0.002/(2*pi) * (screw_theta_rad - initial_theta_rad)',
       'positive_rotation':'Positive right-hand rotation about +Y increases jaw opening; negative closes. Match CAD helix handedness in engine convention before use.',
       'backlash_assumption_m':.0001,'backlash_status':'Explicit modelling proposal; not represented by CAD clearance as a validated tolerance'},
      'support_table':{'world_bounds_m':[[-.130,-.200,-.024],[.800,.650,0]],'proposed_arm_b_base_m':[.320,.500,0],'contact_status':'Visual CAD only; new task must provide matching fixed support collisions.'},
      'handle':{'grip_sleeve_body':'manual_grip_sleeve','sleeve_origin_in_crank_m':[.035,.022,0],'sleeve_hinge_axis_in_crank':[0,1,0],'bearing':'Passive free-spinning grip sleeve on crank pin, no motor or weld to robot','provisional_hinge_damping_nm_s_per_rad':.00001,'provisional_hinge_coulomb_friction_nm':.00001,'bearing_assumption':'Low-friction sleeve bearing; numerical values are provisional and require sensitivity testing. Only radial/axial contact transmission, not commanded orientation tracking.','radius_m':.035,'grasp_pin_diameter_m':.008,'grasp_pin_length_m':.024,
       'pin_center_world_at_zero_m':[.355,.157,.055+lift],'pin_axis':[0,1,0],'sweep_min_z_m':.015+lift,
       'sweep_max_z_m':.095+lift,'note':'Lowest surface includes 5 mm endcap radius; gripper envelope needs separate collision validation.'},
      'travel':{'reference_contact_gap_m':.014,'allowed_jaw_q_m':[-.002,.026],'full_gap_range_m':[.012,.040],
       'recommended_load_gap_m':.020,'near_clamp_start_gap_m':.016,'turns_20_to_14':3,'turns_16_to_14':1,
       'turns_39_to_14':12.5,'short_demo_condition':'A near-clamp initial state must be explicitly declared; do not conceal omitted opening turns.'},
      'force_model_proposal':{'manual_shaft_torque_limit_nm':.020,'equivalent_handle_tangent_force_n':.020/.035,
       'friction_coefficient_assumption':.15,'lead_angle_rad':math.atan(.002/(math.pi*.007)),
       'frictionless_axial_upper_bound_n':2*math.pi*.020/.002,
       'quasistatic_square_thread_axial_estimate_n':.020/(.007/2*math.tan(math.atan(.002/(math.pi*.007))+math.atan(.15))),
       'required_simulation':'Apply contact-derived hand torque to shaft; constrain screw translation to zero and jaw rotation to zero. Use finite torque/friction, joint limits, finite contact stiffness and measured jaw forces. Do not motor the jaw or teleport angle/translation.',
       'limitations':'Square-thread formula is only a provisional estimate; CAD ridge is not a validated thread standard. Add bearing drag and calibrated friction before force claims. Self-locking is not guaranteed from CAD.'},
      'collision_authority':'Original fixed stock/jaw contact faces from tasks/yam_machine_tending/scene.xml; new handle/nut/bridge collisions must be introduced and audited in a separate dual-arm task.',
      'clearance_risks':['Raised nut bridge near first gripper needs full articulated collision checks.','Second-arm base, wrist and all crank angles require reachability/collision checks.','CAD support/rod overlaps describe an assembled mechanism, not collision pairs.'],
      'powered_components':'None: no motor, pneumatic barrel, service line or powered actuator in this CAD variant.'}
    manifest={'schema_version':1,'mesh_units':'m','cad_units':'mm','quaternion_convention':'wxyz','step_file':'manual_vise_assembly.step',
      'body_frames_world_m':{k:[v/1000 for v in p] for k,p in frames.items()},'objects':objects,
      'mechanical_spec':'mechanical_spec.json','configuration':'jaw q=0 (14 mm gap), manual screw theta=0; initial stock yaw pi',
      'source':'tools/build_manual_vise_cad.py','purpose':'Visual/design reference, not a replacement for contact physics'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(OUT/'mechanical_spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    (OUT/'README.md').write_text(f'# Manual screw-vise variant\n\nSeparate design reference: the powered-vise checkpoint is unchanged. A {pedestal_height_mm:g} mm pedestal lifts the entire vise and finished stock; raw stock remains in its original tray. Change this with `--pedestal-height-mm` when regenerating. Build with `/tmp/clonebench-cad-env/bin/python tools/build_manual_vise_cad.py`. STEP uses millimetres; each STL uses metres in its declared body frame. The complete assembly contains a genuine helical CAD ridge at 2 mm pitch, drilled bearing supports, guide bearings, a translating nut bridge and a radial robot-graspable crank.\n\nThe grip sleeve is a separate `manual_grip_sleeve` body with origin (0.035, 0.022, 0) m in the crank frame and a proposed passive Y-axis bearing; the robot need not rotate its wrist with the crank. Low bearing damping/friction are explicit provisional mechanical assumptions. The manual table spans world X −0.130 to 0.800 m and Y −0.200 to 0.650 m, with its top at Z=0.\n\nScrew rotation is axially fixed; the anti-rotation nut and moving jaw translate along Y. Handle centre is world (0.320, 0.135, {0.055+lift:.3f}) m, radius 35 mm. At zero angle the cylindrical 8 mm × 24 mm grasp pin is centred at (0.355, 0.157, {0.055+lift:.3f}) m. A 20 to 14 mm closing stroke needs three turns; a declared 16 to 14 mm near-clamp stroke needs one. Full 39 to 14 mm closing needs 12.5 turns.\n\n`mechanical_spec.json` defines proposed coupling, finite torque, friction and force bounds. None is calibrated hardware evidence. New handle/bridge collision geometry, both arms, all crank angles and nut travel require a separately audited simulation task. No powered actuator or implicit infinite-force drive is included. The original jaw/stock faces remain the reference contact geometry; this CAD is not manufacturing validated.\n')
    print(json.dumps({'objects':len(objects),'stl_bytes':sum((OUT/o['filename']).stat().st_size for o in objects),'output':str(OUT)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--pedestal-height-mm',type=float,default=40);args=parser.parse_args();build(args.pedestal_height_mm)
