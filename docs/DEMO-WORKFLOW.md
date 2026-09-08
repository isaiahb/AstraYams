# Prepared workflow demo

The three prompt choices are backed by `assets/workcells/demo-workflows/catalog.json`:
keyed insertion, powered-vise loading, and bimanual manual-vise design.
Each contains a concept image, inspectable CAD scene, configuration stage and
the relevant learning evidence or explicit outstanding work.

Use the first two existing examples to explain learning while a new configuration
is prepared. Keyed insertion has a 14.3-second orbitable audited replay and prior
20/20 nominal plus 20/20 stress trials. Powered-vise loading has paired recorded
PPO seating results, 2/5 to 4/5 on the same five held-out seeds. Manual tightening
has CAD and static reachability samples, not a trained manipulation policy.

The configure command copies a selected prepared template and its hashed mesh
assets, compiles it in MuJoCo, checks source/bundle model parameters, and tests
one reset/step for the two existing Gym tasks. It writes actual progress events.
It does not simulate a minute of work with timers, claim fresh CAD generation,
or relabel past training as a new training run. Local template preparation can
finish in well under a minute. Custom design/training is separate work.

```sh
PYTHONPATH=src:tools python tools/configure_demo_environment.py \
  --scenario machine-tending --output runs/demo-configurations/my-new-environment
```

Concept images are prepared visual references, not exact mechanical drawings.
The existing CAD and experiments preceded some of these illustrations. Do not
present that historical work as image-to-CAD generation performed live.

CAD playback uses recorded body transforms and actual YAM mesh geometry.
Playback speed changes presentation time only. An exploded view is inspection
geometry and must pause playback until the assembly is restored.

The manual tray has been moved to x=.18 to clear the raised pedestal. The
powered cosmetic base was narrowed without altering the frozen physics model.
See `assets/workcells/manual_vise_cad/layout-review.json` for geometric checks.
