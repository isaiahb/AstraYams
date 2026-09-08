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
