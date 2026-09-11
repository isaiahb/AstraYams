"""V16: form-captured detachable net, based on upstream SO101 finger STEP.

CAD millimetres, canonical frame = net ring centre, +Z up, jaw at -X.
This exports mechanical fit poses, never labels them as a learned/physics replay.
"""
import json,math,shutil
from pathlib import Path
import cadquery as cq
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation as R

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/tower-lift-v16/tool-study'
REF=ROOT/'assets/end-effectors/dockable-net/reference'
CLOSED=.0276
PIVOT=(-141.6,18.8,69.2)

def rounded(w,l,h,r=2):
    return cq.Workplane('XY').box(w,l,h,centered=(True,True,False)).edges('|Z').fillet(r)

def transform(s,rot,pos):
    rv=R.from_matrix(rot).as_rotvec();a=np.linalg.norm(rv)
    if a>1e-9:s=s.rotate((0,0,0),tuple(rv/a),float(np.degrees(a)))
    return s.translate(tuple(pos))

def open_jaw(s,q):
    return s.rotate(PIVOT,(PIVOT[0],PIVOT[1]-1,PIVOT[2]),math.degrees(q-CLOSED))

def build_parts():
    # STEP and corresponding official STL use identical datums (mm vs m).
    fix=cq.importers.importStep(str(REF/'Wrist_Roll_Follower_SO101.step')).val()
    fix=transform(fix,np.array([[0,0,1],[0,-1,0],[1,0,0]]),[-165.949706,-.218214,49])
    jaw=cq.importers.importStep(str(REF/'Moving_Jaw_SO101.step')).val()
    rot=R.from_rotvec(np.array([0,-1,0])*CLOSED).as_matrix()@np.array([[0,-1,0],[0,0,-1],[1,0,0]])
    jaw=transform(jaw,rot,[-141.6,-.1,69.2])
    # An integrated printed seat at each finger tip, not a gripped extra adapter.
    lowpad=rounded(30,18,8,3).translate((-73,0,35))
    uppad=rounded(30,18,8,3).translate((-73,0,57))
    socket_low=rounded(14.3,10.3,5,.75).translate((-73,0,39.85))
    socket_up=rounded(14.3,10.3,5,.75).translate((-73,0,55.15))
    fix=cq.Workplane('XY').newObject([fix]).union(lowpad).cut(socket_low)
    jaw=cq.Workplane('XY').newObject([jaw]).union(uppad).cut(socket_up)
    # Lug shoulders bear on the two pad faces; shallow keys take shear/twist.
    lug=rounded(20,12,14,2).translate((-73,0,43))
    bottom=rounded(14,10,3,.6).translate((-73,0,40))
    top=rounded(14,10,3,.6).translate((-73,0,57))
    ring=cq.Workplane('XY').circle(43).circle(38).extrude(4)
    neck=cq.Workplane('XZ').polyline([(-65,46),(-65,54),(-51,54),(-34,1),(-43,1),(-57,46)]).close().extrude(5,both=True)
    frame=ring.union(neck).union(lug).union(bottom).union(top)
    keeper=cq.Workplane('XY').circle(43).circle(38).extrude(2).translate((0,0,4))
    for a in [45,135,225,315]:
        x,y=40.5*math.cos(math.radians(a)),40.5*math.sin(math.radians(a))
        hole=cq.Workplane('XY').center(x,y).circle(1.3).extrude(8)
        frame=frame.cut(hole);keeper=keeper.cut(hole)
    # A shallow textile rest shape, 16 mm deep. Mechanics remain separate.
    wires=[]
    for swap in [False,True]:
        for off in range(-32,33,8):
            extent=math.sqrt(40.5**2-off**2);pts=[]
            for k in range(17):
                a=-extent+2*extent*k/16;x,y=(off,a) if swap else (a,off)
                pts.append(cq.Vector(x,y,4-16*(1-(x*x+y*y)/40.5**2)+(.3 if swap else -.3)))
            path=cq.Wire.assembleEdges([cq.Edge.makeSpline(pts)])
            wires.append(cq.Workplane(cq.Plane(origin=pts[0],normal=pts[1]-pts[0])).circle(.30).sweep(path).val())
    textile=cq.Workplane('XY').newObject([cq.Compound.makeCompound(wires)])
    # Dock supports the rigid ring only. The wrist can lower 4 mm and retreat
    # from the key while the ring remains on the horseshoe seat.
    notch=cq.Workplane('XY').box(110,16,30).translate((-55,0,0))
    dock=cq.Workplane('XY').circle(47).circle(37).extrude(6).translate((0,0,-6)).cut(notch)
    lip=cq.Workplane('XY').circle(47).circle(44.5).extrude(2).cut(notch)
    dock=dock.union(lip)
    for y in [-33,33]:
        tab=rounded(34,14,6,2).translate((45,y,-6))
        tab=tab.cut(cq.Workplane('XY').center(55,y).circle(2.2).extrude(20,both=True));dock=dock.union(tab)
    # A single bent/printed side support carries the fork above the shelf edge.
    # Coordinates here match the packing CAD view: deck centre (0,-165,-87).
    support=cq.Workplane('YZ').polyline([(-55,-79),(-35,-79),(40,-9),(-40,-9)]).close().extrude(3).translate((53.5,0,0))
    foot=rounded(22,22,4,2).translate((55,-47,-83))
    flange=rounded(20,92,4,2).translate((55,0,-10))
    support=support.union(foot).union(flange)
    for y in [-33,33]:support=support.cut(cq.Workplane('XY').center(55,y).circle(2.2).extrude(20,both=True))
    for x in [49,61]:support=support.cut(cq.Workplane('XY').center(x,-49).circle(2.2).extrude(90,both=True))
    bolt=cq.Workplane('XY').circle(1.2).extrude(6).union(cq.Workplane('XY').circle(2.15).extrude(1.5).translate((0,0,6)))
    return dict(fixed_finger=fix,moving_finger=jaw,net_frame=frame,mesh_keeper=keeper,net_textile=textile,parking_fork=dock,dock_shelf_support=support,mesh_screw=bolt)

def main():
    OUT.mkdir(parents=True,exist_ok=True);cad=OUT/'cad';cad.mkdir(exist_ok=True)
    shapes=build_parts();records=[]
    for name,s in shapes.items():
        solid=s.val();assert solid.isValid(),name
        if name!='net_textile':assert len(s.solids().vals())==1,(name,len(s.solids().vals()))
        cq.exporters.export(s,str(cad/(name+'.step')))
        cq.exporters.export(s,str(cad/(name+'.stl')),tolerance=.12,angularTolerance=.20)
        b=solid.BoundingBox();records.append(dict(name=name,solid_count=len(s.solids().vals()),valid=True,volume_mm3=solid.Volume(),bounds_mm=[b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax]))
        print('Exported',name,flush=True)
    # Original SO101 servo mesh at the preserved wrist datum.
    servo=trimesh.load(ROOT/'assets/robots/so101/upstream/assets/sts3215_03a_v1.stl')
    servo.apply_scale(1000)
    rg=np.array([[0,0,-1],[0,1,0],[1,0,0]])
    matrix=np.eye(4);matrix[:3,:3]=rg@R.from_euler('x',-90,degrees=True).as_matrix()
    matrix[:3,3]=[-141.6,.1,56.7];servo.apply_transform(matrix);servo.export(cad/'servo.stl')
    # Reuse shelf/container solids already made for this project.
    src=ROOT/'runs/tower-lift-v15/cad'
    fallback=None
    if not (src/'pack_clamshell.step').exists():
        from packing_shelf_cad import parts
        fallback=parts(10,60)
    for name in ['pack_clamshell','pack_lid','pack_carrier','pack_deck','pack_liner']:
        shapes[name]=fallback[name] if fallback else cq.importers.importStep(str(src/(name+'.step')))
        for ext in ['step','stl']:
            if fallback:cq.exporters.export(shapes[name],str(cad/(name+'.'+ext)))
            else:shutil.copy2(src/(name+'.'+ext),cad/(name+'.'+ext))
    # Move the carrier pull loop beyond the deck edge so the lower finger
    # can actually reach underneath it without intersecting the shelf.
    original=shapes['pack_carrier']
    trim=cq.Workplane('XY').box(200,100,40).translate((0,154,5))
    handle=rounded(46,48,8,3).translate((0,123,1)).cut(rounded(36,38,12,2).translate((0,123,-1)))
    shapes['pack_carrier']=original.cut(trim).union(handle)
    for ext in ['step','stl']:cq.exporters.export(shapes['pack_carrier'],str(cad/('pack_carrier.'+ext)))
    assembly=cq.Assembly(name='V16_dockable_net')
    for name in ['fixed_finger','moving_finger','net_frame','mesh_keeper','net_textile']:assembly.add(shapes[name],name=name)
    for k,a in enumerate([45,135,225,315]):
        assembly.add(shapes['mesh_screw'].translate((40.5*math.cos(math.radians(a)),40.5*math.sin(math.radians(a)),0)),name='screw_'+str(k))
    assembly.save(str(cad/'tool-assembly.step'))
    # Exact BRep checks around the rotary release and 4 mm lower-seat escape.
    checks=[]
    def interference(label,a,b):
        v=a.val().intersect(b.val()).Volume();checks.append(dict(check=label,overlap_mm3=v));return v
    interference('closed fixed finger / net',shapes['fixed_finger'],shapes['net_frame'])
    for q in np.linspace(CLOSED,.55,9):
        interference(f'net / moving finger q={q:.4f}',open_jaw(shapes['moving_finger'],q),shapes['net_frame'])
    for dz in np.linspace(0,-4,5):
        interference(f'dock release lower jaw dz={dz:.1f}',shapes['fixed_finger'].translate((0,0,dz)),shapes['net_frame'])
        interference(f'dock release upper jaw dz={dz:.1f}',open_jaw(shapes['moving_finger'],.55).translate((0,0,dz)),shapes['net_frame'])
    interference('dock / net frame',shapes['parking_fork'],shapes['net_frame'])
    interference('dock / mesh',shapes['parking_fork'],shapes['net_textile'])
    # After lowering clear of the key, retreat along -X.
    for dx in [-5,-15,-30,-55]:
        interference(f'lower finger retreat {dx} mm',shapes['fixed_finger'].translate((dx,0,-4)),shapes['net_frame'])
        interference(f'upper finger retreat {dx} mm',open_jaw(shapes['moving_finger'],.55).translate((dx,0,-4)),shapes['net_frame'])
    # Parked net, side-support and supported carrier: sampled CAD fits.
    carrier=shapes['pack_carrier'].translate((0,-165,-83))
    deck=shapes['pack_deck'].translate((0,-165,-87))
    box=shapes['pack_clamshell'].translate((0,-165,-78.5))
    interference('dock support / clamshell',shapes['dock_shelf_support'],box)
    interference('dock support / carrier',shapes['dock_shelf_support'],carrier)
    def handling(s):return s.rotate((0,0,0),(0,0,1),-90).translate((0,-78,-125))
    interference('handle approach lower finger / deck',handling(shapes['fixed_finger']),deck)
    interference('handle approach lower finger / carrier',handling(shapes['fixed_finger']),carrier)
    interference('handle approach lower finger / box',handling(shapes['fixed_finger']),box)
    interference('handle approach upper finger / carrier',handling(open_jaw(shapes['moving_finger'],-.04)),carrier)
    # Opposed keys must genuinely block a lateral slide with jaws closed.
    blockers=[]
    for direction in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0)]:
        shifted=shapes['net_frame'].translate(direction)
        vol=sum(shifted.val().intersect(shapes[n].val()).Volume() for n in ['fixed_finger','moving_finger'])
        blockers.append(dict(direction_mm=direction,overlap_mm3=vol))
    report=dict(revision='V16 dockable net',coordinate_system='mm; net rim at z=0; wrist approaches from -X',jaw_closed_rad=CLOSED,jaw_open_rad=.55,jaw_pivot_mm=PIVOT,key_clearance_per_side_mm=.15,key_depth_mm=3,lower_escape_mm=4,net_opening_mm=76,mesh_depth_mm=16,checks=checks,shear_blocking=blockers,
      scope='Exact CAD interference and obstruction checks; not hardware fit, robot reach, flexible-net simulation or learned motion.',source='Upstream SO101 finger STEP; mounting datums preserved; finger tips modified',parts=records)
    (OUT/'design.json').write_text(json.dumps(report,indent=2)+'\n')
    shutil.copy2(ROOT/'tools/templates/dockable-net-review.html',OUT/'index.html')
    (OUT.parent/'index.html').write_text('<meta http-equiv="refresh" content="0;url=tool-study/index.html">')
    print('Largest overlap:',max(x['overlap_mm3'] for x in checks),flush=True)
    print('Blocked lateral directions:',blockers,flush=True)

if __name__=='__main__':main()
