# Hemp leaf-removal research

Started 2026-09-12 after the user clarified that the prospective design partner works with non-psychoactive hemp.

## Objective

Develop a reference-grounded model of living hemp anatomy and mechanics for agricultural leaf-removal robotics. Begin with one inspectable specimen and its contact behavior, then build a task environment and evaluate learned manipulation.

The partner's purpose, cultivar, plant stage, removal method, robot, and acceptance criteria are still unspecified. These affect the model; none has been silently selected. The initial robotics task can use an externally designated target leaf so that leaf selection and manipulation can be evaluated separately.

## Contents

- [Model and validation plan](MODEL-PLAN.md)
- [Source register](sources.json)
- [Specimen record template](specimen.template.json)
- [Earlier anatomy literature](../cannabis-anatomy/ANATOMY-NOTES.md)
- [Reusable realism methodology](../../docs/simulation/REALISM-METHOD.md)

## First deliverable

One stem section containing a visible node, petiole, compound leaf, and neighboring protected structures. Review it beside photographs from comparable viewpoints, then show contact, release, and recovery with collision overlays and an orbitable replay.

The model must distinguish the stem, leaf stalk, individual leaflets, midribs, and their attachment regions. Their mass and mechanical properties are separate quantities. The specimen template leaves unsupported values empty; an empty value is unknown, never zero.

## Current status

This checkpoint establishes the research workspace and engineering plan. There is no hemp mesh, calibrated simulator, trained policy, or validated removal tool yet. No strawberry material values have been transferred.

The reusable assets are the evidence ledger, contact accounting, matched control experiments, replay approach, numerical convergence checks, and policy evaluation methodology. Hemp geometry and material behavior need their own evidence.

The next input that materially changes the work is the partner's task description. Representative photos and an example of the existing manual operation would ground the specimen and tool requirements; neither is present in this folder.
