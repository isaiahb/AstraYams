# AstraFactory UX exploration

Started 2026-09-08 19:42 UTC. Bounded exploration until 20:42 UTC while the user is away.

## Agreed direction

- Prompt-driven home plus visual project catalog.
- The project, rather than its org chart, is the primary object.
- Explicit disciplines: ID, ME, EE, software, manufacturing, robotics.
- Research/spikes happen throughout each discipline, triggered by uncertainty.
- ID includes generated concept images and form CAD. ME owns detailed functional CAD. The transition must remain inspectable.
- Teams are proposed for a bounded scope. Users can adjust them without managing an org chart.
- Central artifact canvas with a persistent project-lead conversation; deeper team details on demand.
- Hackathon story culminates in a robot learning an assembly using the designed geometry. Mockup states must not masquerade as experiment evidence.

## Design questions being resolved

1. Can people distinguish the discipline from the kind of artifact without two competing progress bars?
2. Does research stay connected to a question, decision, and acceptance test?
3. Can people inspect image → form CAD → detailed CAD without implying automatic geometric correctness?
4. Can a proposed handoff show protected constraints, unresolved assumptions, and downstream impact?
5. Can owners work in parallel without UI treating all disciplines as sequential stages?
6. Are team size and resource budget clear before an execution decision?

## Iteration 1

The earlier workspace was calm but hid too much behind Engineer. Replace its global stage bar with workstream navigation. Use an artifact trail within a discipline. Represent research as a first-class artifact and a contextual spike, not an initial stage that disappears.

Next prototype: a sensor-pod enclosure is an illustrative example, chosen to make ID, ME, EE and assembly handoffs visible. This is not a change to the actual hackathon task or a validated product design.

## Iteration 2 — discipline/artifact workspace

- Added `workspace-v3.html`, a self-contained, non-production UI study with inline assets.
- Explicit ID/ME/EE/SW/manufacturing/robotics workstreams; artifact trails differ by discipline.
- ID uses a real image-generated concept sheet. CAD and engineering representations are explicitly schematic, not claimed as generated/validated engineering assets.
- Added an ID → ME handoff preview showing included artifacts, protected intent, and unresolved questions.
- Research spike creation retains the question and its originating artifact in the discipline's research view for this page session.
- Team proposals belong to a workstream; assignment state no longer bleeds between disciplines.
- Replaced verbose repeated rail status labels with simple discipline names after visual inspection.
- Browser checks: ID concepts render, create spike → close → Research retains its linked question; ID handoff opens ME Packaging; team assignment updates the displayed team state.
- Host preview does not reliably dispatch native form submit events. Explicit button click handling fixed spike submission. Check remaining home/chat form actions in the next iteration.

## Next iteration priorities

1. Home and chat submission behavior; per-project state isolation in mock catalog.
2. Preserve team preferences and accurately reflect generalist versus specialist choices.
3. Make artifact versions / upstream changes concrete without cluttering the default view.
4. Research provenance: question → finding → decision → evidence, with missing sources clearly pending.
5. Inspect 1024px and narrower layouts and dark appearance.
6. Distinguish ME Packaging from Detailed CAD (currently share a schematic illustration).

Current inline preview: `/Users/isaiah/.codex/visualizations/2026/09/08/01a0822a-02ec-7c12-a11a-3a9fd5df3f9a/discipline-workspace.html`.
Standalone browser wrapper: `/tmp/af-discipline-preview.html`, served by the local preview server at port 59112. Regenerate via visualize skill render.py with --force after edits.

## Iteration 3 — behavior and project isolation

Preserved v3; new checkpoint `workspace-v4.html` and inline `discipline-workspace-v4.html`.

- Project catalog remembers each project's selected workstream/artifact, research spikes, concept selection, team preference, and assignment state during this page session.
- New project prompt and project conversation now use verified click handlers in the inline host.
- Selecting a lean team updates roles, tradeoff explanation, and team count. Reassigning the team respects that choice. ID specialist proposal now explicitly includes a reviewer.
- Removed sensor-pod imagery from other example projects. Empty artifact slots and project-specific names make unfinished work honest.
- Browser verified: select lean ID team → assign → switch to gripper → return to sensor pod preserves `Team · 1 assigned`; new project prompt opens its own Brief; handoff and research flows remain in the prototype.
- Corrected sample sensor-pod names/questions bleeding into a newly created project's brief and research.

Next: source/evidence provenance, version changes and handoff impact; distinguish detailed CAD from packaging; responsive appearance checks. Current best preview is v4. Do not edit v3.

## Iteration 4 — simplify the default workspace

Responds to Isaiah's latest feedback: easier to understand, less confusing.

- Preserved v4; v5 defaults to Focus view with a plain-language next decision, one primary artifact action, and a short artifact history labeled with its discipline owner.
- Full ID/ME/EE/etc workspace remains available under All work. This preserves the requested detail rather than replacing it with a generic Engineer stage.
- Research remains reachable as Explore alternatives next to the artifact's conversation. Goals and acceptance details stay collapsed.
- Developing a selected image now opens a concrete next-step proposal (inputs, deliverable, check) before navigating to a clearly labeled schematic CAD preview.
- Main image height constrained so the next action is easier to find; removed repeated concept-selection instructions in Astra's conversation.
- Browser verified: Develop concept A → proposed form CAD step → All work retains Industrial design / Form CAD context.
- Home hides project-only team/mode controls.

Current best: `workspace-v5.html`; inline `focused-workspace-v5.html`. Next passes: version/provenance detail and handoff change impact, then responsive QA. Focus view should remain simple as details are added.

## Iteration 5 — simulation as a shared engineering loop

Latest user steering supersedes the generic robot-test endpoint and preference for hiding the sidebar: restore the workstream sidebar by default. Keep Focus view optional.

- Preserved v5; v6 defaults to the project catalog with Sensor pod, Modular robot arm, and Lunar mass driver example projects.
- Restored explicit workstream rail. Replaced ROB/Robot test with Simulation & analysis: Question → Model → Experiment → Feedback.
- Added illustrative project-specific robot-arm and lunar mass-driver schematics and simulation questions. These are study placeholders, not actual engineered CAD or validated analyses.
- Simulation feedback explicitly distinguishes geometry, controller, and modeling issues; proposed owner routing changes by project.
- Robot-arm feedback opens ME Detailed CAD and leaves a link back to the originating finding. Lunar concept feedback opens EE architecture with ME involvement explained.
- Browser verified: robot-arm catalog → Simulation → Feedback → change proposal → ME, with backlink and pending-investigation note.
- Home now hides the previous project's title and project-specific controls.

Current best: `workspace-v6.html`, inline `simulation-workspace-v6.html`. Next pass should deepen artifact/provenance and revision comparison while keeping the sidebar and task-specific simulation. Do not revert to a fixed Robot test endpoint.
