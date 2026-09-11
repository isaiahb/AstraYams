"""Passive, roller-actuated hinged net floor. Dimensions in millimetres.

The shaft carries a lever outside the container footprint. CAD and ideal-hinge
physics are a prototype, not a validated bearing/spring/food-contact design.
"""
import cadquery as cq
from packing_shelf_cad import rounded


def parts(post_height_mm=88):
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
    p['gate_shaft'] = cq.Workplane('XZ').polygon(6, 2.95).extrude(-106).translate((0, -28, 0))
    lever = rounded(49, 7, 5, 2).translate((-21.5, 0, -2.5))
    lever = lever.union(cq.Workplane('XZ').circle(5).extrude(3.5, both=True))
    lever = lever.cut(cq.Workplane('XZ').polygon(6, 3).extrude(10, both=True))
    p['gate_trigger_lever'] = lever
    p['gate_bearing'] = cq.Workplane('XZ').circle(3).circle(1.65).extrude(8)
    # Fixed rounded cam/roller and a slotted support. Height is an assembly
    # parameter; the runner is deliberately external to the clamshell.
    p['gate_roller'] = cq.Workplane('XZ').circle(6).circle(2).extrude(12, both=True)
    p['gate_roller_post'] = rounded(10, 10, post_height_mm, 2)
    foot = rounded(40, 35, 4, 3)
    for y in [-10, 10]:
        foot = foot.cut(cq.Workplane('XY').center(0, y).circle(2.1).extrude(6))
    p['gate_roller_foot'] = foot
    return p
