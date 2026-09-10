"""Measured YAM interface, solid B-rep berry support cradle. Units: millimetres."""
from pathlib import Path
import json
import cadquery as cq
from cadquery import exporters
OUT=Path(__file__).resolve().parent
P=dict(handle_length=34.,handle_width=26.,handle_thickness=16.,handle_corner_radius=3.,jaw_contact_length=28.,cradle_offset=70.,outer_radius=17.,inner_radius=15.,bowl_center_height=15.,rim_height=8.,side_opening_y=5.,edge_radius=.65)
C=P['cradle_offset'];H=P['bowl_center_height']
# The YAM pads span 34 mm axially and 40 mm laterally; retain insertion clearance.
handle=cq.Workplane('XY').box(P['handle_length'],P['handle_width'],P['handle_thickness']).edges().fillet(P['handle_corner_radius'])
# Elliptical loft creates a changing structural section with rounded sides.
sections=[(10,11,6,0),(20,9,4.8,-.7),(34,6.8,3.3,-1.8),(48,5.7,3.0,-2),(59,4.8,2.5,-1.5),(66,4.,2.,-1.5)]
wires=[]
for x,ry,rz,z in sections:
 wires.append(cq.Workplane('YZ',origin=(x,0,z)).ellipse(ry,rz).val())
neck=cq.Solid.makeLoft(wires,ruled=False)
outer=cq.Workplane('XY').sphere(P['outer_radius']).translate((C,0,H))
clip=cq.Workplane('XY').box(50,50,P['rim_height']+3,centered=(True,True,False)).translate((C,0,-3))
outer=outer.intersect(clip)
inner=cq.Workplane('XY').sphere(P['inner_radius']).translate((C,0,H))
opening=cq.Workplane('XY').box(50,30,30,centered=(True,False,False)).translate((C,-P['side_opening_y']-30,-3))
# Round the bowl lip and side opening before fusing the structural neck.
bowl=outer.cut(inner).cut(opening).edges().fillet(P['edge_radius'])
core=handle.union(cq.Workplane(obj=neck)).clean()
shoulder=[e for e in core.val().Edges() if 14<e.Center().x<18 and e.geomType()=='BSPLINE']
core=core.newObject(shoulder).fillet(2.)
body=core.union(bowl).cut(inner).clean()
solid=body.val();assert solid.isValid();assert len(solid.Solids())==1
exporters.export(body,str(OUT/'berry-cradle.step'))
exporters.export(body,str(OUT/'berry-cradle.stl'),tolerance=.045,angularTolerance=.08)
exporters.export(body,str(OUT/'berry-cradle.brep'))
section=body.cut(cq.Workplane('XY').box(200,100,100).translate((40,-50,0))).clean()
assert section.val().isValid()
exporters.export(section,str(OUT/'section.stl'),tolerance=.045,angularTolerance=.08)
# Orthographic drawings are exported from the same exact solid.
for name,projection in [('top',(0,0,1)),('side',(0,-1,0)),('end',(1,0,0)),('isometric',(1,-1,1))]:
 exporters.export(body,str(OUT/f'{name}.svg'),opt={'width':1000,'height':600,'projectionDir':projection,'showHidden':False,'showAxes':False,'strokeWidth':.6})
bb=solid.BoundingBox();report=dict(parameters_mm=P,valid=solid.isValid(),solids=len(solid.Solids()),volume_mm3=solid.Volume(),surface_mm2=solid.Area(),bounds_mm=[bb.xlen,bb.ylen,bb.zlen],nominal_density_g_cm3=1.01,nominal_solid_PA12_mass_g=solid.Volume()/1000*1.01,scope='Solid concept CAD for a printed PA12 prototype, not a validated production design. Density is a design assumption; no bruise or food-contact certification claimed.',grip_interface='Opposed flat Z faces, 16 mm nominal separation; 26 mm width and 34 mm axial engagement envelope.',construction=['R3 grip body','Smooth elliptical neck loft with R2 shoulder blend','Concentric spherical bowl with 2 mm radial wall','Side opening','R0.65 exposed bowl edges'],coordinate_mapping='To YAM gripper metres: [-CAD_Y, CAD_Z, -130-CAD_X] / 1000')
(OUT/'design.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
