"""Generate convex contact components from the actual tool/jaw surfaces.

Approximation is explicit, with source hashes and parameters. This does not
calibrate friction, stiffness or contact-force response.
"""
from pathlib import Path
import argparse
import hashlib
import json
import time
import xml.etree.ElementTree as E
import coacd
import trimesh


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, default=Path('runs/tower-lift-v8'))
    args = parser.parse_args()
    run = args.run.resolve()
    out = run / 'contact-meshes'
    out.mkdir(exist_ok=True)
    root = E.parse(run / 'so101/scene.xml').getroot()
    names = ['wrist_roll_follower_so101_v1', 'moving_jaw_so101_v1',
             'pack_net_frame', 'pack_net_retainer']
    records = []
    coacd.set_log_level('warn')
    for name in names:
        asset = root.find(f"asset/mesh[@name='{name}']")
        source = Path(asset.get('file'))
        mesh = trimesh.load(source, force='mesh')
        if asset.get('scale'):
            mesh.apply_scale([float(x) for x in asset.get('scale').split()])
        params = dict(threshold=.0005, real_metric=True, max_convex_hull=48,
                      resolution=2000, mcts_nodes=12, mcts_iterations=40,
                      mcts_max_depth=3, seed=180, preprocess_mode='auto')
        start = time.monotonic()
        pieces = coacd.run_coacd(coacd.Mesh(mesh.vertices, mesh.faces), **params)
        files = []
        for i, (vertices, faces) in enumerate(pieces):
            path = out / f'{name}-{i}.stl'
            trimesh.Trimesh(vertices=vertices, faces=faces).export(path)
            files.append(path.name)
        record = dict(name=name, source=str(source),
                      source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                      input_watertight=bool(mesh.is_watertight),
                      parameters=params, wall_s=time.monotonic()-start, parts=files)
        records.append(record)
        print(name, len(files), round(record['wall_s'], 1), flush=True)
        (out / 'manifest.json').write_text(json.dumps(dict(
            method='CoACD collision-aware convex decomposition; 0.5 mm target, not an error guarantee',
            source='https://github.com/SarahWeiii/CoACD', records=records), indent=2)+'\n')


if __name__ == '__main__':
    main()
