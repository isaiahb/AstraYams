"""Read recorded physics; export timing and sampled motion without rerunning it."""
import argparse
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np

from astrafactory.harvest_timing import summarize_timing


def audit(run):
    episodes = []
    model = mujoco.MjModel.from_xml_path(str((run / 'task/scene.xml').resolve()))
    for path in sorted(run.glob('episode-*.json')):
        payload = json.loads(path.read_text())
        result, trace = payload['result'], payload['trace']
        with np.load(path.with_suffix('.npz')) as z:
            t, v = z['t'], z['qvel']
            if len(t) != len(trace) + 1 or v.shape != (len(t), model.nv):
                raise ValueError(f'{path}: recording/model shape mismatch')
            if not np.allclose(t[1:], [r['sim_s'] for r in trace]):
                raise ValueError(f'{path}: trace/physics clock mismatch')
            if not np.isfinite(v).all() or not np.all(np.diff(t) > 0):
                raise ValueError(f'{path}: invalid state/clock')
            arms = {}
            for label, prefix, key in [('catcher', '', 'catch_targets'),
                                       ('cutter', 'cut_', 'cut_targets')]:
                ids = [int(model.joint(f'{prefix}joint{i}').dofadr[0]) for i in range(1, 7)]
                speeds = np.abs(v[:, ids])
                rates = np.diff(z[key], axis=0) / np.diff(t)[:, None]
                arms[label] = dict(
                    sampled_peak_joint_speed_rad_s=float(speeds.max()),
                    sampled_p95_max_joint_speed_rad_s=float(np.quantile(speeds.max(axis=1), .95)),
                    peak_recorded_target_slew_rad_s=float(np.abs(rates).max()),
                    joint_travel_rad_per_joint=np.trapezoid(speeds, t, axis=0).tolist(),
                )
            episodes.append(dict(
                recording=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                physics_sha256=hashlib.sha256(path.with_suffix('.npz').read_bytes()).hexdigest(),
                controller=result.get('controller'), seed=result.get('seed'),
                timing=summarize_timing(trace, result, float(t[0])), arms=arms,
                motion_scope='Recorded 50 Hz samples can miss between-sample peaks. '
                             'Joint-target slew is not actual joint speed or a hardware safety limit.',
            ))
    if not episodes:
        raise ValueError(f'No episodes in {run}')
    return dict(run=str(run), episodes=episodes)


def plot(report, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    episodes = [(Path(r['run']).name, e) for r in report for e in r['episodes']]
    palette = ['#257b83', '#719876', '#d4a04a', '#926b9d', '#b96554']
    fig, axes = plt.subplots(len(episodes), 1, figsize=(11, 3.0 * len(episodes) + 1), squeeze=False)
    for ax, (name, e) in zip(axes[:, 0], episodes):
        timing = e['timing']
        for i, phase in enumerate(timing['phases']):
            x, duration = phase['start_s'], phase['duration_s']
            ax.barh(0, duration, left=x, height=.5, color=palette[i % len(palette)])
            label = f"{phase['phase'].replace('_', ' ')}: {duration:.2f}s"
            ax.text(.01 + .245 * i, -.66, label, transform=ax.transAxes, fontsize=9,
                    color=palette[i % len(palette)])
        for key, label in [('cut_s', 'Cut'), ('first_sustained_net_retention_s', 'Caught'),
                           ('first_settled_placement_s', 'Settled')]:
            value = timing[key]
            if key == 'first_sustained_net_retention_s' and timing['cut_s'] is None:
                continue  # Already caught at reset: do not label verification as a new catch.
            if value is not None:
                ax.axvline(value, color='#25353c', linestyle='--', linewidth=1)
                ax.text(value, .35, f'{label} {value:.2f}s', fontsize=9, ha='center')
        ax.set_xlim(0, max(20, timing['elapsed_s'] + 1)); ax.set_ylim(-.5, .65)
        ax.set_yticks([]); ax.set_xlabel('Elapsed simulation seconds (1× playback)', fontsize=9)
        provenance = 'Scripted; starts with caught fruit' if 'Scripted' in (e['controller'] or '') else 'PPO chain'
        ax.set_title(provenance + ' · ' + name + '\n' +
                     ('Harvest to placement completed' if timing['full_harvest_completed']
                      else 'Full harvest cycle not demonstrated'), loc='left', fontsize=10)
        for spine in ['left', 'right', 'top']:
            ax.spines[spine].set_visible(False)
    fig.suptitle('Where the recorded time goes', x=.075, ha='left', fontsize=18, weight='bold')
    fig.subplots_adjust(top=.79, bottom=.20, left=.075, right=.975, hspace=2.2)
    fig.savefig(path, dpi=160, facecolor='#fbfbf7'); plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runs', nargs='+', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report = [audit(run) for run in args.runs]
    (args.out / 'timing.json').write_text(json.dumps(report, indent=2) + '\n')
    plot(report, args.out / 'timing.png')
    print(json.dumps(report, indent=2))
