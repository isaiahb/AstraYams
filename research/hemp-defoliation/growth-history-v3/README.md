# Growth history v3: persistent bud states

Preserves v2 geometry and its uncalibrated timing. Every modeled true-leaf axil now has a persistent bud record, including nodes outside the existing activation scenario. Buds remain dormant or activate into a linked shoot. Activation eligibility is still the inherited scenario, not measured physiology. This change separates representation from the future activation model; it does not calibrate branch development.

Bud markers are optional enlarged diagnostic geometry, amber dormant and blue active. They are not anatomically sized buds. Inspected the branching-stage three-quarter skeleton and its attached markers in browser. Default canopy dimensions remain unchanged. The canopy's regular narrow shape and lateral leaf-stage reset remain unresolved.

Checks cover parent attachment, monotone activation, activation time preceding appearance, and one active bud per child axis. Final scenario contains 171 bud records: 23 active and 148 dormant. Counts are model outputs, not observations. Existing geometric tests pass. No mechanics or ML introduced.

Research basis and remaining evidence gaps: ../organ-development-v1/REPORT.md. Run check.mjs with Node and publish.py with Python from this directory or repository root.

## Basal growth audit

`node audit-buds.mjs` exports `bud-history-audit.json`, tracing every main-axis bud. The lowest two node ranks are held inactive by the existing scenario; ranks 3–12 are eligible for delayed activation. Thus the absence of growth at the very bottom is authored, not a biological result. “Dormant” currently means model-inactive, not a measured physiological state. Do not add basal growth or calibrate recurrence based on the user's tentative hypothesis. Need same-node longitudinal observations distinguishing initiation, visible outgrowth and subsequent leaf expansion. No geometry changes in this audit.
