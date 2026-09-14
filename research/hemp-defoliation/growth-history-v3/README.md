# Growth history v3: persistent bud states

Preserves v2 geometry and its uncalibrated timing. Every modeled true-leaf axil now has a persistent bud record, including nodes outside the existing activation scenario. Buds remain dormant or activate into a linked shoot. Activation eligibility is still the inherited scenario, not measured physiology. This change separates representation from the future activation model; it does not calibrate branch development.

Bud markers are optional enlarged diagnostic geometry, amber dormant and blue active. They are not anatomically sized buds. Inspected the branching-stage three-quarter skeleton and its attached markers in browser. Default canopy dimensions remain unchanged. The canopy's regular narrow shape and lateral leaf-stage reset remain unresolved.

Checks cover parent attachment, monotone activation, activation time preceding appearance, and one active bud per child axis. Final scenario contains 171 bud records: 23 active and 148 dormant. Counts are model outputs, not observations. Existing geometric tests pass. No mechanics or ML introduced.

Research basis and remaining evidence gaps: ../organ-development-v1/REPORT.md. Run check.mjs with Node and publish.py with Python from this directory or repository root.
