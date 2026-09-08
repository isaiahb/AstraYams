# Skill experiment evidence contract

`tools/build_skill_observatory.py` exports `runs/skill-observatory/experiments.json` and a standalone `index.html`. The input `experiments.jsonl` is an append-only ledger. No server, GPU or app change is required. All statuses describe recorded events, never inferred running jobs. Outcomes are simulation evidence, not hardware validation.

```sh
python tools/build_skill_observatory.py --import-existing
python tools/build_skill_observatory.py --event /path/to/event.json
python -m unittest discover -s tests -p 'test_skill_experiments.py'
```

The importer adds each known historical run once. It preserves evidence paths and hashes; historical hypotheses, timing, reward changes and promotion thresholds are unknown unless explicitly present in the source. Import time is not execution time. A historical success cannot be retrospectively promoted through this API. New candidates need new IDs and prospective records.

## Event envelope and generated JSON

Each ledger line has `schema_version: 1`, `sequence`, `previous_sha256`, UTC `recorded_at`, `experiment_id`, `event_type`, `payload`, and `sha256`. Hashes use canonical sorted compact JSON excluding the event's own hash. Append uses an advisory lock and fsync. Existing bytes are never rewritten. Hash chaining detects edits but is not an authenticated signature or write-once storage system.

Generated JSON has `schema_version`, `generated_at`, `ledger_head`, `event_count`, `limitations`, and `experiments`. Each experiment contains its ID, original `events`, `proposal`, optional `result` and `promotion`, `evidence_integrity` (`verified`, `missing_or_changed`, `not_checked`), and `observed_status` (`proposal_recorded`, `result_recorded`, `decision_recorded`). Consumers must display missing/changed evidence and avoid treating old accepted decisions as currently verified if integrity fails.

## Producer API

```python
from astrafactory.skill_experiments import append_event, artifact, digest
ledger = 'runs/skill-observatory/experiments.jsonl'
append_event(ledger, 'grasp-candidate-002', 'proposal', proposal, root='.')
append_event(ledger, 'grasp-candidate-002', 'result', {
    'evaluation_fingerprint': digest(proposal['evaluation']),
    'seeds': proposal['evaluation']['seeds'],
    'episodes': 5, 'successes': 2,
    'evidence': [artifact('runs/candidate-002/report.json')],
    'scope': 'Privileged-state grasp with scripted IK; no insertion policy',
    'physical_validation': False,
})
append_event(ledger, 'grasp-candidate-002', 'promotion', {
    'decision': 'rejected', 'reason': '2/5 is below the frozen promotion threshold',
})
```

The CLI `--event` reads `{experiment_id, event_type, payload}` from a JSON file. Generate the proposal **before training/evaluation**, then append one immutable result and at most one promotion decision. Corrections and repeated evaluations use distinct experiment IDs; do not rewrite or reuse a prior ID. Unknown fields should be null or explicitly described as unknown, never guessed.

Required proposal payload:

```json
{
  "hypothesis": "Explicit experiment hypothesis, not a reconstructed thought process",
  "retrospective": false,
  "skill_graph": {
    "nodes": [{"id": "grasp", "label": "Grasp", "implementation": "hybrid", "inputs": "Privileged pose/contact; learned commands and scripted IK"}],
    "edges": []
  },
  "model": {"parameter_count": 5252, "checkpoint": null, "checkpoint_sha256": null},
  "data": {"training_seeds": [100, 101], "manifest": null, "manifest_sha256": null},
  "training": {"wall_seconds": null, "started_at": null, "finished_at": null, "device": "cpu"},
  "changes": {"reward": null, "domain_randomization": null},
  "evaluation": {
    "thresholds": {"qualified_hold_seconds": 0.5, "rise_m": 0.02},
    "evaluator_sha256": "hash of frozen evaluator/task provenance",
    "seeds": [2000, 2001, 2002, 2003, 2004],
    "split": "development",
    "promotion_min_success_rate": 0.8
  }
}
```

This is a schema example, not a prescribed experiment or a change to the current evaluator. Record the **actual full immutable task acceptance criteria and evaluator hash**. Reward and training randomization changes belong in `changes`; they do not alter `evaluation`. Store model size, data manifest hashes, training seeds, script revisions, timing and hardware when measured. Extra payload fields can preserve run-specific metadata. Graph edges use `from`, `to`, and an explicit `guard`; nodes use `learned`, `scripted`, or `hybrid` and disclose their observation inputs.

Promotion `accepted` requires a prospective proposal, explicit success-rate target, nonempty frozen threshold/evaluator provenance, unchanged evaluation fingerprint and exact seed list, a nonzero measured episode count meeting the target, and currently matching local evidence SHA256. Train/evaluation seed overlap is rejected. `rejected` and `not_evaluated` require an explicit reason. The ledger checks consistency and file integrity; it does not re-execute physics or prove that a producer's counts are truthful. Review the linked source evidence. A development promotion is not a final-test claim.

Artifacts use repository-relative `path`, `sha256` and `bytes`. They must exist under the supplied root when results are appended, and are rechecked on snapshot and acceptance. Immutable external checkpoint/release URLs may be additional model/data fields; they do not replace locally inspectable evaluation evidence. The private draft archive from the completed GPU run remains available separately; no credentials are embedded in records.

For a predeclared paired comparison, set `evaluation.comparison` to `paired_success_strict_improvement_no_regression`. Acceptance additionally requires `result.paired_outcomes` in frozen seed order, with Boolean `baseline_success` and `candidate_success`, plus `baseline_evidence` artifact records. Candidate successes must strictly exceed baseline successes, and no seed successful at baseline may become a failure. Matching totals alone are insufficient. Baseline artifacts are integrity-checked too. If baseline is already perfect, this success-based gate cannot promote; a different metric must be specified prospectively in a new experiment rather than invented after results.

The result may include `training: {wall_seconds, started_at, finished_at, ...}`, checkpoint and source hashes, and other measurements that were unknown when the proposal was registered. The proposal's evaluation specification remains immutable. Evaluation-only proposals for already-frozen checkpoints should explicitly state that training preceded registration; prospective evaluation is not prospective training.

`note` is an additional append-only event for explicit findings and provenance corrections. Its payload requires `message`, may include locally verified `evidence`, and may set `blocks_promotion: true`. A blocking note permanently prevents acceptance of that experiment; it does not rewrite the original proposal or permit changing thresholds. Use a new prospective experiment for corrected criteria. Snapshots preserve every note under `notes`. This is used for the discovered discrepancy between stale task.json descriptions and the actual frozen ContactTask.evaluate implementation.

Source-file preregistration can also be imported: record the original proposal artifact/hash, its producer-confirmed pre-evaluation creation order, and the report's matching proposal hash. The ledger timestamp remains the actual import time. Never backdate events. Explicitly distinguish this method from direct ledger preregistration; an unsourced after-the-fact hypothesis remains retrospective.
