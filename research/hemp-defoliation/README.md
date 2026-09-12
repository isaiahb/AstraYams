# Hemp leaf-removal research

Started 2026-09-12 after the user clarified that the prospective design partner works with non-psychoactive hemp.

## Objective

Develop a reference-grounded model of hemp anatomy and mechanics for agricultural leaf-removal robotics in commercial CBD flower production for consumption, as specified by the user. Begin with one inspectable specimen and its contact behavior, then build a task environment and evaluate learned manipulation.

The user has requested all three operations: selected leaf removal on standing plants, large-leaf removal from cut branches, and fine leaf trimming around harvested flowers. Cultivar, specimen condition at each operation, removal methods, robot, and acceptance criteria remain unspecified. The initial robotics tasks can use externally designated target leaves so that selection and manipulation can be evaluated separately.

## Contents

- [Partner task brief](TASK-BRIEF.md)
- [First morphology diagnostic and rejected physics candidate](diagnostics/README.md)
- [Model and validation plan](MODEL-PLAN.md)
- [Source register](sources.json)
- [Specimen record template](specimen.template.json)
- [Earlier anatomy literature](../cannabis-anatomy/ANATOMY-NOTES.md)
- [Reusable realism methodology](../../docs/simulation/REALISM-METHOD.md)

## First deliverable

One stem section containing a visible node, petiole, compound leaf, and neighboring protected structures. Review it beside photographs from comparable viewpoints, then show contact, release, and recovery with collision overlays and an orbitable replay.

The model must distinguish the stem, leaf stalk, individual leaflets, midribs, and their attachment regions. Their mass and mechanical properties are separate quantities. The specimen template leaves unsupported values empty; an empty value is unknown, never zero.

## Current status

The workspace contains a measured-outline geometry diagnostic and a rejected elastic-shell candidate. The candidate has both numerical stability and leaflet-topology problems; it is not a valid task environment. There is no calibrated simulator, trained policy, or validated removal tool yet. No strawberry material values have been transferred.

The reusable assets are the evidence ledger, contact accounting, matched control experiments, replay approach, numerical convergence checks, and policy evaluation methodology. Hemp geometry and material behavior need their own evidence.

The next anatomy work is separating individual leaflet surfaces and their attachments using the published landmarks, with hidden portions labeled as inferred. Partner photos and examples of the three manual operations will be needed to establish representative anatomy and task constraints; neither is present in this folder.
