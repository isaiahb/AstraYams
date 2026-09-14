"""A reversible foliage addition to photo-fit-v1; no image fitting or inference.

Uses the original generator's geometric routines only. Importing that module
loads its small reference image; its expensive fitting/main routine is not run.
Generated additions are hypotheses, not a measured cultivar distribution.
"""
from pathlib import Path
import importlib.util
import json
import hashlib
import shutil
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / 'runs/hemp-foliage-density-v1'
SOURCE = HERE.parent / 'photo-fit-v1/build.py'
spec = importlib.util.spec_from_file_location('photo_geometry', SOURCE)
geo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geo)


def additions():
    axes, lookup = geo.topology()
    rng = np.random.default_rng(913)
    shoots, leaves = [], []
    # Interior nodes only: retain the original tips, main silhouette and leaves.
    # Distribute shoots in depth as well as across the frontal image plane.
    for i, parent in enumerate(axes):
        if parent['parent'] != 'main':
            continue
        for node in range(1, len(parent['nodes']) - 1):
            origin = parent['nodes'][node]
            tangent = geo.unit(parent['nodes'][node + 1] - parent['nodes'][node - 1])
            sign = 1 if (i + node) % 2 else -1
            lateral = geo.unit(np.cross(tangent, [0, 0, 1])) * sign
            direction = geo.unit(.25 * tangent + .70 * lateral + np.array([0, 0, .8]))
            length = float(rng.uniform(.10, .17) * (1.1 - .27 * origin[2] / geo.HEIGHT))
            nodes = np.array([origin + length * (direction * t + np.array([0, 0, .12]) * t*t)
                              for t in np.linspace(0, 1, 4)])
            aid = f"{parent['id']}/density-{node}"
            shoot = dict(id=aid, parent=parent['id'], node=node, nodes=nodes,
                         points=geo.curve(nodes), r0=parent['r0']*.42, r1=parent['r0']*.12)
            shoots.append(shoot)
            for k, at in enumerate(nodes[1:], 1):
                # Basal leaves are larger; smaller terminal leaves preserve a tip.
                theta = i * 2.399 + node * 1.13 + k * 2.399
                d = geo.unit([np.cos(theta), np.sin(theta)*.65, rng.uniform(-.18, .28)])
                size = float(rng.uniform(.057, .077) * (1 - .16 * (k-1)))
                petiole = float(rng.uniform(.026, .042))
                leaves.append(dict(id=f'{aid}/leaf-{k}', axis=aid, node=k, at=at,
                                   junction=at+d*petiole, direction=d, length=size,
                                   observed=False, n=5 if k < 3 else 3,
                                   twist=float(rng.uniform(-.35, .35)), tone=float(rng.uniform(.88, 1.10))))
    return axes, lookup, shoots, leaves


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    baseline_path = ROOT/'runs/hemp-photo-fit-v1/shape-constrained.json'
    baseline = json.loads(baseline_path.read_text())
    original, lookup, shoots, leaves = additions()
    all_axes = {**lookup, **{a['id']: a for a in shoots}}
    errors = [np.linalg.norm(a['nodes'][0]-all_axes[a['parent']]['nodes'][a['node']]) for a in shoots]
    errors += [np.linalg.norm(l['at']-all_axes[l['axis']]['nodes'][l['node']]) for l in leaves]
    assert max(errors, default=0) < 1e-10
    parts = geo.build_mesh(shoots, leaves, baseline['parameters'])
    existing = {p['id'] for p in baseline['parts']}
    ids = existing | {p['id'] for p in parts}
    assert len(ids) == len(existing)+len(parts)
    assert all(p['parent'] in ids for p in parts)
    assert all(np.isfinite(p['positions']).all() for p in parts)
    assert all(0 <= j < len(p['positions'])//3 for p in parts for j in p['indices'])
    # Baseline is referenced unchanged; this file contains only additions.
    data = dict(parts=parts, axes=[{k: a[k].tolist() if isinstance(a[k], np.ndarray) else a[k]
                    for k in ('id','parent','node','nodes','r0','r1')} for a in shoots],
                leaves=[{k: l[k].tolist() if isinstance(l[k], np.ndarray) else l[k]
                    for k in ('id','axis','node','at','junction','length','n')} for l in leaves])
    (OUT/'additions.json').write_text(json.dumps(data, separators=(',', ':'), allow_nan=False))
    report = dict(baseline='/runs/hemp-photo-fit-v1/shape-constrained.json',
                  baseline_sha256=hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
                  baseline_leaves=len(baseline['leaves']), added_leaves=len(leaves),
                  total_leaves=len(baseline['leaves'])+len(leaves),
                  baseline_axes=len(baseline['axes']), added_axes=len(shoots),
                  max_attachment_error_m=float(max(errors)), seed=913,
                  physics='Static connected geometry; no new collision, stiffness, growth or damage validation.',
                  evidence='Added shoots and leaf counts are an explicit visual hypothesis, not measured commercial-plant data.')
    for path in (OUT/'checks.json', HERE/'checks.json'):
        path.write_text(json.dumps(report, indent=2)+'\n')
    for name in ('index.html', 'viewer.js'):
        shutil.copy2(HERE/name, OUT/name)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
