"""Conservative convex slices of a tessellated CAD surface, including open seams.

Clip triangle edges against each slab before taking its hull. Selecting existing
vertices alone loses long faces; solid booleans silently fail on open STL seams.
"""
import numpy as np
import trimesh


def sliced_hulls(vertices, faces, step=4., overlap=.1):
    vertices=np.asarray(vertices); triangles=vertices[np.asarray(faces)]
    hulls=[]
    for start in np.arange(vertices[:,0].min(),vertices[:,0].max(),step):
        lo,hi=start-overlap/2,start+step+overlap/2
        tri=triangles[(triangles[:,:,0].max(axis=1)>=lo)&(triangles[:,:,0].min(axis=1)<=hi)]
        if not len(tri):continue
        points=[tri.reshape(-1,3)[((tri[:,:,0]>=lo)&(tri[:,:,0]<=hi)).ravel()]]
        a=tri; b=np.roll(tri,-1,axis=1); delta=b-a
        for plane in (lo,hi):
            valid=np.abs(delta[:,:,0])>1e-12
            t=np.divide(plane-a[:,:,0],delta[:,:,0],out=np.full(valid.shape,-1.),where=valid)
            hit=valid&(t>=0)&(t<=1)
            points.append((a+t[:,:,None]*delta)[hit])
        points=np.unique(np.round(np.concatenate(points),9),axis=0)
        if len(points)>=4:
            hulls.append(trimesh.convex.convex_hull(points))
    if not hulls:raise ValueError('CAD contact decomposition produced no volume')
    return hulls
