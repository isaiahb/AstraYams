"""Inspectable, append-only experiment evidence. No execution or inferred live state."""
from __future__ import annotations
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path

SCHEMA_VERSION = 1

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def artifact(path, root='.'):
    path = Path(path).resolve(); root = Path(root).resolve()
    return {'path': str(path.relative_to(root)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}

def verify_artifact(item, root):
    path = (Path(root) / item['path']).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError('Evidence must remain within repository root')
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
        raise ValueError('Missing or changed evidence: ' + item['path'])

def validate(events, event, root):
    eid, kind, p = event['experiment_id'], event['event_type'], event['payload']
    if not isinstance(eid, str) or not eid.strip(): raise ValueError('experiment_id required')
    previous = [e for e in events if e['experiment_id'] == eid]
    if kind == 'proposal':
        if previous: raise ValueError('Experiment proposal already exists; use a new experiment ID')
        for key in ('hypothesis', 'skill_graph', 'model', 'data', 'training', 'changes', 'evaluation', 'retrospective'):
            if key not in p: raise ValueError('Missing proposal field: ' + key)
        graph = p['skill_graph']; ids = [n['id'] for n in graph['nodes']]
        if not ids or len(ids) != len(set(ids)): raise ValueError('Unique skill nodes required')
        for n in graph['nodes']:
            if n['implementation'] not in ('learned', 'scripted', 'hybrid'): raise ValueError('Explicit skill implementation required')
            if not n.get('inputs'): raise ValueError('Skill input disclosure required')
        for edge in graph['edges']:
            if edge['from'] not in ids or edge['to'] not in ids: raise ValueError('Unknown graph endpoint')
        evaluation = p['evaluation']
        for key in ('thresholds', 'evaluator_sha256', 'seeds', 'split', 'promotion_min_success_rate'):
            if key not in evaluation: raise ValueError('Missing evaluation field: ' + key)
        seeds = evaluation['seeds']
        if len(seeds) != len(set(seeds)): raise ValueError('Duplicate evaluation seeds')
        if set(seeds) & set(p['data'].get('training_seeds', [])): raise ValueError('Train/evaluation seed overlap')
        rate = evaluation['promotion_min_success_rate']
        if rate is not None and not 0 <= rate <= 1: raise ValueError('Invalid promotion rate')
    elif kind == 'result':
        if not previous or previous[0]['event_type'] != 'proposal': raise ValueError('Proposal required first')
        if any(e['event_type'] == 'result' for e in previous): raise ValueError('Immutable result already exists')
        spec = previous[0]['payload']['evaluation']
        if p['evaluation_fingerprint'] != digest(spec): raise ValueError('Evaluation criteria changed')
        if p['seeds'] != spec['seeds']: raise ValueError('Evaluation seed set changed')
        if type(p['episodes']) is not int or type(p['successes']) is not int or not 0 <= p['successes'] <= p['episodes'] or p['episodes'] != len(p['seeds']): raise ValueError('Invalid episode counts')
        if not p.get('evidence'): raise ValueError('Result requires inspectable evidence')
        for item in p['evidence']: verify_artifact(item, root)
    elif kind == 'note':
        if not previous or not p.get('message'): raise ValueError('Notes require an existing experiment and explicit message')
        for item in p.get('evidence', []): verify_artifact(item, root)
    elif kind == 'promotion':
        if not previous: raise ValueError('Proposal required')
        if any(e['event_type'] == 'promotion' for e in previous): raise ValueError('Promotion decision already recorded')
        if p['decision'] not in ('accepted', 'rejected', 'not_evaluated') or not p.get('reason'): raise ValueError('Explicit promotion decision/reason required')
        if p['decision'] == 'accepted':
            if any(e['event_type'] == 'note' and e['payload'].get('blocks_promotion') for e in previous):
                raise ValueError('Experiment has an unresolved promotion-blocking provenance note; use a new prospective experiment')
            proposal = previous[0]['payload']; spec = proposal['evaluation']
            results = [e for e in previous if e['event_type'] == 'result']
            if proposal['retrospective'] or spec['promotion_min_success_rate'] is None or not results: raise ValueError('Acceptance requires prospective threshold and measured result')
            result = results[-1]['payload']
            for item in result['evidence']: verify_artifact(item, root)
            if not spec['evaluator_sha256'] or not spec['thresholds'] or result['episodes'] == 0 or result['successes']/result['episodes'] < spec['promotion_min_success_rate']: raise ValueError('Promotion threshold not met')
            if spec.get('comparison') == 'paired_success_strict_improvement_no_regression':
                pairs = result.get('paired_outcomes', [])
                if [x['seed'] for x in pairs] != spec['seeds'] or any(type(x.get(k)) is not bool for x in pairs for k in ('baseline_success', 'candidate_success')):
                    raise ValueError('Complete paired Boolean outcomes required')
                if sum(x['candidate_success'] for x in pairs) != result['successes']:
                    raise ValueError('Paired result count mismatch')
                if any(x['baseline_success'] and not x['candidate_success'] for x in pairs) or sum(x['candidate_success'] for x in pairs) <= sum(x['baseline_success'] for x in pairs):
                    raise ValueError('No strict paired improvement or a nominal regression')
                if not result.get('baseline_evidence'): raise ValueError('Baseline evidence required')
                for item in result['baseline_evidence']: verify_artifact(item, root)
    else: raise ValueError('Unknown event type')

def read_ledger(path):
    path = Path(path)
    events = []
    if not path.exists(): return events
    for line in path.read_text().splitlines():
        event = json.loads(line); stored = event.pop('sha256')
        if event.get('schema_version') != SCHEMA_VERSION or event['sequence'] != len(events)+1 or event['previous_sha256'] != (events[-1]['sha256'] if events else None) or digest(event) != stored:
            raise ValueError('Ledger hash chain invalid')
        event['sha256'] = stored; events.append(event)
    return events

def append_event(path, experiment_id, event_type, payload, root='.'):
    """Append under advisory file lock. Existing bytes are never rewritten."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        events = read_ledger(path)
        event = {'schema_version': SCHEMA_VERSION, 'sequence': len(events)+1,
                 'previous_sha256': events[-1]['sha256'] if events else None,
                 'recorded_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                 'experiment_id': experiment_id, 'event_type': event_type, 'payload': payload}
        validate(events, event, root); event['sha256'] = digest(event)
        handle.write(json.dumps(event, sort_keys=True, allow_nan=False)+'\n'); handle.flush(); os.fsync(handle.fileno())
        return event

def snapshot(path, root='.'):
    events = read_ledger(path); experiments = {}
    for event in events:
        row = experiments.setdefault(event['experiment_id'], {'experiment_id': event['experiment_id'], 'events': []})
        row['events'].append(event)
        if event['event_type'] == 'note': row.setdefault('notes', []).append(event['payload'])
        else: row[event['event_type']] = event['payload']
    for row in experiments.values():
        row['evidence_integrity'] = 'not_checked'
        if 'result' in row:
            try:
                for item in row['result']['evidence'] + row['result'].get('baseline_evidence', []) + [item for note in row.get('notes', []) for item in note.get('evidence', [])]: verify_artifact(item, root)
                row['evidence_integrity'] = 'verified'
            except (ValueError, OSError): row['evidence_integrity'] = 'missing_or_changed'
        row['observed_status'] = 'decision_recorded' if 'promotion' in row else 'result_recorded' if 'result' in row else 'proposal_recorded'
    return {'schema_version': SCHEMA_VERSION, 'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'ledger_head': events[-1]['sha256'] if events else None, 'event_count': len(events), 'experiments': list(experiments.values()), 'limitations': 'Recorded evidence only; no inferred live activity. Simulation outcomes are not hardware validation. Hash chaining detects edits, not trusted authorship.'}
