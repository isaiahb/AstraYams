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
        video = next((a for a in evidence(nominal) if a['path'].endswith('.mp4')), None)
        failed = by_id.get('full-micro-composition-v1', {})
        before = next((a for a in evidence(failed) if a['path'].endswith('seed-2500-replay.mp4')), None)
        hero = '<section class="hero"><p class="eyebrow">CURRENT CHECKPOINT · FROZEN FINAL TEST</p><h1>From grasp to insertion</h1><div class="metrics"><div><strong>'+str(nr['successes'])+'/'+str(nr['episodes'])+'</strong><span>Nominal final seeds</span></div><div><strong>'+str(sr['successes'])+'/'+str(sr['episodes'])+'</strong><span>Stress final seeds</span></div><div><strong>'+esc(f'{count:,}' if count is not None else 'Not recorded')+'</strong><span>Learned parameters</span></div></div><p>Learned grasp → alignment → insertion, with scripted targets, guards and IK. Privileged simulator state; no teacher during execution.</p>'
        if video: hero += '<figure>'+player(video)+'<figcaption>Final nominal replay · exact recorded actions, independently audited</figcaption></figure>'
        if before: hero += '<p><a href="'+href(before)+'">Watch the earlier failed insertion</a> · <a href="#run-full-micro-composition-v1">Inspect its rejected 2/10 result</a></p>'
        hero += '<details><summary>Final test scope and audit details</summary><p>Nominal and stress are separate 20-episode held-out tests. Simulation outcomes are not hardware validation. Replay is not fresh policy inference. No checkpoint changes followed final selection.</p><pre>'+esc(json.dumps({'nominal': nominal, 'stress': stress}, indent=2))+'</pre></details></section>'
    picker = '<label>Find an experiment <select onchange="location.hash=this.value"><option value="">Choose a recorded run</option>'+''.join('<option value="run-'+esc(r['experiment_id'])+'">'+esc(r['experiment_id'])+'</option>' for r in ordered)+'</select></label>'
    cards = []
    for row in ordered:
        p = row['proposal']; r = row.get('result'); decision = row.get('promotion', {})
        status = 'final result recorded' if r and p['evaluation']['split'].startswith('final_') else decision.get('decision', row['observed_status']).replace('_', ' ')
        graph = ' → '.join(n['label']+' ['+n['implementation']+']' for n in p['skill_graph']['nodes'])
        measured = str(r['successes'])+'/'+str(r['episodes'])+' measured successes' if r else 'No result recorded'
        hypothesis = '<p>'+esc(p['hypothesis'])+'</p>' if p.get('hypothesis') else ''
        reason = '<p>'+esc(decision['reason'])+'</p>' if decision.get('reason') else ''
        links = ' · '.join('<a href="'+href(a)+'">'+esc(Path(a['path']).name)+'</a>' for a in evidence(row))
        videos = ''.join('<figure>'+player(a)+'<figcaption>'+esc(Path(a['path']).name)+'</figcaption></figure>' for a in evidence(row) if a['path'].endswith('.mp4'))
        cards.append('<article id="run-'+esc(row['experiment_id'])+'"><div class="runhead"><span class="status '+esc(decision.get('decision', 'recorded'))+'">'+esc(status)+'</span><strong>'+esc(measured)+'</strong></div><h3>'+esc(row['experiment_id'])+'</h3><p class="graph">'+esc(graph)+'</p>'+hypothesis+reason+'<details><summary>Evidence, replay and provenance</summary><p>'+links+'</p>'+videos+'<pre>'+esc(json.dumps(row, indent=2))+'</pre></details></article>')
    css = 'body{font:16px system-ui;background:#10151d;color:#e2eaf2;margin:32px auto;max-width:1040px;padding:0 24px}h1{font-size:36px;margin:8px 0 22px}h3{font-size:19px;margin:14px 0}p{line-height:1.5}a,summary{color:#9ddcf5}summary{cursor:pointer;padding:8px 0}article{border:1px solid #384658;border-radius:12px;padding:20px;margin:16px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}video{width:100%;max-height:500px;background:#05080b;border-radius:10px}figure{margin:18px 0}figcaption,.graph{color:#aebccd;font-size:14px}.eyebrow{font-size:12px;letter-spacing:1.4px;color:#93cfc1}.metrics{display:flex;gap:48px;flex-wrap:wrap}.metrics strong{display:block;font-size:32px}.metrics span{display:block;color:#aebccd;margin-top:4px}.hero{margin-bottom:40px}.runhead{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.status{display:inline-block;padding:6px 10px;border-radius:6px;background:#384658;font-weight:700;text-transform:uppercase;font-size:11px}.accepted{background:#175f4d}.rejected{background:#7d3038}select{padding:10px;max-width:100%;margin:8px}article:target{border-color:#9ddcf5}'
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>AstraFactory skill evidence</title><style>'+css+'</style>'+hero+'<h2>Experiment history</h2><p>Recorded results and decisions, newest first. No inferred live activity.</p>'+picker+''.join(cards)+'<details><summary>Ledger integrity and export metadata</summary><pre>'+esc(json.dumps({k:v for k,v in data.items() if k!='experiments'}, indent=2))+'</pre></details></html>'


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
