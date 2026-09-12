# Hemp leaf-removal research

Started 2026-09-12 after the user clarified that the prospective design partner works with non-psychoactive hemp.

## Objective

Develop a reference-grounded model of hemp anatomy and mechanics for agricultural leaf-removal robotics in commercial CBD flower production for consumption, as specified by the user. Begin with one inspectable specimen and its contact behavior, then build a task environment and evaluate learned manipulation.

The user has requested all three operations: selected leaf removal on standing plants, large-leaf removal from cut branches, and fine leaf trimming around harvested flowers. Cultivar, specimen condition at each operation, removal methods, robot, and acceptance criteria remain unspecified. The initial robotics tasks can use externally designated target leaves so that selection and manipulation can be evaluated separately.

## Contents

- [Indoor whole-plant context](indoor/README.md) — current visual model
- [Whole-plant anatomy study](whole-plant/ANATOMY.md) — preserved isolated specimen
- [Partner task brief](TASK-BRIEF.md)
- [First morphology diagnostic and rejected physics candidate](diagnostics/README.md)
- [Model and validation plan](MODEL-PLAN.md)
- [Source register](sources.json)
- [Specimen record template](specimen.template.json)
- [Earlier anatomy literature](../cannabis-anatomy/ANATOMY-NOTES.md)
- [Reusable realism methodology](../../docs/simulation/REALISM-METHOD.md)

## First deliverable

Current user direction: a complete plant, with an inspectable hierarchy from roots through stems, nodes, branches, leaves and flower structures. The whole-plant anatomy study supersedes an isolated leaf as the visible deliverable. Later contact diagnostics must remain traceable to this complete anatomical context.

The model must distinguish the stem, leaf stalk, individual leaflets, midribs, and their attachment regions. Their mass and mechanical properties are separate quantities. The specimen template leaves unsupported values empty; an empty value is unknown, never zero.

## Current status

The workspace contains a whole-plant static anatomy candidate, plus the preserved measured-outline diagnostic and rejected elastic-shell candidate. The new model separates leaflet surfaces and retains organ parents and attachment locations. It has no calibrated physics, trained policy or validated removal tool. No strawberry material values have been transferred.

The reusable assets are the evidence ledger, contact accounting, matched control experiments, replay approach, numerical convergence checks, and policy evaluation methodology. Hemp geometry and material behavior need their own evidence.

The next anatomy work is matching complete-plant structure, branching and node geometry against representative specimens. Partner photos and examples of the three manual operations will be needed to establish task constraints; neither is present in this folder.
