# Partner task brief

Updated 2026-09-12 from the user's clarification.

## Confirmed by the user

- Crop: non-psychoactive hemp.
- Application: a commercial grower producing CBD flowers for consumption.
- Requested automation: the grower's defoliation process.
- Project objective: research anatomy and mechanics, then build a useful robot-learning simulation.

## Three requested operations

The user confirmed all three of the following operations. Each needs a separate task definition and evaluation, sharing anatomical assets where appropriate:

| Requested operation | Consequence for the model |
|---|---|
| Selected leaf removal from a standing plant | Include the supporting plant, connected branches, neighboring leaves, and attachment compliance |
| Large-leaf removal from harvested branches | Include how the branch is held or fixtured, its condition, and support contacts |
| Small-leaf trimming around harvested flowers | Include local flower/leaf geometry, delicate contact, and the actual trimming interface |

These are all in project scope. Their ordering and the condition of the material at each stage remain partner-specific. No removal schedule, target selection rule, tool mechanism, or material parameters have been chosen. Reuse geometry where justified, but do not reuse living-tissue properties for dried material without evidence.

## Engineering decisions that can proceed

Maintain organ-level identification, geometry provenance, contact accounting, and separate measured versus assumed properties. Preserve raw specimen condition and anatomical context. Start with the stem/petiole/leaf component diagnostic, then build the standing-plant task, branch-handling task, and flower-trimming task. This implementation order is an engineering proposal, not the partner's production sequence.

## Remaining partner-specific information

Cultivar and specimen condition at each stage; what is removed and protected; how a human currently performs each operation; robot and tool constraints; observed failure modes; quality acceptance criteria; and cycle time. These remain unknown, rather than a generic commercial standard.
