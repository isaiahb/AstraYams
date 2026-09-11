"""Concept A: one supported clamshell, carrier, side bracket and small net.

CAD dimensions are design choices around a catalog container envelope. This is
not a released part drawing or a compliant textile/contact implementation.
All CAD dimensions here are millimetres.
"""
import math
import cadquery as cq


def rounded(w,l,h,r=3):
    return cq.Workplane('XY').box(w,l,h,centered=(True,True,False)).edges('|Z').fillet(r)


def parts(shelf_inboard_mm=0, shelf_drop_mm=0):
    p={}
    # Mount plate reuses four photo-model M5 positions on the lower faceplate.
    # It sits in front of that plate, laterally clear of the robot mounting sole.
    back=cq.Workplane('XY').box(205-shelf_inboard_mm,4,170+shelf_drop_mm).translate((-177.5+shelf_inboard_mm/2,44,-30-shelf_drop_mm/2)).edges('|Y').fillet(4)
    for x in [-102,-85]:
        for z in [-40,40]:
            back=back.cut(cq.Workplane('XZ').center(x,z).circle(2.8).extrude(60,both=True))
    p['pack_mount_plate']=back
    # Two side webs remain outside the carrier path. The load goes into the
    # carriage plate/guide shoes, never through the plastic robot base.
    p['pack_web']=cq.Workplane('YZ').polyline([(46,-108-shelf_drop_mm),(288,-108-shelf_drop_mm),(46,-26)]).close().extrude(3)
    p['pack_deck']=rounded(163,246,4,5)
    # Fore/aft carrier guides have an open front end for supported exchange.
    p['pack_guide']=cq.Workplane('XY').box(3,224,6,centered=(True,True,False))
    p['pack_rear_stop']=rounded(136,6,10,1)
    p['pack_latch']=cq.Workplane('XY').box(22,4,15).edges('|Y').fillet(2)
    p['pack_latch_pin']=cq.Workplane('XY').circle(2).extrude(18)
    # Hollow carrier, base support and shallow walls: the container is not
    # suspended by its thin rim. A front handle is for dock engagement.
    tray=rounded(139,208,11,6).cut(rounded(129,198,12,4).translate((0,0,3)))
    for x in [-47,0,47]:
        tray=tray.cut(cq.Workplane('XY').center(x,0).slot2D(150,10,90).extrude(3.1))
    tab=rounded(46,16,8,3).translate((0,108,1))
    tab=tab.cut(rounded(32,8,10,2).translate((0,108,0)))
    p['pack_carrier']=tray.union(tab)
    p['pack_liner']=rounded(107,168,1.5,7)
    # Approximate tapered vented PET clamshell; catalog external envelope only.
    # Open height is a design interpretation, not an exact supplier CAD copy.
    outer=cq.Workplane('XY').rect(108,168).workplane(offset=76).rect(123,186).loft()
    inner=cq.Workplane('XY').workplane(offset=.7).rect(106.6,166.6).workplane(offset=76).rect(121.6,184.6).loft()
    box=outer.cut(inner)
    rim=rounded(126,189,1.2,5).cut(rounded(120,183,2,4)).translate((0,0,75.5))
    box=box.union(rim)
    for y in [-65,-40,-15,15,40,65]:
        for x in [-58,58]:
            vent=cq.Workplane('YZ').center(y,48).slot2D(15,3,90).extrude(85,both=True)
            # One cut spans both opposite sides, repeated once per y.
            if x<0:box=box.cut(vent)
    p['pack_clamshell']=box
    # Closed lid lies in +X from the long-side hinge; rotate it 95 degrees
    # about -Y to hold it nearly upright along the outboard container edge.
    lid=rounded(126,189,4.5,5).cut(rounded(124.6,187.6,5,4.3).translate((0,0,.7)))
    p['pack_lid']=lid.translate((63,0,0))
    p['pack_hinge']=cq.Workplane('XY').circle(2).extrude(25)
    clip=cq.Workplane('XY').box(10,10,22).edges('|Z').fillet(2)
    clip=clip.cut(cq.Workplane('XY').box(3,12,16).translate((0,0,4)))
    p['pack_lid_clip']=clip
    # Fastener envelopes with real heads, shafts and washers, supplier pending.
    bolt=cq.Workplane('XY').circle(2.5).extrude(16)
    bolt=bolt.union(cq.Workplane('XY').polygon(6,8).extrude(3).translate((0,0,16)))
    p['pack_m5_bolt']=bolt
    p['pack_washer']=cq.Workplane('XY').circle(5).circle(2.7).extrude(1)
    # A shallow net with a rigid rectangular pinch handle and bolted clamp ring.
    ring=cq.Workplane('XY').circle(43).circle(38).extrude(4)
    # Raised handle lets the shallow net enter a clamshell while its handle
    # passes above the rim. A flat handle would strike the container wall.
    handle=rounded(44,16,17.8,3).translate((-59,0,41.1))
    neck=cq.Workplane('XZ').polyline([(-44,0),(-36,0),(-49,54),(-57,54)]).close().extrude(8,both=True)
    ring=ring.union(handle).union(neck)
    retain=cq.Workplane('XY').circle(43).circle(38).extrude(2)
    for a in [45,135,225,315]:
        x,y=40.5*math.cos(math.radians(a)),40.5*math.sin(math.radians(a))
        hole=cq.Workplane('XY').center(x,y).circle(1.3).extrude(10,both=True)
        ring=ring.cut(hole);retain=retain.cut(hole)
    p['pack_net_frame']=ring;p['pack_net_retainer']=retain
    p['pack_net_screw']=cq.Workplane('XY').circle(1.2).extrude(6).union(cq.Workplane('XY').circle(2.1).extrude(1.5).translate((0,0,6)))
    # Rest-shape textile represented by swept filaments, not an invisible bowl.
    wires=[]
    for swap in [False,True]:
        for offset in range(-32,33,8):
            # Continue the textile into the bolted ring's clamping land.
            extent=math.sqrt(40.5**2-offset**2)
            pts=[]
            for k in range(17):
                a=-extent+2*extent*k/16;x,y=(offset,a) if swap else (a,offset)
                pts.append(cq.Vector(x,y,4-20*(1-(x*x+y*y)/40.5**2)+(.35 if swap else -.35)))
            path=cq.Wire.assembleEdges([cq.Edge.makeSpline(pts)])
            plane=cq.Plane(origin=pts[0],normal=pts[1]-pts[0])
            wires.append(cq.Workplane(plane).circle(.35).sweep(path).val())
    p['pack_net_textile']=cq.Workplane('XY').newObject([cq.Compound.makeCompound(wires)])
    # Empty parking dock accepts the handle; shown even though a future
    # automated carrier exchange could let the arm retain its net continuously.
    dock=rounded(32,30,22,3).cut(rounded(20,32,24,2).translate((0,0,4)))
    p['pack_net_dock']=dock
    p['pack_dock_support']=cq.Workplane('XY').box(36,4,30)
    return p
