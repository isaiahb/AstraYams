"""Compile a reproducible morphology hypothesis into the existing physical graph.

Seeds describe correlated hypotheses, not an empirically fitted plant population.
No loaded pose, contact mask, or physical state is adjusted by this compiler.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'tasks/strawberry_specimen/parametric/canopy-v8.json'


def compile_spec(config_path=DEFAULT, seed=None):
    cfg = json.loads(Path(config_path).read_text())
    spec = json.loads((ROOT / cfg['baseline_graph']).read_text())
    spec['scope'] = cfg['scope']
    spec['morphology_evidence'] = cfg['evidence']
    spec['parameter_status'] = cfg['parameter_status']
    spec['mechanics'] = copy.deepcopy(cfg['mechanics'])
    spec['simulation_timestep_s'] = cfg.get('simulation_timestep_s',spec['simulation_timestep_s'])
    spec['crown_structure'] = copy.deepcopy(cfg['crown_structure'])
    spec['leaflet_profile'].update(cfg['leaflet_profile'])
    crown = np.array(spec['crown_m'])
    rng = np.random.default_rng(seed)
    variation = cfg['variation']
    size = float(rng.uniform(*variation['size_scale'])) if seed is not None else 1.
    openness = float(rng.uniform(*variation['radial_scale'])) if seed is not None else 1.
    turn = float(rng.uniform(*variation['azimuth_offset_rad'])) if seed is not None else 0.
    rotation = np.array([[np.cos(turn),-np.sin(turn),0],
                         [np.sin(turn),np.cos(turn),0],[0,0,1]])
    leaves = []
    for organ in cfg['leaves']:
        leaf = copy.deepcopy(organ)
        offset = np.array(leaf.pop('attachment_m'), float)
        delta = np.array(leaf.pop('endpoint_from_crown_m'), float)
        # Shared latent causes, not independently sampled endpoints or masses.
        delta[:2] *= size * openness
        delta[2] *= size
        delta = rotation @ delta
        offset = rotation @ offset
        leaf['tip'] = (crown + delta).tolist()
        leaf['length'] *= size
        leaf['shaft_radius_m'] *= size
        leaf['yaw'] += turn
        d = delta - offset
        azimuth = np.arctan2(d[1], d[0])
        unit_horizontal = np.array([np.cos(azimuth), np.sin(azimuth), 0])
        controls = []
        for which, angle, fraction in [('base', leaf.pop('base_inclination_deg'), .30),
                                       ('tip', leaf.pop('tip_inclination_deg'), .28)]:
            radians = np.deg2rad(angle)
            tangent = np.sin(radians)*unit_horizontal + np.array([0,0,np.cos(radians)])
            handle = tangent * np.linalg.norm(d) * fraction
            controls.append((handle if which == 'base' else d-handle).tolist())
        leaf['growth'] = {'attachment_m':offset.tolist(),'control_points_m':controls,
                          'stipule_length_m':min(.018,float(np.linalg.norm(d))*.15),
                          'status':'unloaded shape hypothesis; not photo-measured or fitted loaded pose'}
        leaves.append(leaf)
    spec['leaves'] = leaves
    # Fruit dimensions co-vary; mass follows volume at the same assumed density.
    for branch in spec['truss']:
        if 'fruit' in branch:
            branch['fruit']['radius'] *= size
            branch['fruit']['length'] *= size
            branch['fruit']['mass'] *= size**3
    # Keep tissue modulus, trough and truss paths fixed in this morphology study.
    # More material variability requires a separate calibration experiment.
    spec['parameterization'] = {
        'schema_version':1, 'seed':seed, 'split':'representative' if seed is None else 'held-out-morphology',
        'latent_variables':{'size_scale':size,'radial_scale':openness,'azimuth_offset_rad':turn},
        'dependencies':variation['dependencies'], 'distribution_status':variation['status'],
        'config_sha256':hashlib.sha256(Path(config_path).read_bytes()).hexdigest(),
        'roots':{'representation':'fixed crown boundary; root geometry and pullout absent',
                 'validity':'above-ground contact hypothesis only; must test anchorage before transfer'},
    }
    validate(spec)
    return spec


def validate(spec):
    """Reject malformed anatomy/units before passing it to the physics builder."""
    names = [x['id'] for x in spec['leaves']] + [x['id'] for x in spec['truss']]
    if len(set(names)) != len(names):
        raise ValueError('Organ identifiers must be unique')
    known = {'crown'}
    for branch in spec['truss']:
        if branch['parent'] not in known:
            raise ValueError('Truss must be a connected, parent-before-child tree')
        known.add(branch['id'])
        if branch['radius'] <= 0 or np.linalg.norm(branch['unloaded_delta']) <= 0:
            raise ValueError('Nonpositive branch dimensions')
        if 'fruit' in branch and any(branch['fruit'][k] <= 0 for k in ['radius','length','mass']):
            raise ValueError('Nonpositive fruit properties')
    for leaf in spec['leaves']:
        if leaf['length'] <= 0 or leaf['shaft_radius_m'] <= 0:
            raise ValueError('Nonpositive leaf properties')
        points = np.array([[0,0,0],*leaf['growth']['control_points_m'],
                           np.array(leaf['tip'])-spec['crown_m']-np.array(leaf['growth']['attachment_m'])])
        if not np.isfinite(points).all():
            raise ValueError('Nonfinite centerline')
        if np.any(np.diff(points[:,2]) <= 0):
            raise ValueError('This upright-canopy hypothesis requires monotonically rising unloaded control points')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,default=DEFAULT)
    parser.add_argument('--seed',type=int)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(compile_spec(args.config,args.seed),indent=2)+'\n')
    print(args.output)
