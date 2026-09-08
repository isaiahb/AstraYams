#!/usr/bin/env python3
"""Dimensioned visual CAD; original MuJoCo scene remains contact authority.

Build in mm, STEP in mm, body-local STL in metres. No simulation files edited.
"""
from pathlib import Path
import argparse, hashlib, json, math
import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/workcells/machine_tending_cad'
COLORS = {'cast': [0.18,0.23,0.26], 'steel': [0.57,0.62,0.66],
          'bright': [0.76,0.81,0.84], 'dark': [0.055,0.07,0.08],
          'blue': [0.16,0.36,0.43], 'tray': [0.66,0.71,0.73]}
BODY_WORLD_MM = {'world': (0,0,0), 'vise': (320,0,0),
                 'vise_slider': (320,13,30), 'free_peg': (250,-100,4.1),
                 'finished_stock': (320,0,20.1)}


def box(x,y,z,at=(0,0,0),bevel=0):
    part=cq.Workplane('XY').box(x,y,z)
    if bevel: part=part.edges().chamfer(bevel)
    return part.translate(at)


def cylinder_y(radius,length,at):
    return cq.Workplane('XZ').circle(radius).extrude(length).translate(at)


def screw(at, diameter=5):
    # Actual hex recess in a rounded cylindrical socket-head screw.
    head=cq.Workplane('XY').circle(diameter/2).extrude(2)
    head=head.edges('>Z').fillet(.3)
    cut=cq.Workplane('XY').polygon(6,diameter*.53).extrude(1.3).translate((0,0,.8))
    return head.cut(cut).translate(at)


def tray():
    outer=cq.Workplane('XY').box(80,80,14,centered=(True,True,False)).edges('|Z').fillet(3)
    inner=cq.Workplane('XY').box(72,72,12,centered=(True,True,False)).edges('|Z').fillet(2).translate((0,0,4))
    return outer.cut(inner).edges('>Z').fillet(.5)


def build(output=OUT):
    output.mkdir(parents=True,exist_ok=True); objects=[]; assembly=cq.Assembly(name='YAM_contact_machine_tending_visual_reference')
    def add(name,body,shape,color='steel',description=''):
        solid=shape.val()
        if not solid.isValid(): raise ValueError(f'Invalid CAD solid: {name}')
        filename=name+'.stl'; solid.scale(.001).exportStl(str(output/filename),tolerance=.00010,angularTolerance=.20,relative=False)
        bounds=solid.BoundingBox()
        record={'name':name,'body':body,'mesh_path':str((output/filename).relative_to(ROOT)),
                'filename':filename,'units':'m','origin':'original MuJoCo body frame; geometry transform baked',
                'position':[0,0,0],'quaternion':[1,0,0,0],'color':COLORS[color],
                'bounds_m':{'min':[bounds.xmin/1000,bounds.ymin/1000,bounds.zmin/1000],
                            'max':[bounds.xmax/1000,bounds.ymax/1000,bounds.zmax/1000]},
                'description':description,'sha256':hashlib.sha256((output/filename).read_bytes()).hexdigest()}
        objects.append(record)
        # Stocks have 180-degree initial world-Z orientation in the frozen task.
        location=cq.Location(cq.Vector(*BODY_WORLD_MM[body]),cq.Vector(0,0,1),180 if body in ('free_peg','finished_stock') else 0)
        assembly.add(shape,name=name,loc=location,color=cq.Color(*COLORS[color]))
    # Machined base with mounting counterbores, rear actuator extension and relieved edges.
    base=box(90,80,16,(0,0,8),1.2).union(box(82,94,9,(0,65,4.5),1))
    for x in [-35,35]:
        for y in [-29,55,102]:
            hole=cq.Workplane('XY').center(x,y).circle(2.6).extrude(22)
            counter=cq.Workplane('XY').center(x,y).circle(4.6).extrude(4).translate((0,0,6 if y>40 else 12))
            base=base.cut(hole).cut(counter)
    add('vise_machined_base','vise',base,'cast','Chamfered mounting base with six drilled and counterbored holes.')
    for x in [-35,35]:
        for y in [-29,55,102]:add(f'base_socket_screw_{x}_{y}','vise',screw((x,y,6.1 if y>40 else 12.1),7),'dark')
    add('precision_seat','vise',box(28,22,4,(0,0,18),.15),'bright','Top plane remains z=20 mm.')
    # Original stock-facing planes stay exactly y=-7 and moving-local y=-6 mm.
    add('fixed_jaw_carrier','vise',box(50,9,20,(0,-14.5,30),.5),'cast')
    add('fixed_replaceable_jaw_plate','vise',box(50,3,20,(0,-8.5,30),.15),'steel')
    add('moving_jaw_carrier','vise_slider',box(50,9,20,(0,1.5,0),.5),'cast')
    add('moving_replaceable_jaw_plate','vise_slider',box(50,3,20,(0,-4.5,0),.15),'steel')
    for x in [-20,20]:
        add(f'fixed_plate_screw_{x}','vise',screw((x,-13,38),4.5),'dark')
        add(f'moving_plate_screw_{x}','vise_slider',screw((x,0,8),4.5),'dark')
    for x in [-14,14]: add('seat_endstop_'+str(x),'vise',box(6,50,20,(x,0,30),.2),'steel')
    for x in [-35,35]:
        add('ground_guide_rail_'+str(x),'vise',cylinder_y(3.5,102,(x,71,24)),'bright')
        bearing=box(13,20,13,(x,0,-6),1).cut(cylinder_y(3.55,24,(x,12,-6)))
        add('slider_linear_bearing_'+str(x),'vise_slider',bearing,'cast')
    # Rounded powered-cylinder housing, real coaxial bore and visible seals.
    barrel=cylinder_y(14,52,(0,121,30)).cut(cylinder_y(5.1,56,(0,123,30)))
    add('powered_actuator_housing','vise',barrel,'blue','Design reference for existing force-driven motor; no simulated pneumatics.')
    for y in [65,124]:
        cap=box(34,6,34,(0,y,30),2).cut(cylinder_y(5.1,10,(0,y+5,30)))
        add('actuator_endcap_'+str(y),'vise',cap,'cast')
    seal=cylinder_y(7,3,(0,62,30)).cut(cylinder_y(4.05,4,(0,62.5,30)))
    add('actuator_rod_seal','vise',seal,'dark')
    add('moving_piston_rod','vise_slider',cylinder_y(4,82,(0,87,0)),'bright','Attached to actual slider; axis Y; moves continuously with recorded jaw joint.')
    for x in [-12,12]:
        for z in [18,42]:add(f'actuator_tie_rod_{x}_{z}','vise',cylinder_y(1.5,65,(x,128,z)),'bright')
    fitting=cq.Workplane('YZ').polygon(6,7).extrude(7).translate((12,101,30))
    add('actuator_service_fitting','vise',fitting,'bright')
    add('actuator_service_connector','vise',cq.Workplane('YZ').circle(2.6).extrude(7).translate((19,101,30)),'dark')
    # Sheet-style trays with actual rounded lips/corners, aligned to contact-floor heights.
    for name,pos in [('raw',(250,-100,0)),('output',(240,100,0))]:
        add(name+'_formed_metal_tray','world',tray().translate(pos),'tray')
        label=box(26,.7,5,(pos[0],pos[1]-40.2,8),.2)
        add(name+'_tray_identification_plate','world',label,'blue' if name=='raw' else 'dark')
    # Thick tool plate with recessed slots and counterbored mounting pattern.
    table=box(760,540,24,(180,0,-12),3)
    for y in [-230,-190,190,230]:
        slot=cq.Workplane('XY').center(180,y).slot2D(710,3).extrude(-2)
        table=table.cut(slot)
    for x in [-120,20,160,300,440,510]:
        for y in [-230,230]:table=table.cut(cq.Workplane('XY').center(x,y).circle(3).extrude(-12))
    add('fixture_tooling_table','world',table,'cast')
    for name,body in [('raw_stock','free_peg'),('finished_stock','finished_stock')]:
        add(name,body,box(18,14,70,(0,0,35)),'steel','Exact original stock dimensions and bottom origin; collision authority unchanged.')
    assembly.save(str(output/'machine_tending_assembly.step'))
    manifest={'schema_version':1,'purpose':'visual CAD and dimensioned design reference only',
              'contact_authority':'tasks/yam_machine_tending/scene.xml (unchanged)',
              'source':'tools/build_machine_fixture_cad.py','cad_units':'mm','mesh_units':'m',
              'step_file':'machine_tending_assembly.step','step_configuration':'original task reset, slider joint=0; world coordinates in mm',
              'quaternion_convention':'wxyz','objects':objects,
              'dimensions_mm':{'stock':[18,14,70],'stock_grasp_height':54,'seat_world':[320,0,20],
                               'vise_jaw_top_world_z':40,'closed_nominal_gap':14,'slider_travel':[-2,26],
                               'jaw_width':50,'base':[90,80,16],'tray_outer':[80,80,14],'tray_floor_z':4},
              'limitations':['Visual solids are not collision models or manufacturing-validated hardware.',
                             'Cosmetic radii, bearings, actuator and fastener details are engineering illustration.',
                             'No YAM mesh, simulation source, policy or recorded action was modified.']}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'README.md').write_text('# Machine-tending CAD reference\n\nBuild with `/tmp/clonebench-cad-env/bin/python tools/build_machine_fixture_cad.py`. CadQuery constructs dimensioned solids in millimetres. STEP is a named, coloured assembly in millimetres at the original reset configuration. Each STL is exported in metres in its original MuJoCo body frame; read `manifest.json` for attachment, bounds and hashes. World-attached table and tray coordinates are already baked. Stock meshes retain exact 18 × 14 × 70 mm dimensions with the body origin at the bottom.\n\nThe moving rod and jaw assembly attach to `vise_slider`, so recorded slider motion is visible without invented animation. The powered actuator housing is a visual design reference, not a calibrated pneumatic or electric mechanism. Chamfers, counterbores, hex sockets, guide bearings and formed tray rims are CAD geometry.\n\nThe unchanged `tasks/yam_machine_tending/scene.xml` remains the contact and dynamics authority. These visual assets must never replace collision geometry implicitly. Cosmetic geometry may differ at fillets and around housings; no manufacturing tolerances, strength, seals, cutting loads or collision clearances are validated.\n')
    print(json.dumps({'objects':len(objects),'output':str(output),'stl_bytes':sum((output/o['filename']).stat().st_size for o in objects),'step_bytes':(output/'machine_tending_assembly.step').stat().st_size}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=OUT);args=ap.parse_args();build(args.output)
