"""Regression: long CAD faces must collide between their tessellation rings."""
import importlib.util
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
import trimesh

spec=importlib.util.spec_from_file_location('cad_collision',Path(__file__).parents[1]/'tools/cad_collision.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def test_sparse_long_faces_and_unmerged_stl_seams_are_covered():
    # Only two tessellation rings, forty millimetres apart; the original
    # vertex-filter decomposition left the entire middle without colliders.
    mesh=trimesh.creation.cylinder(radius=3,height=40,sections=16)
    mesh.vertices=mesh.vertices[:,[2,0,1]]
    tri=mesh.vertices[mesh.faces]
    vertices=tri.reshape(-1,3);faces=np.arange(len(vertices)).reshape(-1,3)
    hulls=module.sliced_hulls(vertices,faces)
    samples=np.concatenate([tri.mean(axis=1),tri[:,0]*.2+tri[:,1]*.4+tri[:,2]*.4])
    distance=np.full(len(samples),np.inf)
    for hull in hulls:
        planes=ConvexHull(hull.vertices).equations
        distance=np.minimum(distance,np.max(samples@planes[:,:3].T+planes[:,3],axis=1))
    assert len(hulls)==10
    assert np.max(distance)<1e-7
