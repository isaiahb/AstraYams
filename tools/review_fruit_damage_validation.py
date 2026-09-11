"""Research review from measured contacts and a controlled timestep comparison."""
import argparse
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mujoco
import numpy as np


def load(root, name):
    return json.loads((root / name / 'contact-exposure.json').read_text())


def compare(root):
    names = ['catch-paired-coarse', 'catch-paired-fine']
    reports = [load(root, n) for n in names]
    assert reports[0]['initial_state_sha256'] == reports[1]['initial_state_sha256']
    groups = []
    for surface in ['flesh', 'calyx']:
        pairs = [next(p for p in r['pairs'] if p['fruit'] == 'fruit_secondary_b'
                      and p['surface'] == surface and p['counterpart'] == 'flex:catcher_net')
                 for r in reports]
        checks = {}
        for metric, limit in [('normal_impulse_Ns', .05), ('peak_point_normal_N', .10),
                              ('contact_duration_s', .05)]:
            a, b = [p[metric] for p in pairs]
            absolute = abs(a - b)
            relative = absolute / max(abs(a), abs(b), 1e-12)
            allowed = max(limit * max(abs(a), abs(b)),
                          2 * reports[1]['timestep_s'] if metric == 'contact_duration_s' else 0.)
            checks[metric] = dict(coarse=a, fine=b, relative_difference=relative,
                                  limit=limit, passed=absolute <= allowed)
        groups.append(dict(surface=surface, counterpart='flex:catcher_net', checks=checks))
    m = mujoco.MjModel.from_xml_path(str((root / names[0] / 'task/scene.xml').resolve()))
    data = [mujoco.MjData(m), mujoco.MjData(m)]
    z = [np.load(next((root / n).glob('episode-*.npz'))) for n in names]
    np.testing.assert_allclose(z[0]['t'], z[1]['t'])
    body = m.body('fruit_secondary_b').id; distances = []
    for i in range(len(z[0]['t'])):
        for d, recording in zip(data, z):
            d.qpos[:] = recording['qpos'][i]; mujoco.mj_kinematics(m, d)
        distances.append(float(np.linalg.norm(data[0].xpos[body] - data[1].xpos[body])))
    peak = max(distances)
    return dict(status='PASS' if peak <= .001 and all(c['passed'] for g in groups for c in g['checks'].values())
                else 'FAIL', scope='Numerical contact convergence, not biological validation',
                initial_state_sha256=reports[0]['initial_state_sha256'],
                timesteps_s=[r['timestep_s'] for r in reports],
                peak_target_origin_path_difference_m=peak, path_limit_m=.001, contacts=groups,
                protocol='Thresholds proposed in docs/simulation/fruit-damage-protocol.json; no retuning.')


def figures(root, reports, convergence):
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex='col', sharey='row')
    for col, (name, title) in enumerate([
            ('learned-command-replay-v2', 'Cut and catch · replayed PPO motor targets'),
            ('basket-command-replay-v2', 'Basket transfer · scripted motor targets')]):
        report = reports[name]
        s = np.load(root / name / 'contact-samples.npz')['samples']
        names = report['sample_columns']
        def series(fruit, key): return s[:, names.index(fruit + '/' + key)]
        axes[0, col].plot(s[:, 0], series('fruit_secondary_b', 'flesh_sum_normal_N'), color='#236d79', label='Fruit flesh')
        axes[0, col].plot(s[:, 0], series('fruit_secondary_b', 'calyx_or_other_sum_normal_N'), color='#d28c38', label='Calyx / other')
        for fruit, color in [('fruit_primary', '#9a4861'), ('fruit_secondary_a', '#70669c'), ('fruit_green', '#60964c')]:
            if fruit in report['fruit_bodies']:
                axes[1, col].plot(s[:, 0], series(fruit, 'flesh_sum_normal_N'), color=color, label=fruit.replace('fruit_', ''))
        axes[0, col].set_title(title, fontsize=11)
        for ax in axes[:, col]:
            ax.set_ylabel('Sum of normal force (N)'); ax.grid(alpha=.15); ax.legend(fontsize=8)
            ax.set_ylim(bottom=0)
            ax.spines[['top', 'right']].set_visible(False)
        axes[1, col].set_xlabel('Elapsed simulation seconds'); axes[1, col].set_title('Neighboring fruit flesh contacts', fontsize=10)
    # Fix shared limits only after both episodes are drawn. Fixing the first
    # panel early disables autoscaling and can hide a later, larger impact.
    for row in axes:
        maximum = max(float(np.max(line.get_ydata())) for ax in row for line in ax.lines)
        row[0].set_ylim(0, max(maximum * 1.08, 1e-6))
    fig.suptitle('Contact exposure across the whole handling sequence', fontsize=17, weight='bold')
    fig.text(.5, .015, 'Separate episodes; basket starts already caught · every physics step sampled · not bruise predictions', ha='center', fontsize=10)
    fig.tight_layout(rect=[0, .04, 1, .94]); fig.savefig(root / 'contact-history.png', dpi=150); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, key, title in zip(axes, ['peak_point_normal_N', 'normal_impulse_Ns'],
                              ['Largest individual net contact (N)', 'Net normal impulse (N·s)']):
        x = np.arange(2)
        for i, (field, label, color) in enumerate([('coarse', 'dt = 0.125 ms', '#236d79'),
                                                  ('fine', 'dt = 0.0625 ms', '#db9450')]):
            vals = [g['checks'][key][field] for g in convergence['contacts']]
            ax.bar(x + (i - .5) * .34, vals, width=.34, label=label, color=color)
        ax.set_xticks(x, ['Flesh', 'Calyx']); ax.set_title(title, fontsize=11)
        ax.spines[['top', 'right']].set_visible(False); ax.legend(fontsize=8)
    fig.suptitle('Timestep check: ' + convergence['status'] + ' · force estimates need more work', fontsize=15)
    fig.tight_layout(rect=[0, 0, 1, .9]); fig.savefig(root / 'convergence.png', dpi=150); plt.close(fig)


def main(root):
    reports = {n: load(root, n) for n in ['learned-command-replay-v2', 'basket-command-replay-v2']}
    comparison = compare(root); figures(root, reports, comparison)
    (root / 'convergence.json').write_text(json.dumps(comparison, indent=2) + '\n')
    cards = []
    for name, r in reports.items():
        rows = ''.join('<tr>' + ''.join(f'<td>{html.escape(str(v))}</td>' for v in
            [p['fruit'], p['surface'], p['counterpart'], f"{p['peak_point_normal_N']:.3f}",
             f"{p['contact_duration_s']:.3f}", f"{p['normal_impulse_Ns']:.4f}"]) + '</tr>' for p in r['pairs'][:10])
        cards.append(f'''<details><summary>{html.escape(name)} · contact measurements</summary>
        <p>Peak target-origin deviation from original recording: {r['peak_target_origin_drift_from_source_m']*1000:.4f} mm.</p>
        <table><thead><tr><th>Fruit</th><th>Surface</th><th>Counterpart</th><th>Peak point N</th><th>Loaded seconds</th><th>Impulse Ns</th></tr></thead><tbody>{rows}</tbody></table>
        <a href="{name}/contact-exposure.json">Full measurement report</a></details>''')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Fruit damage validation · research bench</title><style>
    body{font:17px/1.55 system-ui;background:#f4f4ec;color:#263a3a;max-width:1160px;margin:auto;padding:32px}h1{font-size:42px;line-height:1.15;margin:.2em 0}h2{margin-top:2em}a{color:#17616c}img{width:100%;border-radius:14px}iframe{width:100%;height:790px;border:1px solid #a8b5ae;border-radius:16px} .status{background:#f2d7bc;padding:15px;border-radius:12px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.card,details{background:white;padding:20px;border-radius:14px}small{color:#4f625c}table{border-collapse:collapse;font-size:13px;width:100%}td,th{text-align:left;border-bottom:1px solid #ddd;padding:7px}details{margin:15px 0;overflow:auto}summary{cursor:pointer;font-weight:600}@media(max-width:750px){.grid{grid-template-columns:1fr}}</style>
    <small>ASTRAFACTORY / MANUAL RESEARCH & SIMULATION REVIEW</small><h1>Can the fruit survive the handling?</h1>
    <p>Research → contact measurements → numerical verification → physical fruit tests → calibrated training model.</p>
    <p class="status"><b>Damage verdict: UNKNOWN.</b> We measured simulated contact exposure. Biological damage is not calibrated, and the paired timestep check failed. A gentle final landing cannot establish that earlier handling was gentle.</p>
    <div class="grid"><section class="card"><b>Impact</b><p>Measure the catch, rim strikes and berry-to-berry collisions. Fit receiver and tissue compliance separately.</p></section>
    <section class="card"><b>Squeezing & rubbing</b><p>Measure local loading, duration, indentation, recovery and sliding. A narrow strand can concentrate load.</p></section>
    <section class="card"><b>Hidden damage</b><p>Use controls, blinded inspection and separate fruit for destructive 24 h / 48 h endpoints. No physical trials completed.</p></section></div>
    <h2>Recorded physical contact histories</h2><p>All fruit are monitored; flesh and calyx are distinct. Initial resting contacts are included. These curves show simulated forces, not a damage score.</p><img src="contact-history.png" alt="Measured full-rate fruit contact forces during catching and placing">
    <h2>Does the measurement survive a smaller timestep?</h2><p>Same recorded initial physical state and zeroed solver warm start; unchanged motor targets and contact parameters. No retuning to pass.</p><img src="convergence.png" alt="Contact convergence comparison">
    <p>Maximum difference between paired fruit-origin paths: PATH_MM mm (proposed limit 1 mm). <a href="convergence.json">Full convergence checks</a>.</p>
    <h2>Inspect the catch in 3D</h2><p>Orbit, pan and scrub the recorded simulation. This is motor-target replay with finite physics, not a new policy-training result. No visible bruise overlay has been invented.</p>
    <iframe src="learned-command-replay-v2/review/index.html" title="Orbitable instrumented harvest replay"></iframe>
    <h2>From force to validated fruit damage</h2><ol><li>Test actual net strands, rim and liner against measured fruit; record force, indentation and recovery.</li><li>Check fresh and delayed damage against untouched and sham-handled controls.</li><li>Fit a local tissue/contact model and test withheld fruit and harvest batches.</li><li>Use a fast calibrated approximation for PPO training, with uncertainty and out-of-domain abstention.</li></ol>
    <p><a href="../../../docs/simulation/FRUIT-DAMAGE-VALIDATION.md">Engineering design and research</a> · <a href="../../../docs/simulation/fruit-damage-protocol.json">Machine-readable experiment protocol</a></p>
    <p>Research: <a href="https://doi.org/10.1590/S0103-90162008000500007">Ferreira et al. 2008</a> · <a href="https://doi.org/10.1111/j.1745-4603.1982.tb00888.x">Holt & Schoorl</a> · <a href="https://doi.org/10.21273/HORTSCI.44.7.1953">Temperature and loading mode</a> · <a href="https://doi.org/10.1016/j.compag.2024.109588">Local FE and damage modeling</a>.</p>
    CARDS</html>'''
    page = page.replace('PATH_MM', f"{comparison['peak_target_origin_path_difference_m']*1000:.2f}").replace('CARDS', '\n'.join(cards))
    (root / 'index.html').write_text(page)
    print(json.dumps(comparison, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--root', type=Path, default=Path('runs/fruit-damage-validation/v1'))
    main(parser.parse_args().root)
