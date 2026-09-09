# Environment research and physics record

Every task can publish an inspectable environment study alongside its learned-skill evidence. The Skill Studio **Research & physics** tab reads `environment_study_path` from the task's `demo.json`. Publish this field early; preserve it when results replace the rest of the manifest. Paths are repository-relative, inside the owning project. Prepared examples may point to `assets/workcells/…`.

The authoritative TypeScript contract and publication validator are in `apps/skill-studio/src/environmentStudySchema.ts`. A populated recorded example is `assets/workcells/strawberry-specimen/study.json`. Its generator is `tools/publish_strawberry_study.py`.

## First publication

```json
{
  "schema_version": 1,
  "title": "Environment study",
  "provenance": "current-run",
  "status": "Gathering references",
  "scope": "Task definition; no physical validation or trained execution yet.",
  "objective": "Describe the physical interaction this environment must reproduce.",
  "sources": [],
  "revisions": [],
  "experiments": [],
  "assumptions": [],
  "next_steps": ["Inspect the task inputs and identify observable contact geometry."]
}
```

Write to a temporary file and rename atomically after validating it. The product polls every five seconds. An invalid update retains the last valid record and displays an error. Existing runs without a study show a neutral empty state; the app does not fabricate research for them.

## Evidence loop

1. **Define the interaction.** Freeze success/failure criteria before fitting or training. Describe what is rendered, what collides, what deforms, what is controlled, and what is omitted.
2. **Gather primary references.** Source entries contain a stable ID, title, organ/feature, publisher, URL, optional local image, credit, observation, modeling application and evidence boundary. Attribute owners; linking a source does not grant redistribution rights. AI concept images must be identified as generated and cannot establish physical measurements.
3. **Build one inspectable example.** Distinguish observed topology from inferred hidden connections and assumed dimensions/material parameters. Every physical parameter needs a basis and the consequence of uncertainty. A visual match alone cannot measure stiffness or damping.
4. **Record each material change.** Append a revision containing observation, decision summary, implemented change, evidence, source IDs, disposition and optional before/after and result paths. Keep rejected attempts. `kept` means retained for this study, not approved for deployment. Summarize engineering rationale; do not request or expose private chain-of-thought.
5. **Probe contact separately.** Each experiment gives its question, method, result/control paths, recorded media, metrics, finding and limitation. A completed outcome needs its result artifact. `passed-diagnostic` describes that specific test only. Paired controls should preserve the same initial state and trajectory except the intentionally changed factor. Name incidental contacts and solver penetrations.
6. **Review before expanding.** Retain the checkpoint label, model SHA-256, validation record, and next steps. Calibrate physical parameters against real measurements before claiming real-world fidelity. Expand variation only after one coherent specimen/contact case is credible; vary coupled attributes together.

## Media and provenance

Include both an overview and the changed region. Videos and replays must come from saved simulation states. `replay_path` uses the existing recorded-body-transform format, `robot_instances: []` for isolated specimens, and `allow_explode: false` when an exploded pose would be misleading. A replay is inspectable evidence, not an active physics solver. Keep illustrative animation separate.

`recorded` denotes a saved historical study, not an active agent. `current-run` denotes records published by the current run, not a promise that an agent is still connected. Show the recorded status; do not animate synthetic activity or infer success from elapsed time. The UI is an evidence surface and the prompt is a publication contract; neither independently verifies an agent's measurements or automatically calibrates the simulator.

For strawberry provenance and limitations, see the specimen README and `REALISM-METHOD.md`. The isolated plant diagnostics do not upgrade the separate scripted harvest baseline into a trained or physically validated harvesting policy.
