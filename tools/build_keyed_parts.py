"""Parametric CAD meshes and exact convex wall pieces for a keyed socket."""
from pathlib import Path
import json
import xml.etree.ElementTree as E
import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import triangulate

P = Path(__file__).resolve().parents[1] / "tasks/keyed_insertion"
ASSETS = P / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)


def prism(points, z0, z1):
    points = np.asarray(points)
    n = len(points)
    vertices = np.r_[np.c_[points, np.full(n, z0)], np.c_[points, np.full(n, z1)]]
    faces = []
    for i in range(1, n - 1):
        faces.extend([[0, i + 1, i], [n, n + i, n + i + 1]])
    for i in range(n):
        j = (i + 1) % n
        faces.extend([[i, j, n + j], [i, n + j, n + i]])
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    mesh.fix_normals()
    assert mesh.is_watertight and mesh.volume > 0
    return mesh


def sub(parent, tag, **attributes):
    return E.SubElement(parent, tag, {k: str(v) for k, v in attributes.items()})


peg = Polygon([(-.009, -.007), (.009, -.007), (.009, .003), (.005, .007), (-.009, .007)])
opening = peg.buffer(.0006, join_style=2)
outer = Polygon([(-.022, -.020), (.022, -.020), (.022, .020), (-.022, .020)])
ring = outer.difference(opening)
walls = [t for t in triangulate(ring) if ring.covers(t)]
assert abs(sum(t.area for t in walls) - ring.area) < 1e-12
prism(list(peg.exterior.coords)[:-1], 0, .038).export(ASSETS / "peg.stl")
socket_meshes = []
for i, wall in enumerate(walls):
    m = prism(list(wall.exterior.coords)[:-1], .008, .040)
    m.export(ASSETS / f"wall_{i}.stl")
    socket_meshes.append(m)
floor = prism(list(outer.exterior.coords)[:-1], 0, .008)
socket_meshes.append(floor)
trimesh.util.concatenate(socket_meshes).export(ASSETS / "socket-cad.stl")
(P / "design.json").write_text(json.dumps({"units": "m", "peg_profile_xy": list(peg.exterior.coords), "peg_length": .038, "socket_clearance_per_side": .0006, "socket_top": .040, "socket_floor": .008, "collision_decomposition": "convex triangular prisms covering the socket walls; the opening is not convex-filled", "wall_count": len(walls)}, indent=2))

root = E.Element("mujoco", model="AstraFactory keyed insertion fixture")
sub(root, "compiler", angle="radian", meshdir="assets", autolimits="true")
sub(root, "option", timestep="0.002", integrator="implicitfast", gravity="0 0 -9.81", iterations="80")
visual = sub(root, "visual")
sub(visual, "global", offwidth="960", offheight="720")
sub(visual, "headlight", ambient=".4 .4 .4", diffuse=".7 .7 .7")
asset = sub(root, "asset")
sub(asset, "mesh", name="peg", file="peg.stl")
for i in range(len(walls)):
    sub(asset, "mesh", name=f"wall{i}", file=f"wall_{i}.stl")
default = sub(root, "default")
sub(default, "geom", friction=".5 .005 .0001", solref=".005 1", solimp=".95 .99 .001", condim="3")
world = sub(root, "worldbody")
sub(world, "light", pos="0 -.2 .5", dir="0 .2 -.5", directional="true")
sub(world, "camera", name="overview", pos=".13 -.18 .15", xyaxes=".81 .585 0 -.30 .415 .86")
sub(world, "geom", name="bench", type="plane", size=".3 .3 .01", rgba=".13 .17 .21 1")
socket = sub(world, "body", name="socket")
sub(socket, "geom", name="socket_floor", type="box", pos="0 0 .004", size=".022 .020 .004", rgba=".22 .48 .65 1")
for i in range(len(walls)):
    sub(socket, "geom", name=f"socket_wall_{i}", type="mesh", mesh=f"wall{i}", rgba=".22 .48 .65 1")
tool = sub(world, "body", name="held_tool")
for name, axis, bounds in [("tool_x", "1 0 0", "-.05 .05"), ("tool_y", "0 1 0", "-.05 .05"), ("tool_z", "0 0 1", ".006 .12")]:
    sub(tool, "joint", name=name, type="slide", axis=axis, range=bounds)
sub(tool, "joint", name="tool_yaw", type="hinge", axis="0 0 1", range="-1.2 1.2")
sub(tool, "inertial", pos="0 0 .035", mass=".15", diaginertia=".0001 .0001 .00005")
sub(tool, "geom", name="peg", type="mesh", mesh="peg", rgba=".96 .63 .16 1")
sub(tool, "geom", name="tool_holder", type="cylinder", pos="0 0 .048", size=".014 .01", rgba=".65 .69 .74 1")
act = sub(root, "actuator")
for name, joint, force in [("x", "tool_x", "-20 20"), ("y", "tool_y", "-20 20"), ("z", "tool_z", "-20 20"), ("yaw", "tool_yaw", "-.6 .6")]:
    sub(act, "motor", name=name, joint=joint, ctrlrange=force)
E.indent(root)
E.ElementTree(root).write(P / "scene.xml", encoding="unicode")
print(f"Built keyed CAD: {len(walls)} convex socket wall pieces; opening preserved")
