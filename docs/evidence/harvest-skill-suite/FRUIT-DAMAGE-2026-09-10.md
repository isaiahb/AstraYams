# Fruit damage validation: measured progress

Design: [research, fixtures, model architecture and validation protocol](../../simulation/FRUIT-DAMAGE-VALIDATION.md).
Machine-readable plan: [fruit-damage-protocol.json](../../simulation/fruit-damage-protocol.json).
Local visual review: `runs/fruit-damage-validation/v1/index.html` (server port 8793).
Tracked measurement receipt: [source hashes, exact replay checks, contact exposures
and convergence results](fruit-damage-results-2026-09-10.json).

## What changed

An observational contact recorder measures every fruit's flesh and calyx/other
contacts at every physics step. It includes fruit–fruit and fruit–calyx contacts,
textile contacts, sustained exposure and repeated contact onsets. Existing reward,
forces, collision filters, termination criteria and policy weights are unchanged.
Pressure, tissue energy, damage probability and bruise volume remain unknown.

The replay footer now calls its old contact category **tool/net→neighbor**. It
never covered all plant–plant contacts; those are measured by the new observer.
Natural resting contacts should not automatically be classified as damage.

## Exact recorded-command reproduction

- `learned-command-replay-v2`: 0–13.2 s of the five-PPO partial-chain-v6 motor
  targets, finite motors and full plant/net dynamics. qpos, qvel and equality-state
  arrays match the source **bit-for-bit** across this window. The cut occurs at
  9.48725 s. Largest individual target-flesh/net normal contact: **6.649 N** at
  11.858125 s. Target-calyx/net point peak: **5.593 N**. This is not a bruise score.
- `basket-command-replay-v2`: all 15.68 s from basket-commission-v8, starting
  already caught. The same three physical-state arrays match **bit-for-bit**.
  Largest individual flesh/net contact: **2.625 N**; flesh/rim point contact:
  **0.310 N**; calyx/basket-liner point contact: **0.355 N**. The prior final-placement
  score could not represent these earlier net/rim contacts. This remains scripted
  commissioning, not a learned complete harvest.
- Neighboring fruit have resting and manipulation-associated fruit–fruit/calyx
  contacts. The largest 0.780 N point contact occurs during the first 6.625 ms of
  the recorded window; it must not be described as a later cutter strike.

`contact-exposure.json` contains scalar force exposure by surface/counterpart and
`contact-samples.npz` contains integration-rate time series. Source JSON and NPZ
hashes are included. No accepted source recordings were overwritten.

## Numerical validation: failed

Paired catch windows start at source time 9.32 s from identical qpos, qvel,
equality state and explicitly zeroed solver warm start (verified combined hash).
Motor targets and contact parameters match; timesteps are 0.125 and 0.0625 ms.
Both windows end at 13.2 s. The old recording lacks the historical solver warm
start; therefore these controlled window restarts are distinct experiments from
the exact full-start reproduction above.

| Check | Coarse | Fine | Difference relative to larger magnitude | Gate |
| --- | ---: | ---: | ---: | --- |
| Flesh/net largest point force | 3.096 N | 2.071 N | 33.10% | Fail, 10% |
| Flesh/net normal impulse | 0.15506 Ns | 0.17704 Ns | 12.41% | Fail, 5% |
| Calyx/net largest point force | 0.09571 N | 0.17081 N | 43.97% | Fail, 10% |
| Calyx/net normal impulse | 0.07294 Ns | 0.05487 Ns | 24.77% | Fail, 5% |

Maximum difference between paired fruit-origin paths is **9.811 mm**, exceeding
the proposed 1 mm gate. Loaded durations differ by under 2%, which does not rescue
the force/path failures. Contact topology and solver/restart sensitivity need
investigation before fitting tissue mechanics to these loads. This evidence does
not establish which timestep is closer to physical truth.

Earlier restart trials that retained reset-derived warm starts are preserved as
`catch-window-coarse/fine`; they are not the controlled paired result. Initial
instrumentation trials stopped on a missing MuJoCo flex-name accessor; they
produced no accepted force reports and remain in their original folders. The
corrected observer uses `mj_id2name` and has a flexible-strand regression test.

## Checks completed and what remains

Five measurement tests pass: known-mass static impulse, free-flight/nonmutation
and duplicate-clock checks, flexible-strand contact attribution, both sides of
fruit-to-fruit contact, and opposing compression that must not cancel. These are
instrument checks, not biological fruit validation. The chart and orbitable catch
were inspected. Sources and protocols distinguish actual findings from proposed
physical test settings; no equipment purchase or physical fruit test occurred.

Next work: isolate the dynamic-net catch in a smaller fixture, improve numerical
convergence without tuning away force spikes, and compare realistic strand/rim
support geometries. Tissue calibration then needs measured force–indentation,
patch/recovery and delayed damage observations on identified fruit. Do not replace
the current proxy score with invented damage probabilities in the meantime.
