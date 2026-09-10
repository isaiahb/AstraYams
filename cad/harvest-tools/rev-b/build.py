"""Parametric two-tool mechanism study. CAD units mm; preview is NOT physics."""
from pathlib import Path
import json, math
import cadquery as cq
import numpy as np
import trimesh

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
parts=[]; solids={}; assembly=cq.Assembly(name='YAM_cut_and_catch_B')
WHITE='#dce7e6'; TEAL='#217a78'; STEEL='#9cabb2'; DARK='#343e45'

def add(name,shape,group,color,material,explode=(0,0,0)):
    s=shape.val() if isinstance(shape,cq.Workplane) else shape
    assert s.isValid() and len(s.Solids())==1, name
    cq.exporters.export(s,str(P/f'{name}.step'))
    cq.exporters.export(s,str(P/f'{name}.stl'),tolerance=.08,angularTolerance=.12)
    restored=cq.importers.importStep(str(P/f'{name}.step')).val()
    assert restored.isValid() and abs(restored.Volume()-s.Volume())<.01
    solids[name]=s
    parts.append(dict(name=name,file=name+'.stl',group=group,color=color,material=material,
                      volume_mm3=s.Volume(),valid=True,explode=explode))
    assembly.add(s,name=name)
    return s

def box(x,y,z,center,r=0):
    b=cq.Workplane('XY').box(x,y,z)
    if r:b=b.edges().fillet(r)
    return b.translate(center)

def hole_y(x,y,z,length=20,r=1.35):
    return cq.Solid.makeCylinder(r,length,cq.Vector(x,y,z),cq.Vector(0,1,0))

def screw(name,x,y,z,length,group,axis='z'):
    # M2.5 nominal envelope with real clearance and recessed hex; threads omitted.
    s=cq.Workplane('XY').circle(1.25).extrude(-length)
    s=s.union(cq.Workplane('XY').circle(2.25).extrude(1.8))
    s=s.cut(cq.Workplane('XY',origin=(0,0,1.81)).polygon(6,2.2).extrude(-1.0))
    if axis=='y':s=s.rotate((0,0,0),(1,0,0),-90)
    return add(name,s.translate((x,y,z)),group,STEEL,'steel fastener envelope',(0,0,10))

def ring(rx,ry,ix,iy,z,h):
    # Separate cut avoids ellipse wire winding ambiguity.
    a=cq.Workplane('XY',origin=(0,0,z)).ellipse(rx,ry).extrude(h)
    b=cq.Workplane('XY',origin=(0,0,z-1)).ellipse(ix,iy).extrude(h+2)
    return a.cut(b)

# Complete rim; separate retaining ring clamps a replaceable textile flange.
frame=ring(32,28,27,23,-1.5,4)
handle=box(34,18,20,(-70,0,-7),2)
wires=[cq.Workplane('YZ',origin=(x,0,z)).ellipse(ry,rz).val()
       for x,ry,rz,z in [(-60,8,6,-7),(-48,6,4,-6),(-37,6,3.5,-3),(-29,8,2.5,0)]]
frame=frame.union(handle).union(cq.Workplane(obj=cq.Solid.makeLoft(wires))).clean()
retainer=ring(32,28,27,23,2.8,2.4)
holes=[(29.5,0),(-29.5,0),(0,25.5),(0,-25.5)]
for x,y in holes:
    bore=cq.Workplane('XY',origin=(x,y,-5)).circle(1.35).extrude(16)
    frame=frame.cut(bore);retainer=retainer.cut(bore)
add('catcher_frame',frame,'catcher',WHITE,'PA12 prototype assumption')
add('net_retaining_ring',retainer,'catcher',TEAL,'PA12 prototype assumption',(0,0,16))
for j,(x,y) in enumerate(holes):screw(f'rim_screw_{j}',x,y,5.2,7,'catcher')

# One clamping carrier per stock distal finger. The cavity follows the measured
# envelope; a liner fills the remaining gap. This is NOT a verified clamp preload.
# Canonical tool coordinates: +X forward, jaw travel along Y, +Z upward.
shell=box(35,3,54,(130,-12,0),.5)
for z in [-23.7,23.7]:
    shell=shell.union(box(35,11.2,6.6,(130,-5.1,z),.5))
# Flat screw-on cover and a rounded tapered cantilever leading to the blades.
cover=box(35,2,54,(130,1.5,0),.45)
spine=cq.Solid.makeLoft([cq.Workplane('YZ',origin=(x,y,0)).ellipse(ry,rz).val()
                        for x,y,ry,rz in [(143,-9,4,6),(158,-8,4,5),(174,-7,4,3),(184,-7,4,2)]])
shell=shell.union(cq.Workplane(obj=spine)).union(box(15,7,3,(182,-7,-2.02),.5)).clean()
# Machined/printed flat seat: the steel blade rests on the carrier, not inside it.
shell=shell.cut(box(17,10,15,(182.5,-6.5,6.98)))
for x in [120,140]:
    for z in [-23.7,23.7]:
        bore=hole_y(x,-16,z,22)
        shell=shell.cut(bore);cover=cover.cut(hole_y(x,-16,z,22,r=1.05))
# The last 7 mm is the exposed cutting edge; blade-root holes locate replaceable steel.
outline=[(176,-10),(200,-10),(204,-6),(204,3),(197,4),(191,-2),(176,-2)]
blade=cq.Workplane('XY',origin=(0,0,-.52)).polyline(outline).close().extrude(.5)
for x in [179,185]:
    bore=cq.Workplane('XY',origin=(x,-7,-6)).circle(1.35).extrude(12)
    blade=blade.cut(bore);shell=shell.cut(bore)
# Mirror the opposing cartridge across Y; offset its cutting plane in Z.
for side,sgn in [('left',-1),('right',1)]:
    group='cutter_'+side
    if sgn<0:sh,cv,bl=shell,cover,blade
    else:
        sh=shell.mirror('XZ').mirror('XY')
        cv=cover.mirror('XZ')
        bl=blade.mirror('XZ').mirror('XY')
    add(side+'_carrier',sh,group,WHITE,'PA12 prototype; stiffness unverified')
    add(side+'_clamp_cover',cv,group,TEAL,'2 mm aluminium tapped clamp plate',(0,-sgn*10,0))
    add(side+'_blade',bl,group,STEEL,'0.5 mm steel blank; edge grinding not yet detailed',(0,0,sgn*8))
    # Flat insert between the finger face and clamp cover: compression not solved.
    liner=box(30,.5,38,(130,.25,0),.15)
    if sgn>0:liner=liner.mirror('XZ')
    add(side+'_liner',liner,group,DARK,'elastomer; friction/compression uncalibrated')
    # Four clamping screws span cover into the outside ears. Mirror fasteners as needed.
    for j,(x,z) in enumerate([(120,-23.7),(120,23.7),(140,-23.7),(140,23.7)]):
        n=f'{side}_clamp_screw_{j}'
        s=cq.Workplane('XY').circle(1.25).extrude(-16).union(cq.Workplane('XY').circle(2.25).extrude(1.8))
        s=s.cut(cq.Workplane('XY',origin=(0,0,1.81)).polygon(6,2.2).extrude(-1))
        s=s.rotate((0,0,0),(1,0,0),90).translate((x,-13.5,z))
        if sgn>0:s=s.mirror('XZ')
        add(n,s,group,STEEL,'steel fastener envelope')
    for j,x in enumerate([179,185]):
        s=cq.Workplane('XY').circle(1.25).extrude(-4).union(cq.Workplane('XY').circle(2.25).extrude(1.6))
        s=s.cut(cq.Workplane('XY',origin=(0,0,1.61)).polygon(6,2.2).extrude(-1)).translate((x,-7,-.02))
        if sgn>0:s=s.mirror('XZ').mirror('XY')
        add(f'{side}_blade_screw_{j}',s,group,STEEL,'steel fastener envelope')

# Transform the official meshes directly. These are the source gripper-local
# translations from the imported YAM scene, so no prior training run is required.
F=np.array([[0,0,-1],[0,1,0],[1,0,0]])
for name,source,offset in [('yam_gripper','gripper',[-.014,-.0463995,.0731]),
                         ('yam_left','tip_left',[-.01399989,-.0469495,.0731001]),
                         ('yam_right','tip_right',[-.0140001,-.04584943,.0731001])]:
    geo=trimesh.load(ROOT/f'assets/robots/yam/v1/assets/{source}.stl',force='mesh')
    geo.vertices=(geo.vertices+offset)@F.T*1000
    geo.export(P/f'{name}.stl')

def tube(points,r=.20,n=6):
    p=np.array(points);v=[]
    for i,c in enumerate(p):
        t=p[min(i+1,len(p)-1)]-p[max(0,i-1)];t/=np.linalg.norm(t)
        ref=np.array([0.,0.,1.])
        if abs(t@ref)>.95:ref=np.array([1.,0.,0.])
        u=np.cross(t,ref);u/=np.linalg.norm(u);w=np.cross(t,u)
        for a in np.linspace(0,2*np.pi,n,endpoint=False):v.append(c+r*(u*np.cos(a)+w*np.sin(a)))
    f=[]
    for i in range(len(p)-1):
        for j in range(n):
            a=i*n+j;b=i*n+(j+1)%n;c=b+n;e=a+n;f.extend([[a,b,c],[a,c,e]])
    f.extend([[0,j+1,j] for j in range(1,n-1)])
    e=(len(p)-1)*n;f.extend([[e,e+j,e+j+1] for j in range(1,n-1)])
    return trimesh.Trimesh(v,f,process=False)

net=[]
for swap in [False,True]:
    rx,ry=(26,30) if swap else (30,26)
    ix,iy=(23,27) if swap else (27,23)
    for x in np.arange(-rx+1,rx,2.5):
        yl=ry*np.sqrt(1-(x/rx)**2);pts=[]
        for y in np.linspace(-yl,yl,45):
            z=2.65-28*max(0,1-(x/ix)**2-(y/iy)**2)
            pts.append((y,x,z) if swap else (x,y,z))
        net.append(tube(pts))
trimesh.util.concatenate(net).export(P/'net-pouch.stl')

# Preserved from berry_primary in the v14 specimen-derived support task, in mm.
# Context geometry only; the present tools have not been integrated into its dynamics.
fruit=trimesh.load(P/'reference/berry.stl',force='mesh');v=fruit.vertices
v[:,2]+=12-v[:,2].min();fruit.export(P/'berry-reference.stl')
stem_bottom=float(v[:,2].max());cut_z=stem_bottom+10
# A context-only stem cylinder: it remains visible during the CAD closure preview.
trimesh.creation.cylinder(radius=1,height=28,sections=24,transform=trimesh.transformations.translation_matrix([0,0,stem_bottom+14])).export(P/'stem-reference.stl')

# Collision check of the two nominal rigid tool cartridges, independent of rendering.
collision=[]
for travel in np.linspace(7,3,9):
    worst=0.;pair=None
    for left in [p for p in parts if p['group']=='cutter_left']:
        for right in [p for p in parts if p['group']=='cutter_right']:
            a=solids[left['name']].translate((0,-travel,0))
            b=solids[right['name']].translate((0,travel,0))
            volume=a.intersect(b).Volume()
            if volume>worst:worst=volume;pair=[left['name'],right['name']]
    collision.append(dict(per_jaw_offset_mm=float(travel),max_cross_cartridge_intersection_mm3=worst,pair=pair))
    print('jaw clearance',collision[-1],flush=True)

manifest=dict(title='Catch + cut · mechanism study B',units='mm',parts=parts,cut_z=cut_z,
  jaw_open_mm=7,jaw_closed_mm=3,catcher_jaw_offset_mm=9.05,
  catcher_gripper_origin=[-200,0,-7],cutter_gripper_origin=[200,0,cut_z],
  aperture_mm=[54,46],net_rest_depth_mm=28,fruit_lowest_point_above_rim_plane_mm=12,
  blade_thickness_mm=.5,nominal_blade_plane_clearance_mm=.04,
  stem_diameter_mm=2,mesh_pitch_mm=2.5,collision_sweep=collision,
  scope='Static/kinematic CAD preview. Net is an assumed textile rest shape. No physics, fracture, bruise or PPO result for these tools.',
  robot_source='../../../assets/robots/yam/SOURCE.json')
(P/'design.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Export separate manufacturing components, and an assembly at the CLOSED state.
world_assembly=cq.Assembly(name='cut_and_catch_closed')
for part in parts:
    s=solids[part['name']];group=part['group']
    if group.startswith('cutter'):
        sign=-1 if group.endswith('left') else 1
        s=s.translate((0,sign*3,0)).rotate((0,0,0),(0,0,1),180).translate((200,0,cut_z))
    color=cq.Color(*[int(part['color'][i:i+2],16)/255 for i in (1,3,5)])
    world_assembly.add(s,name=part['name'],color=color)
world_assembly.export(str(P/'harvest-tools.step'))
print('Built',len(parts),'rigid solids + separate textile and source robot references',flush=True)
