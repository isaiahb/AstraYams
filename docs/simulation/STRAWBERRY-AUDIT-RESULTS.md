# Contact audit results

Six four-second diagnostics from frozen v8 rest positions; 0.5 ms timestep. All completed without physics warnings. This is not real-world validation.

| Trial | Outcome | Peak probe force (N) | Max probe penetration (mm) |
|---|---|---:|---:|
| leaf | Target missed | 0.299 | 1.492 |
| stalk | Incidental contacts; not isolated | 0.128 | 4.842 |
| berry | Target contact confirmed; uncalibrated | 0.393 | 0.431 |

All negative controls reported zero probe contacts. The leaf approach is not a successful isolated leaf test. The stalk trial exposes excessive incidental foliage penetration that needs investigation before promotion. The berry trial contacts only its intended berry.

Separate canopy rest-angle candidate: eight seconds without physics warnings. Last-second fruit-coordinate span: 0.04277459922621962 mm. This does not measure leaf settling or validate contact response.

Next: collision overlay and thin-leaf collision decomposition/solver sensitivity; revise approach clearance and repeat the unchanged target tests. Match leaflet shape and orientation to a coherent reference specimen. Do not simply remove collision masks to obtain a pass.
