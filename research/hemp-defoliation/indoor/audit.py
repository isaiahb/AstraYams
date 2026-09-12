"""Narrow geometric checks; this is not a collision or biological validation."""
from pathlib import Path
import json
import numpy as np

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[2]/'runs/hemp-indoor-v1'


def segment_distance(p,points):
    a=np.array(points[:-1]);v=np.diff(points,axis=0)
    t=np.clip(np.sum((p-a)*v,axis=1)/np.sum(v*v,axis=1),0,1)
    return float(np.linalg.norm(p-(a+t[:,None]*v),axis=1).min())


def main():
    data=json.loads((OUT/'review-data.json').read_text());lookup={o['id']:o for o in data['organs']}
    node_errors=[];attachment_errors=[]
    for o in data['organs']:
        if not o.get('specimen') or not o['parent']:continue
        p=lookup[o['parent']]
        if o['kind']=='node':node_errors.append(segment_distance(np.array(o['attachment']),p['centerline']))
        if o['kind'] in ['branch','petiole'] and p['kind']=='node':attachment_errors.append(float(np.linalg.norm(np.array(o['attachment'])-p['attachment'])))
    assert max(node_errors)<2e-7 and max(attachment_errors)<2e-7
    cfg=data['config'];base=json.loads((HERE.parent/'whole-plant/specimen.json').read_text())
    d=base['pot_depth_m'];r=base['pot_radius_m'];z=cfg['bench']['surface_z_m']
    # Exact root surfaces, not just root centerlines, for assumed pot containment.
    geometry=json.loads((OUT/'plant.json').read_text());g=geometry['groups']['root'];verts=np.array(g['vertices']);faces=np.array(g['faces'])
    specimens=[]
    for s in data['specimens']:
        subset=np.concatenate([faces[item['first_face']:item['end_face']].ravel() for item in g['organs'] if item['id'].startswith(s['id']+'/')])
        v=verts[np.unique(subset)]-s['substrate_origin_m'];depth=np.clip(-v[:,2]/d,0,1)
        inner_radius=r*(1-.24*depth)-.003
        radial_margin=float((inner_radius-np.linalg.norm(v[:,:2],axis=1)).min())
        bottom_margin=float(v[:,2].min()+d-.006)
        assert radial_margin>0 and bottom_margin>0
        pot_bottom=s['substrate_origin_m'][2]-d
        assert abs(pot_bottom-z)<1e-9
        overhead=cfg['lighting_z_m']-.023-s['bounds_m'][1][2]
        assert overhead>0
        specimens.append({'id':s['id'],'root_wall_min_margin_m':radial_margin,'root_bottom_min_margin_m':bottom_margin,
           'pot_bottom_to_tray_m':pot_bottom-z,'overhead_vertical_margin_m':overhead,
           'geometry_sha256':s['geometry_sha256']})
    assert len({s['geometry_sha256'] for s in specimens})==3
    report={'status':'narrow geometric checks pass; contact physics unvalidated',
      'max_node_to_parent_centerline_error_m':max(node_errors),
      'max_branch_or_petiole_to_node_error_m':max(attachment_errors),'specimens':specimens,
      'all_leaf_hardware_collisions_checked':False,'trellis_contact_solved':False,'biological_calibration':False}
    (OUT/'layout-checks.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
