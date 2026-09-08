"""Import measured legacy runs, append explicit events, and export an offline report."""
import argparse
import html
import json
import os
from pathlib import Path
from astrafactory.skill_experiments import append_event, artifact, digest, read_ledger, snapshot


def import_existing(ledger, root):
    existing = {e['experiment_id'] for e in read_ledger(ledger)}
    sources = [('small-grasp-v1', 'runs/small-grasp-v1/report.json', False),
               ('small-hybrid-composition-v1', 'docs/evidence/skill-composition/small-hybrid-composition-v1.json', True),
               ('hybrid-composition-v1', 'docs/evidence/skill-composition/hybrid-composition-v1.json', True)]
    for eid, relative, hybrid in sources:
        source = root / relative
        if eid in existing or not source.exists(): continue
        report = json.loads(source.read_text())
        tiny = eid != 'hybrid-composition-v1'
        seeds = [report['seed']] if hybrid else [t['seed'] for t in report['trials']]
        successes = int(report['success']) if hybrid else report['handoff_successes']
        nodes = [{'id': 'grasp', 'implementation': 'hybrid' if tiny else 'learned',
                  'label': 'Tiny learned grasp with scripted IK' if tiny else 'SmolVLA grasp',
                  'inputs': report.get('learned_inputs', '12 privileged simulator pose/contact values')}]
        edges = []
        if hybrid:
            nodes.extend({'id': x, 'implementation': 'scripted', 'label': 'Pose-feedback '+x, 'inputs': 'Privileged simulator pose'} for x in ('transport', 'insertion'))
            edges = [{'from': 'grasp', 'to': 'transport', 'guard': report.get('handoffs', [{}])[0].get('guard', 'See source report')}, {'from': 'transport', 'to': 'insertion', 'guard': 'Measured overhead socket alignment'}]
        thresholds = {'recorded_handoff': report.get('handoff')} if not hybrid else {'source_task_hashes': report.get('task_hashes'), 'recorded_handoff_guards': [h['guard'] for h in report.get('handoffs', [])]}
        proposal = {'hypothesis': None, 'hypothesis_note': 'Historical import: no pre-registered hypothesis recovered; no reasoning reconstructed.',
                    'retrospective': True, 'skill_graph': {'nodes': nodes, 'edges': edges},
                    'model': {'parameter_count': 5252 if tiny else None, 'parameter_count_provenance': 'Recorded run description; not recounted during import' if tiny else 'Not recovered', 'checkpoint': report.get('learned_component', 'runs/small-grasp-v1/policy.pt'), 'checkpoint_sha256': report.get('checkpoint_sha256')},
                    'data': {'training_seeds': [e['seed'] for e in report.get('episodes', []) if e['split'] == 'train'], 'episodes': report.get('episodes', []), 'unknown_for_composition': hybrid},
                    'training': {'wall_seconds': None, 'note': 'Timing not recorded in source report', 'history': report.get('history', [])},
                    'changes': {'reward': None, 'domain_randomization': None, 'note': 'No changes inferred from historical artifacts'},
                    'evaluation': {'thresholds': thresholds, 'evaluator_sha256': digest(report.get('task_hashes', {})), 'seeds': seeds, 'split': 'development', 'promotion_min_success_rate': None}}
        append_event(ledger, eid, 'proposal', proposal, root)
        append_event(ledger, eid, 'result', {'evaluation_fingerprint': digest(proposal['evaluation']), 'seeds': seeds, 'episodes': len(seeds), 'successes': successes, 'evidence': [artifact(source, root)], 'scope': report.get('scope', report.get('label')), 'physical_validation': False}, root)
        append_event(ledger, eid, 'promotion', {'decision': 'not_evaluated', 'reason': 'Retrospective development evidence; no pre-registered promotion criterion. Single-seed composition does not establish robust or fully learned assembly.'}, root)


def render(data, root, out):
    esc = lambda x: html.escape(str(x))
    def href(item): return esc(os.path.relpath(root/item['path'], out))
    def evidence(row):
        items = row.get('result', {}).get('evidence', []) + [a for n in row.get('notes', []) for a in n.get('evidence', [])]
        return list({a['path']: a for a in items}.values())
    def player(item):
        return '<video controls preload="metadata" src="'+href(item)+'"></video>'
    ordered = sorted(data['experiments'], key=lambda row: row['events'][-1]['sequence'], reverse=True)
    by_id = {r['experiment_id']: r for r in ordered}
    nominal = by_id.get('full-micro-composition-v3-final-nominal')
    stress = by_id.get('full-micro-composition-v3-final-stress')
    hero = ''
    if nominal and stress and nominal.get('result') and stress.get('result'):
        nr, sr = nominal['result'], stress['result']
        count = nominal['proposal']['model'].get('parameter_count')
        nominal_video = next((a for a in evidence(nominal) if a['path'].endswith('.mp4')), None)
        layout = by_id.get('skill-layout-cases-v1', {})
        layout_video = next((a for a in evidence(layout) if a['path'].endswith('four-physical-generalization-trials.mp4')), None)
        video = layout_video or nominal_video
        failed = by_id.get('full-micro-composition-v1', {})
        before = next((a for a in evidence(failed) if a['path'].endswith('seed-2500-replay.mp4')), None)
        hero = '<section class="hero"><p class="eyebrow">CURRENT CHECKPOINT · FROZEN FINAL TEST</p><h1>From grasp to insertion</h1><div class="metrics"><div><strong>'+str(nr['successes'])+'/'+str(nr['episodes'])+'</strong><span>Nominal final seeds</span></div><div><strong>'+str(sr['successes'])+'/'+str(sr['episodes'])+'</strong><span>Stress final seeds</span></div><div><strong>'+esc(f'{count:,}' if count is not None else 'Not recorded')+'</strong><span>Learned parameters</span></div></div><p>Learned grasp → alignment → insertion, with scripted targets, guards and IK. Privileged simulator state; no teacher during execution.</p>'
        if layout_video:
            hero = hero.replace('CURRENT CHECKPOINT · FROZEN FINAL TEST', 'CURRENT CHECKPOINT · SAME WEIGHTS, DIFFERENT LAYOUTS').replace('From grasp to insertion', 'Watch the frozen skills transfer')
            hero += '<p><strong>6/6 named layout cases succeeded.</strong> Four audited replays shown: peg offsets ±30 mm, socket offsets ±40 mm and vertical key rotations ±30°. Same peg/socket geometry; these are not tilted holes.</p>'
        if video: hero += '<figure>'+player(video)+'<figcaption>'+('Four contrasting layouts · exact recorded actions, independently audited' if layout_video else 'Final nominal replay · exact recorded actions, independently audited')+'</figcaption></figure>'
        if layout_video and nominal_video: hero += '<p><a href="'+href(nominal_video)+'">Watch the original final nominal replay</a> · <a href="#run-skill-layout-cases-v1">Inspect all six named cases</a></p>'
        if before: hero += '<p><a href="'+href(before)+'">Watch the earlier failed insertion</a> · <a href="#run-full-micro-composition-v1">Inspect its rejected 2/10 result</a></p>'
        hero += '<details><summary>Final test scope and audit details</summary><p>Nominal and stress are separate 20-episode held-out tests. Simulation outcomes are not hardware validation. Replay is not fresh policy inference. No checkpoint changes followed final selection.</p><pre>'+esc(json.dumps({'nominal': nominal, 'stress': stress}, indent=2))+'</pre></details></section>'
    visual_hero = ''
    visual = by_id.get('visual-student-v1-8episodes-retention-trained')
    blank = by_id.get('visual-student-v1-8episodes-retention-blank-camera')
    initial = by_id.get('visual-student-v1-8episodes-retention-untrained')
    if visual and visual.get('result'):
        result = visual['result']; video = next((a for a in evidence(visual) if a['path'].endswith('sensor-video.mp4')), None)
        metrics = []
        for label, row in [('Trained RGB + proprio', visual), ('Blank-camera control', blank), ('Untrained control', initial)]:
            if row and row.get('result'):
                r=row['result'];metrics.append('<div><strong>'+str(r['successes'])+'/'+str(r['episodes'])+'</strong><span>'+esc(label)+'</span></div>')
        visual_hero = '<section class="hero"><p class="eyebrow">FIRST VISUAL PICKUP EXPERIMENT</p><h1>Sensor boundary passed.<br>Pickup milestone failed.</h1><div class="metrics">'+''.join(metrics)+'</div><p>The student receives two fixed RGB views plus joint and controller feedback. Its '+f"{result['model']['parameter_count']:,}"+'-parameter network trained for '+f"{result['training']['wall_seconds']:.1f}"+' s on eight demonstrations. All five trained trials ended at the original force limit, with no validated pickup; the paired controls also failed.</p><p>The actual checkpoint passed the independent oracle-poison and fixed-reset audits. That software check is separate from control success: visual pickup, full visual assembly and hardware transfer are not demonstrated. Final test seeds remain untouched.</p>'
        if video: visual_hero += '<figure>'+player(video)+'<figcaption>Actual two-camera student inputs · first trained trial, seed 21000 · failed pickup</figcaption></figure>'
        visual_hero += '<p><a href="#run-visual-student-v1-8episodes-retention-trained">Inspect failed candidate and audits</a> · <a href="#run-visual-student-v1-8episodes-retention-blank-camera">Inspect blank-camera control</a></p><details><summary>Student sensor contract and evidence</summary><p>RGB[2,160,160,3] + measured q7/qd7/commanded targets7/previous actions7. No object pose, contact-force or task-phase input; no runtime teacher or IK. Hardware calibration, timing and gripper mapping remain unvalidated.</p><pre>'+esc(json.dumps(visual,indent=2))+'</pre></details></section>'
        hero='<h2>Earlier privileged-state chain — separate scope</h2>'+hero.replace('<h1>','<h2>').replace('</h1>','</h2>')
    challenge_rows = []
    for row in ordered:
        if not row['experiment_id'].startswith('skill-generalization-v1-'): continue
        spec = row['proposal']['evaluation']; ranges = spec['randomization']; result = row.get('result')
        outcome = str(result['successes'])+'/'+str(result['episodes']) if result else 'No result recorded'
        pose = max(abs(x) for x in ranges['peg_xy_uniform_m'])*1000
        yaw = max(abs(x) for x in ranges['shared_yaw_uniform_rad'])
        independent = max(abs(x) for x in ranges['additional_socket_yaw_rad'])
        condition = f"Peg/socket XY ±{pose:g} mm; shared yaw ±{yaw:g} rad; extra socket yaw ±{independent:g} rad"
        dynamics = f"Mass/inertia {ranges['peg_mass_inertia_scale'][0]:g}–{ranges['peg_mass_inertia_scale'][1]:g}×; friction {ranges['sliding_friction_scale'][0]:g}–{ranges['sliding_friction_scale'][1]:g}×"
        challenge_rows.append('<tr><td><a href="#run-'+esc(row['experiment_id'])+'">'+esc(spec['profile'].replace('_',' '))+'</a></td><td><strong>'+esc(outcome)+'</strong></td><td>'+esc(condition)+'<br>'+esc(dynamics)+'</td></tr>')
    challenges = ''
    if challenge_rows:
        challenges = '<section><h2>How far does the frozen skill transfer?</h2><p>Same keyed peg and socket geometry. These wider pose and dynamics challenges test robustness without retraining; they do not establish generalization to new parts or hardware.</p><div class="tablewrap"><table><thead><tr><th>Challenge</th><th>Measured success</th><th>Reset conditions</th></tr></thead><tbody>'+''.join(reversed(challenge_rows))+'</tbody></table></div></section>'
    timing = ''
    benchmark = by_id.get('micro-grasp-device-benchmark', {}).get('result')
    large = by_id.get('micro-grasp-device-benchmark-batch4096', {}).get('result')
    if benchmark:
        rows = []
        for batch, item in [(512, benchmark), (4096, large)]:
            if not item: continue
            med = item['timing_medians']; cpu = med['cpu']['resident_update_seconds']; gpu = med['mps']['resident_update_seconds']
            winner = f"CPU {gpu/cpu:.2f}× faster" if cpu < gpu else f"MPS {cpu/gpu:.2f}× faster"
            rows.append(f"<tr><td>{batch}</td><td>{cpu:.3f} s</td><td>{gpu:.3f} s</td><td>{winner}</td></tr>")
        timing = '<section><h2>CPU or GPU? The measured workload matters.</h2><p>Actual micro-grasp training data on an Apple M4 Pro: two-thread CPU versus local Apple MPS GPU. Identical initialized weights and batch sequences; 400 total updates across two 1,540-parameter specialists.</p><table><thead><tr><th>Batch size</th><th>CPU median</th><th>MPS median</th><th>Resident-update result</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table><p>Three repeats after warmup, with GPU synchronization. Allocation, transfers and optimizer setup are measured separately in the source report. Changing batch size measures throughput, not policy quality.</p><p>The original local loop took '+f"{benchmark['original_measured_loop']['total_seconds']:.2f}"+' s, including '+f"{benchmark['original_measured_loop']['training_seconds']:.2f}"+' s training. Rollout work includes both IK/controller computation and CPU physics/evaluation; moving only the network to a GPU would not move all of that work.</p><p>No A100 timing or end-to-end cloud speedup was measured. SmolVLA training is a different workload. <a href="#run-micro-grasp-device-benchmark">Inspect raw timings and rollout profile</a>.</p></section>'
    picker = '<label>Find an experiment <select onchange="location.hash=this.value"><option value="">Choose a recorded run</option>'+''.join('<option value="run-'+esc(r['experiment_id'])+'">'+esc(r['experiment_id'])+'</option>' for r in ordered)+'</select></label>'
    cards = []
    for row in ordered:
        p = row['proposal']; r = row.get('result'); decision = row.get('promotion', {})
        status = 'final result recorded' if r and p['evaluation']['split'].startswith('final_') else decision.get('decision', row['observed_status']).replace('_', ' ')
        graph = ' → '.join(n['label']+' ['+n['implementation']+']' for n in p['skill_graph']['nodes'])
        measured = ('Local CPU/MPS timing measurement' if r.get('measurement_type') == 'timing_benchmark' else str(r['successes'])+'/'+str(r['episodes'])+' measured successes') if r else 'No result recorded'
        hypothesis = '<p>'+esc(p['hypothesis'])+'</p>' if p.get('hypothesis') else ''
        reason = '<p>'+esc(decision['reason'])+'</p>' if decision.get('reason') else ''
        links = ' · '.join('<a href="'+href(a)+'">'+esc(Path(a['path']).name)+'</a>' for a in evidence(row))
        videos = ''.join('<figure>'+player(a)+'<figcaption>'+esc(Path(a['path']).name)+'</figcaption></figure>' for a in evidence(row) if a['path'].endswith('.mp4'))
        cards.append('<article id="run-'+esc(row['experiment_id'])+'"><div class="runhead"><span class="status '+esc(decision.get('decision', 'recorded'))+'">'+esc(status)+'</span><strong>'+esc(measured)+'</strong></div><h3>'+esc(row['experiment_id'])+'</h3><p class="graph">'+esc(graph)+'</p>'+hypothesis+reason+'<details><summary>Evidence, replay and provenance</summary><p>'+links+'</p>'+videos+'<pre>'+esc(json.dumps(row, indent=2))+'</pre></details></article>')
    css = 'body{font:16px system-ui;background:#10151d;color:#e2eaf2;margin:32px auto;max-width:1040px;padding:0 24px}h1{font-size:36px;margin:8px 0 22px}h3{font-size:19px;margin:14px 0}p{line-height:1.5}a,summary{color:#9ddcf5}summary{cursor:pointer;padding:8px 0}article{border:1px solid #384658;border-radius:12px;padding:20px;margin:16px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}video{width:100%;max-height:500px;background:#05080b;border-radius:10px}figure{margin:18px 0}figcaption,.graph{color:#aebccd;font-size:14px}.eyebrow{font-size:12px;letter-spacing:1.4px;color:#93cfc1}.metrics{display:flex;gap:48px;flex-wrap:wrap}.metrics strong{display:block;font-size:32px}.metrics span{display:block;color:#aebccd;margin-top:4px}.hero{margin-bottom:40px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:12px;border-bottom:1px solid #384658;vertical-align:top}.tablewrap{overflow:auto}section{margin-bottom:36px}.runhead{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.status{display:inline-block;padding:6px 10px;border-radius:6px;background:#384658;font-weight:700;text-transform:uppercase;font-size:11px}.accepted{background:#175f4d}.rejected{background:#7d3038}select{padding:10px;max-width:100%;margin:8px}article:target{border-color:#9ddcf5}'
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>AstraFactory skill evidence</title><style>'+css+'</style>'+visual_hero+hero+challenges+timing+'<h2>Experiment history</h2><p>Recorded results and decisions, newest first. No inferred live activity.</p>'+picker+''.join(cards)+'<details><summary>Ledger integrity and export metadata</summary><pre>'+esc(json.dumps({k:v for k,v in data.items() if k!='experiments'}, indent=2))+'</pre></details></html>'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--ledger', type=Path, default=Path('runs/skill-observatory/experiments.jsonl'))
    p.add_argument('--out', type=Path, default=Path('runs/skill-observatory'))
    p.add_argument('--import-existing', action='store_true')
    p.add_argument('--event', type=Path, help='JSON with experiment_id, event_type, payload to append')
    a = p.parse_args(); root = a.root.resolve()
    ledger = a.ledger if a.ledger.is_absolute() else root/a.ledger
    out = a.out if a.out.is_absolute() else root/a.out
    if a.import_existing: import_existing(ledger, root)
    if a.event:
        e = json.loads(a.event.read_text()); append_event(ledger, e['experiment_id'], e['event_type'], e['payload'], root)
    data = snapshot(ledger, root); out.mkdir(parents=True, exist_ok=True)
    (out/'experiments.json').write_text(json.dumps(data, indent=2)+'\n')
    (out/'index.html').write_text(render(data, root, out))
    print(json.dumps({'experiments': len(data['experiments']), 'events': data['event_count'], 'json': str(out/'experiments.json'), 'report': str(out/'index.html')}))

if __name__ == '__main__': main()
