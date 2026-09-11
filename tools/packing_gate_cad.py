"""Passive, roller-actuated hinged net floor. Dimensions in millimetres.

The shaft carries a lever outside the container footprint. CAD and ideal-hinge
physics are a prototype, not a validated bearing/spring/food-contact design.
"""
import cadquery as cq
from packing_shelf_cad import rounded


def parts(post_height_mm=88, lever_offset_mm=70, paired=False):
    p = {}
    # Two fixed hinge ears, connected to the existing back edge of the frame.
    ear = rounded(12, 8, 12, 2).translate((-40, 24, -8))
    hole = cq.Workplane('XZ').center(-40, -5).circle(1.65).extrude(45, both=True)
    ear = ear.cut(hole)
    p['gate_fixed_ears'] = ear.union(ear.translate((0, -48, 0)))
    # Coordinates are relative to the hinge axis. A shallow moving ring supports
    # the textile. The boss and bridge key it to the transverse shaft.
    ring = cq.Workplane('XY').center(40, 0).circle(37.5).circle(34.5).extrude(2)
    bridge = rounded(12, 32, 4, 2).translate((3, 0, -1))
    boss = cq.Workplane('XZ').circle(4).extrude(18, both=True)
    keyway = cq.Workplane('XZ').polygon(6, 3).extrude(24, both=True)
    p['gate_floor_ring'] = ring.union(bridge).union(boss).cut(keyway)
    # A hexagonal steel shaft transmits the external lever torque to the floor.
    shaft_start = -(lever_offset_mm+8) if paired else -28
    shaft_length = 2*(lever_offset_mm+8) if paired else lever_offset_mm+36
    p['gate_shaft'] = cq.Workplane('XZ').polygon(6, 2.95).extrude(-shaft_length).translate((0, shaft_start, 0))
    lever = rounded(49, 7, 5, 2).translate((-21.5, 0, -2.5))
    lever = lever.union(cq.Workplane('XZ').circle(5).extrude(3.5, both=True))
    lever = lever.cut(cq.Workplane('XZ').polygon(6, 3).extrude(10, both=True))
    p['gate_trigger_lever'] = lever
    p['gate_bearing'] = cq.Workplane('XZ').circle(3).circle(1.65).extrude(8)
    # Fixed rounded cam/roller and a slotted support. Height is an assembly
    # parameter; the runner is deliberately external to the clamshell.
    p['gate_roller'] = cq.Workplane('XZ').circle(6).circle(2).extrude(12, both=True)
    p['gate_roller_post'] = rounded(10, 10, post_height_mm, 2)
    foot = rounded(80 if lever_offset_mm>70 else 40, 35, 4, 3)
    for y in [-10, 10]:
        foot = foot.cut(cq.Workplane('XY').center(-20 if lever_offset_mm>70 else 0, y).circle(2.1).extrude(6))
    p['gate_roller_foot'] = foot
    # Front-side carrier wall requires the second column to step outward.
    # The inboard heel still bolts through the deck; its top reaches back to
    # the original roller position, leaving the release geometry unchanged.
    p['gate_roller_offset_post']=rounded(10,10,post_height_mm-8,2).translate((0,25,0)).union(rounded(10,35,8,2).translate((0,12.5,post_height_mm-8)))
    extended_foot=rounded(80,60,4,3).translate((0,12.5,0))
    for y in [-10,10]:extended_foot=extended_foot.cut(cq.Workplane('XY').center(20,y).circle(2.1).extrude(6))
    p['gate_roller_offset_foot']=extended_foot
    # The roller sits between two ears instead of intersecting a solid post.
    # The lever approaches from below as it turns nearly vertical. Put the
    # crossbar behind the axle, leaving that entire approach lane open.
    fork=rounded(10,31,4,1).translate((-12,0,-12))
    for y in [-14,14]:fork=fork.union(rounded(22,3,15,1).translate((-6,y,-12)))
    fork=fork.cut(cq.Workplane('XZ').circle(2.1).extrude(20,both=True))
    p['gate_roller_fork']=fork
    p['gate_roller_axle']=cq.Workplane('XZ').circle(1.95).extrude(17.5,both=True)
    # Flush M4 screw envelopes and hex nuts for an underside mounting plate.
    screw=cq.Workplane('XY').circle(2).extrude(11).translate((0,0,-9))
    head=cq.Workplane('XY').workplane(offset=2).circle(2).workplane(offset=2).circle(4).loft()
    socket=cq.Workplane('XY').polygon(6,2.4).extrude(1.3).translate((0,0,2.8))
    p['gate_mount_screw']=screw.union(head).cut(socket)
    p['gate_mount_nut']=cq.Workplane('XY').polygon(6,8.08).circle(2.1).extrude(3).translate((0,0,-7))
    return p
