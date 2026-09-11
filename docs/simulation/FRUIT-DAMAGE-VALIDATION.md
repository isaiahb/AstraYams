# Strawberry damage: simulation engineering and validation design

Revision 1, 2026-09-10. Status: research and measurement instrumentation; **no
biologically calibrated damage predictor or physical fruit tests completed**.
Desktop product/UI work stays paused. Existing physics and acceptance criteria
are preserved. The aim is to choose faster, gentler manipulation by measuring the
load history of every contacted fruit, then testing whether it predicts damage.

## Research and what it permits us to infer

| Primary source | Relevant observation | Design consequence and limit |
| --- | --- | --- |
| [Ferreira et al., 2008, *Strawberry fruit resistance to simulated handling*](https://doi.org/10.1590/S0103-90162008000500007), [full paper](https://revistas.usp.br/sa/en/article/download/22326/24350/25958) | Compared impact, drop and compression in three ripe cultivars. The compression fixture used a 15 mm convex probe, 9.8 N and 2 s; a preliminary 5 s treatment caused more injury. Fruit was inspected after 24–48 h at 24°C / 90–95% RH and sectioned to measure internal bruises. | Include load duration, tool shape and delayed internal inspection. Those deliberately injurious treatments are reference experiments, not safe-force limits. Keep drop and pendulum results separate. |
| [Holt & Schoorl, *Strawberry bruising and energy dissipation*](https://doi.org/10.1111/j.1745-4603.1982.tb00888.x) | Two cultivars differed; absorbed energy correlated with bruise volume, but slow compression and impact had different responses. | Keep loading mode and cultivar in the model. External robot work or incoming kinetic energy is not automatically energy absorbed by fruit tissue. Abstract-level evidence, not a digitized material fit. |
| [Ferreira et al., 2009, *Strawberry Bruising Sensitivity Depends on the Type of Force Applied, Cooling Method, and Pulp Temperature*](https://doi.org/10.21273/HORTSCI.44.7.1953) | Cooling reduced compression susceptibility but increased impact susceptibility in the reported conditions; cooling method also mattered. | Temperature cannot be represented by a universal “colder = safer” multiplier. Publisher full text was blocked; the authored abstract is reproduced in [the bibliographic record](https://cir.nii.ac.jp/crid/1360298345552489344). |
| [*Determination and quantitative evaluation of early postharvest hidden damage…*, 2024](https://doi.org/10.1016/j.compag.2024.109588) | Combined physical material testing, explicit finite-element dynamics and an empirical response surface; varied contact material, drop height and angle. | Supports fitting a fast predictor from a separately validated local mechanical model. Published abstract inspected; reported accuracy under its particular tested conditions is not accuracy for our net, tool or fruit. |
| [*Strain-rate dependent dynamic damage behavior of strawberries*, 2026](https://www.sciencedirect.com/science/article/pii/S0260877426001895) | Reports rate-dependent response; central-pith Young's modulus increased from 0.53 to 1.61 MPa across 1–7 mm/s loading rates. | Do not assign one constant modulus to the entire berry, or transfer pith parameters to skin, flesh or stalk. Accessible publisher summary only; specimen details/raw data are not available here. |

These studies motivate experiments. They do not establish a universal safe force,
pressure, speed, drop height or damage probability for our strawberries. The
current catch/placement loads also differ from many published laboratory loads;
extrapolating downward and calling the result harmless would be unjustified.

## Missing measurements in the current scene

The fruit body is rigid. Its mesh gives shape and inertia, but does not resolve
flesh compression, skin rupture, achenes concentrating contact, viscoelasticity or
bruising. The flexible net represents the net, not the tissue underneath it.
The current basket score considers the first basket impact and its aftermath; it
cannot account for all prior loads in the net, frictional rubbing or neighboring
fruit. A final gentle placement cannot undo earlier damage.

MuJoCo exposes contact forces in a contact frame through
[`mj_contactForce`](https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html#mj-contactforce).
Its [soft-contact model](https://mujoco.readthedocs.io/en/stable/computation/index.html#contact)
does not turn solver overlap into a calibrated tissue indentation or provide a
measured contact patch. Dividing force by an arbitrary triangle area would invent
pressure. Summing opposing force vectors would conceal squeezing.

## Implemented now: exposure measurements

`FruitContactAudit` observes each integration step without changing forces,
positions, velocities, reward or termination. It records:

- Fruit identity; flesh versus calyx/other surface; contacting geom or textile.
- Sum of compressive normal forces, largest individual contact force, tangential
  force magnitude, accumulated normal/tangential impulse, loaded duration and
  contact onsets. Onset counts may include numerical chatter.
- Peak contact position in world and fruit-body coordinates, and solver overlap
  separately from biological deformation.
- All fruit–fruit contacts attributed to both affected fruit; these cannot then
  be summed as total dissipated energy.

Damage probability, bruise volume, tissue-absorbed energy and pressure are **null**.
The 1 µN detection floor only suppresses numerical zero; it is not a damage limit.
Whole-episode exposure must persist across PPO handoffs. Resting force is retained
as a measurement, not automatically penalized as accumulated damage.

`probe_fruit_contact_exposure.py` re-simulates saved motor targets in the complete
plant/textile scene. It injects the initial recorded state once, records trajectory
drift against the source, and never overwrites the source episode. This is
instrumented command replay, not a fresh closed-loop PPO success. Full-rate
measurements cannot be reconstructed reliably from 50 Hz playback frames.

## Physical test fixtures and their simulation twins

The dimensions and ranges below are **proposed fixture settings**, not published
safe limits. Use the actual CAD net, rim, liner and blade-edge samples wherever
possible; record measured strand diameter, pretension, edge radius and cushioning
thickness. Do not replace those surfaces with flat plates in the final validation.

| Test | Fixture/control | Record | Hypothesis it can reject |
| --- | --- | --- | --- |
| Instrument verification | Known mass on force plate; free flight; opposing loads; two-fruit contact | Signed/vector and scalar forces, impulse, clock, fruit attribution | Missing short impacts, force cancellation, double-counted duration, observer changing physics |
| Drop/catch | Release one fruit above actual net, liner, rigid rim and another supported fruit; start at 5/15/30 mm gaps | Synchronized force/deflection, approach/rebound velocities, contact footprint, fruit rotation | Low final basket impact means the whole harvest was gentle; net and tissue absorb the same energy |
| Compression and recovery | Rounded indenter, actual strand sample and rim sample; force ramps initially 0.1/0.3/1 N, holds 0.1/1/5 s, unload | Force–indentation curve, hold creep, recovery, loaded patch and residual shape | The same total force is equivalent on a broad support and a narrow strand; slower is always safer |
| Skin abrasion / puncture | Rounded edge or strand sliding under measured normal load; separate actual blade edge test | Tangential load/displacement, surface microscopy/photographs, rupture and leakage | Normal impulse alone predicts skin damage |
| Repeated exposure | One impact versus repeated smaller contacts; sustained basket load; changing fruit orientation | Complete history and spatial overlap of contact sites | Damage resets between skills, or is just a maximum force |
| End-to-end withheld test | Harvest, transfer, release and retrieve; empty and partly occupied basket | All fruit condition before/after, cycle time, delayed hidden damage | Component-level success guarantees the composed policy or protects previously collected berries |

Measure drop gap from the lowest fruit surface to the receiver, not from its COM.
For a prescribed example 20 g fruit, 5/15/30 mm gravitational gaps correspond to
0.981/2.943/5.886 mJ of potential energy. These are setup calculations, not tissue
damage thresholds. Receiver deformation, fruit rebound and rotation share energy.

Use a stiff, calibrated load cell behind the interchangeable contact fixture,
synchronized displacement sensing and a side camera; sample force initially at
10 kHz with anti-aliasing, then establish adequate sensor bandwidth/convergence
from the measured impact spectrum. Slow-motion phone video can show trajectory
and recovery but may miss peak force and contact duration. Use a macro view or
appropriate transparent instrument for patch observation; pressure film may
alter contact and needs its own control. Cheap spring scales suffice for coarse
static checks, not impact validation. No equipment has been purchased.

## First physical campaign: small and discriminating

Start with one identified cultivar, commercial-ripe class and measured pulp
temperature from one harvest batch. Record mass, principal dimensions, photo IDs,
harvest/storage times, temperature/humidity history and existing defects. Measure
destructive firmness on matched sacrificial fruit, not the test fruit beforehand.

Pilot proposal: 60 independent fruit, ten in each of six groups: untouched,
sham-handled, actual-net catch, liner catch, narrow-strand compression and broad
support compression. Randomize assignment and test order. Use pilot results to
select non-ceiling/non-floor loading levels; keep those fruit out of validation.
Ten per group estimates spread and feasibility; it does not prove a low failure
rate. Expand to different lots, cultivars, maturity classes and temperatures with
blocked randomization and predetermined contrasts rather than a huge unfocused
factorial sweep.

Photograph before, immediately after, and at fixed 24 h / 48 h endpoints under
controlled documented storage. Use separate randomized endpoint groups for
destructive sectioning; the same berry cannot be sectioned twice. Blinded scoring
should include external abrasion/tear/leakage, internal bruise incidence and
volume, residual deformation and subsequent deterioration. Standardized serial
sections with scale allow a volume estimate; report segmentation and slice-spacing
uncertainty. An unhandled control separates ordinary aging from treatment effects.
This timing is a proposed protocol inspired by the cited delayed-damage studies,
not evidence that every damage mode becomes visible at precisely these times.

## Model design: retain only fidelity that changes manipulation decisions

1. **Whole cell:** current rigid fruit + articulated plant + textile dynamics,
   upgraded exposure telemetry. Useful for geometry, clearances and load histories;
   insufficient for stress or bruise claims.
2. **Local mechanical bench:** measured fruit geometry, outer skin and bulk flesh
   with a distinct core only if needed by observations; finite-strain viscoelastic
   response fitted to loading/unloading/relaxation at multiple rates. Add irreversible
   deformation and a separate rupture law only when those effects are measured.
   Fit tool/net compliance separately so a wrong net law cannot masquerade as soft
   fruit. Skin thickness and local material properties remain unmeasured parameters.
3. **Damage predictor:** map mode, contact location/patch, indentation history,
   stress/strain or dissipated tissue energy, duration, repetition and fruit state
   to a distribution of delayed damage outcomes. Fit on physical observations;
   an FE simulation is a hypothesis, not ground truth. A probability model must
   be calibrated on withheld physical fruit and report uncertainty/out-of-domain.
4. **Fast training surrogate:** reduce the validated local model to a contact law
   and history-dependent damage estimator. Test it back in the whole cell: changing
   compliance changes trajectories. A post-hoc score alone cannot correct rigid
   fruit mechanics. Use unknown/abstain outside the measured regime.

Candidate state: per-region recoverable deformation, viscoelastic internal state,
irreversible set and accumulated damage. The bookkeeping lives on each fruit and
survives cutting and all policy handoffs. Do not add independent damage scores
from overlapping contact patches without fitting a spatial/history rule. Maintain
correlations between ripeness, firmness, tissue strength, mass and geometry in
domain randomization; the distribution is a data-derived joint distribution,
not independent sliders.

## Verification and acceptance ladder

- **Measurement verification (implemented tests):** known 20 g static load agrees
  with mg impulse within a declared tolerance; free flight records no contacts;
  observer does not change state; duplicate timestamps fail.
- **Numerical convergence:** compare dt and dt/2 without retuning contact
  parameters. Compare peak force, impulse, contact duration, load location and
  trajectory, not merely warnings. Proposed gate: impulse within 5%, peak within
  10%, contact duration within 5% or two fine steps, fruit-origin path within
  1 mm. These engineering tolerances are not biological safety limits. Mesh/net
  discretization convergence is a separate requirement.
- **Material identification:** loading/hold/unloading curves and patch/recovery
  measurements must constrain separate tissue and receiver parameters. Fit on
  training batches; reserve complete harvest batches/fruit for validation.
- **Damage validation:** freeze preprocessing, parameters and grade definition
  before seeing held-out damage labels. Report calibration, false-safe errors and
  interval coverage by mode/cultivar/batch, not just training R². The acceptable
  market-grade damage rate remains a product decision, not an invented score of 80.
- **Policy validation:** use both arms, neighboring ripe/unripe fruit, occupied
  baskets and genuine topology/position variation. Report accepted fruit per unit
  time, rejected contacts, recovery and damage uncertainty. Speed only competes
  among candidates that pass the fixed physical/quality requirements.

Even zero damaged fruit in 60 independent validation trials gives a one-sided
95% binomial upper bound of about 4.87%, not zero risk. Shared lot effects weaken
the independence assumption. This calculation is an experimental-design warning,
not an acceptance target or an outcome from tests we have run.

## Next concrete decision

Use the newly instrumented catch and placement histories to choose between a
wider textile support, softer/wider strands, a smoother padded rim and a smaller
release gap. These are hypotheses until controlled comparisons and physical fruit
damage observations support them. First establish where the strongest local loads
occur; then build the matching indentation/catch fixture and fit only the model
features needed to discriminate those tool and policy choices.
