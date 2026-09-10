# Recovery evidence and the limits of transfer

Research date: 2026-09-09. The search did not locate an accessible, matching
strawberry fruit-stalk load–hold–unload time series. This is a search result,
not a claim that no such measurements exist. No real curve has been fitted.

| Primary source | What was observed | What it supports here | What it does not identify |
|---|---|---|---|
| [Tsubota et al., 2022](https://www.jstage.jst.go.jp/article/jsamfe/84/4/84_229/_article/-char/en) | Strawberry leaf/petiole loading and damage; new-leaf Young's modulus 89 MPa, increasing with leaf age | Organ and age must accompany stiffness values | Fruit-pedicel modulus, relaxation time or recovery spectrum |
| [Rajendran et al., 2022](https://arxiv.org/html/2207.12552) | Katrina/Zara peduncle compression and cutting, at 1.5 mm/min; irreversible compression failure observed | Keep nondestructive support, crushing and cutting separate; log loading rate and dimensions | Bending recovery or a safe berry-body support pressure |
| [Ruff et al., 1979](https://doi.org/10.13031/2013.35040) | Accessible abstract describes combined tensile/bending stress and fatigue in strawberry stem failure | Failure is a different experiment from reversible recovery | Numerical recovery constants; full paper was not accessed |
| [Ray & Bret-Harte, 2019](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2019.00059/full) | Cantilever tests on woody tree/shrub branches separate rapid, delayed and irreversible response | Distinguish mechanisms and use several observation times | Direct numerical transfer to a strawberry fruit stalk |
| [Strawberry canopy study, 2022](https://www.mdpi.com/2072-4292/14/3/548) | Repeated growth images measured petiole dimensions, orientation and curvature | Growth geometry requires longitudinal observations | Mechanical relaxation constants inferred from a growth image |

The woody-branch study used substantially larger stems than our fruit stalks,
and included long observation periods. A simple standard solid or Burgers law
did not quantitatively fit the measurements; a broad retardation spectrum was
needed. We therefore use one Maxwell branch only to test discriminating
interventions, not as a validated botanical law. Its numerical constants are
not taken from that paper. Delayed recovery seen over a short interval must
not automatically be called permanent deformation.

The canopy paper's publisher page was rate-limited during this search; its
indexed methods describe repeated image measurements. No additional mechanical
claim is based on inaccessible full text. Electrical "relaxation times" in
strawberry peduncle bioimpedance studies were excluded from mechanical parameter
selection because they describe a different response.

## Parameters actually used

| Parameter | Value | Status |
|---|---:|---|
| Equilibrium truss modulus | 45 MPa | Inherited simulation assumption; not a matching measured modulus |
| Added relaxing spring / equilibrium spring | 1 | Illustrative sensitivity choice |
| Stress-relaxation time | 3 s | Illustrative; not a strawberry measurement |
| Local scalar creep/recovery time | 6 s | Derived from this standard-solid network; not a fitted observation |
| Pre-existing rest-curvature fraction | 0.5 | Alternative history hypothesis, paired with doubled stiffness |
| Holds | 1 s and 12 s | Experimental design choices |
| Recovery observation | 15 s after withdrawal | Finite window; cannot establish permanent set |

The third hypothesis changes fixed rest curvature and stiffness **before** the
test, preserving the initial loaded moments. It does not cause growth or
permanent plastic deformation during these few seconds. The relaxing model's
internal state evolves continuously from its constitutive law, even in the
control. No material update depends on a desired fruit position or a timer
triggering a particular recovery shape.

Search terms included combinations of strawberry, pedicel, peduncle, stem,
petiole, bending, creep, stress relaxation, unloading and recovery. Results
about fruit flesh, packaging, bioimpedance, other species, failure and leaf
stalks were separated rather than pooled into a fictitious parameter fit.

## Next real measurements

Record intact truss geometry and fruit masses with a scale and two calibrated
views. Log tool position and force during a small support ramp, fixed-position
holds of several durations, complete withdrawal and a long recovery recording.
Track the calyx, primary stalk tip, common branch and neighboring fruit. Record
cultivar, age/maturity, stalk diameter, hydration, temperature and any damage.
Keep the fruit attached for this test.

Use repeated low-amplitude cycles to assess reproducibility and drift. Reserve
different hold durations, load amplitudes and plants for validation. Observe
for minutes after the fast response; extend the window if motion persists.
Separately measure unloaded geometry or perform controlled removal to constrain
pre-existing rest curvature. A force–deflection curve alone can leave stiffness
and rest-shape tradeoffs unresolved.

## Fruit-contact leads for the next milestone

[An et al., 2020](https://doi.org/10.1016/j.jfoodeng.2020.110016) reports
strawberry loading–unloading tests with rate- and direction-dependent transitions
between recoverable response, local plasticity and failure. The accessible
publisher abstract supports separating these regimes. The repository PDF could
not be fetched in this session; no curve has been extracted or fitted. Tissue
failure moduli must not be relabeled as a safe whole-berry contact stiffness.

[An et al., published online 2024](https://link.springer.com/article/10.1007/s11947-024-03491-0)
provides accessible methods for Malwina fruit cortex specimens: 8 mm diameter
and height, compressed 5 mm at 1 mm/s. Cell-size distributions informed a
bonded-particle model evaluated against tissue compression. These are excised
tissue tests spanning substantial compression, not a calibrated intact-berry
cup-contact law. This is a useful precedent for connecting observed internal
structure to an isolated mechanical test. It does not require modeling every
cell in the whole plant or establish our specimen's parameters.

Proposed next outcome: resolve indentation/contact area for one berry and one
tool, with an isolated force–displacement and unloading comparison before
coupling it into this truss. Treat reversible contact, delayed recovery and
damage as separate identification problems; retain rigid-fruit results as a
baseline. No deformable-fruit implementation is claimed by this study.
