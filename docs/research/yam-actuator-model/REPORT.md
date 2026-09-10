# A calibratable actuator model for YAM manipulation

A useful YAM simulation can include motor electrical dynamics, controller response, gearbox play, heating, and communication timing before a physical arm is available. Hardware measurements can subsequently identify the uncertain parameters and test whether the model predicts new behavior. This is a standard system-identification problem: combine a physical model with experiments that constrain it.[^1] The present research establishes a component map, a model architecture, and a calibration protocol. It does not establish hardware accuracy or replace the current training environment.

The engineering objective is to predict manipulation outcomes: how quickly contact force rises, whether a joint can hold its load, how reversal affects tool position, and whether sensing or command delays cause overshoot. Simulating every transistor is unnecessary for that objective. Modeling the resulting bandwidth, saturation, losses, and delays is necessary when those effects materially change the task.

## Component evidence and revision control

The target is the YAM v1 geometry already imported into AstraFactory, with the linear DM4310 gripper. The upstream snapshot is `i2rt-robotics/i2rt@5b72c47239bd056d0fa6c1a39edeb0537c89443c`. Its arm configuration assigns DM4340 motors to joints 1–3 and DM4310 motors to joints 4–6. Its motor definitions associate these families with 40:1 and 10:1 gear ratios respectively. These are source-backed family identifications; the exact installed motor suffix, winding, hardware revision, firmware, and supply remain unverified.[^2][^3]

Damiao publishes separate model repositories and manuals. The manufacturer-hosted DM-J4310-2EC V1.1 manual V1.2 and DM-J4340-2EC manual V1.1 used here are dated September 8, 2026. Both are pinned by repository commit in `parameters.json`. Their specification pages were inspected visually, including the distinction between 24 V and 48 V columns.[^4][^5]

| Published specification | DM-J4310-2EC V1.1, 24 V | DM-J4340-2EC, 24 V |
|---|---:|---:|
| Reduction | 10:1 | 40:1 |
| Phase resistance | 0.65 Ω | 0.88 Ω |
| Phase inductance | 340 μH | 360 μH |
| Rated / peak phase current | 2.5 / 7.5 A | 3 / 8 A |
| Rated / peak output torque | 3 / 7 N·m | 9 / 27 N·m |
| Rated / no-load speed | 120 / 200 rpm | 36 / 52.5 rpm |

These are **candidate datasheet values**, not measurements of the future arm. Peak ratings do not specify a permissible duty cycle. The table's phase quantities must not be copied into a DC-equivalent model without resolving the current and voltage conventions.

The older DM4340 manual reproduced by Enactic instead lists 0.76 Ω, 317 μH, and 2.5 A rated current for its 24 V version. Preserve this discrepancy; do not average the two manuals into a fictional motor. Select the matching variant after checking its identity and register dump.[^6] The newer DM4310 manual also has a performance-chart caption stating 36 rpm while the plotted speed is approximately 120 rpm. That chart is not a sufficient basis for a fitted torque-speed curve without resolving the discrepancy.[^4]

The pinned SDK uses MIT command encoding ranges of ±28 N·m for DM4340 and ±10 N·m for DM4310. These are not the 27 and 7 N·m manufacturer peak ratings. The ranges determine how numbers are packed into messages, and can be changed in the motor. The SDK's generic `KT=1` and current bounds are placeholders, not electrical specifications.[^3]

The gripper configuration specifies 6.57 rad motor travel and 0.096 m gripper travel, with a linear force conversion. It also requires endpoint calibration. The existing URDF has approximately 0.0939 m combined finger travel. The motor, aperture, and individual-finger coordinates need a single documented conversion before mapping torque to contact force; the crank-gripper model must not be substituted.[^7]

## Model architecture

The proposed signal path is:

```text
policy action
  → sampled, timestamped command buffer
  → CAN encoding / transport / command hold
  → motor position–velocity–torque controller
  → current response and voltage/current limits
  → motor rotor and gearbox
  → link dynamics and object contacts
  → encoder / effort / temperature measurements
  → sampling, filtering and observation delay
  → policy observation
```

This diagram is an engineering design proposal. Every state and conversion needs an explicit coordinate system. Motor radians differ from output-shaft radians; one finger's displacement differs from total aperture. Power conservation is a useful check on these transformations. Controller gains must be converted along with positions, velocities, and torques.

### Electrical behavior and control

A first physical model can use the DC-equivalent equations `L di/dt = v − R(T)i − Ke ωm` and `τm = Kt i`. They express current rise, resistive loss, back-EMF, and torque production. They are an averaged representation of a commutated motor, not a transistor-level inverter simulation. MuJoCo provides this type of model, including optional inductance and heating.[^8]

For the actual Damiao controller, use the documented MIT interface: desired position, velocity, proportional gain, derivative gain, and feedforward torque. The internal controller computes a torque demand and regulates torque-producing current. A PPO that sends position targets can therefore still operate a physically constrained motor; the target must pass through the controller and plant.[^9]

The model should initially expose a bounded current-loop response, voltage saturation, and torque/current limits. Add the firmware's actual clipping order and feedforward behavior once identified. Supply voltage limits available back-EMF headroom; a high-speed motor cannot produce arbitrary torque simply because an output clamp permits it. A shared supply can also couple joints through voltage sag, current limits, and regeneration. The supply model needs its own measurements; bus current is not motor phase current.

For a brushless implementation, explicitly document whether current is phase RMS, phase peak, or q-axis current, and whether resistance is phase or line-to-line. Torque constants may refer to the rotor or geared output. The manufacturer's torque-constant relation includes pole pairs, flux, gear ratio, and transmission coefficient. Dividing output rated torque by rated current is not enough to recover a unique rotor constant and gearbox efficiency.[^4][^5]

### Gearbox, friction, and compliance

Use separate motor-side and output-side coordinates where backlash is consequential. Define a relative displacement `δ = θm/N − q`. A gap model allows small relative motion before the tooth flanks engage; compliant engagement then produces load-dependent deflection and dissipation. Reverse loading and backdriving must work, including after loss of power. Treat friction, lost motion, and elastic deflection as different mechanisms.

MuJoCo documents a two-coaxial-hinge backlash construction with finite rotor inertia. It is a useful initial representation, but it does not identify YAM's backlash width or reproduce every gearbox hysteresis effect.[^10] The detailed version should check that the transmission does not create energy during reversals. A simple output deadband may be adequate for an early sensitivity experiment, but it cannot establish realistic gear engagement forces.

Use static/Coulomb and viscous friction first, then introduce a richer friction law only if measured reversals demand it. Do not double-count gearbox loss as both a fixed efficiency multiplier and fitted friction. Similarly, a rotor inertia `Jm` reflected to a rigid output coordinate becomes `N²Jm`; including both explicit rotor dynamics and the same reflected inertia would count it twice.

### Heating and sustained operation

Use winding and housing thermal states when the data supports both: winding heat capacity receives copper loss, heat passes to the housing, and the housing dissipates it to the mount and air. Begin with one thermal state if only one effective time constant is observable. A driver temperature channel is not automatically a winding-temperature measurement.

In a consistent scalar equivalent, copper loss is `i²R(T)`; in a three-phase model the phase losses must be summed. Resistance rises with winding temperature. At fixed voltage, that changes current; under current regulation, the controller initially increases voltage to maintain torque, until voltage or protection limits intervene. A model that automatically reduces torque whenever temperature rises would miss this distinction. Speed-dependent losses and cooling conditions can change the continuous operating envelope.[^11]

Thermal state should persist across repeated trials that represent one uninterrupted work session. Resetting every episode to a cold motor lets a policy repeatedly exploit peak capability. Datasheet temperature protection and rated torque are separate from a measured safe duration at a given load. Estimate thermal parameters and protection behavior without using destructive overheating tests.

### Communication and sensors

The SDK declares 250 Hz as a default frequency for a bandwidth check; the examined communication loop sends commands sequentially and yields the thread. A 7 ms constant is a slow-loop reporting threshold. Neither number proves actual fixed latency. The wrapper assigns a common host-read timestamp to cached motor states, which also does not prove simultaneous measurement.[^12]

Model command and observation delays separately, with sample-and-hold behavior. Record per-joint age of information, scheduling jitter, packet loss, and configured watchdog behavior. A lost message should cause the documented held-command or fault behavior, not an arbitrary teleport or immediate ideal update. Encoding uses finite resolution; encoder accuracy is a separate quantity from the number of bits in a message.

The normal feedback parser exposes position, velocity, torque-like effort, motor temperature, and driver temperature. It does not expose raw phase-current or bus-voltage samples in that frame. A class field with a default voltage value does not establish a working voltage sensor.[^12] A richer logger or external instrument will be needed for some calibration experiments.

## What the installed engine can already do

The local runtime is MuJoCo 3.12.0. Its native `dcmotor` actuator accepts voltage input and can include inductance, temperature-dependent resistance, and friction. Version 3.12 changed its controller to torque-space gains and position/velocity/feedforward input signatures. Older examples using voltage-space controller gains must not be copied unchanged.[^8][^13]

`tools/probe_yam_motor_model.py` performs isolated operating-point checks with **illustrative, non-YAM parameters**. It checks back-EMF, current derivatives, heating/cooling derivatives, and compilation of the three-input controller and backlash construction. The checked results are saved in `capability-check.json`. These establish engine capability, not integrated arm behavior or a calibrated current controller. The detailed motor layer is not yet connected to the PPO or strawberry demonstrations.

An efficient training model can retain the effects that matter at policy time scales while using the detailed model as a reference. Fast electrical transients can use an exact or stable reduced update; thermal dynamics can run more slowly. Contact dynamics still need a sufficiently small integration step. Accept a cheaper model only after its force transients, reversal behavior, and task outcomes agree with the detailed one over the evaluated operating envelope. No training-speed improvement is asserted before benchmarking.

## Calibration once an arm is available

The first operation should be a read-only identity and configuration capture: arm revision, motor labels, firmware, gearbox ratio, phase resistance/inductance estimates, flux, torque scale, active control mode, limits, encoder offsets, and timeout. Registers documented for related dual-encoder versions include motor-side and output-shaft position, which could help quantify transmission lost motion if the installed firmware exposes them.[^14] A register is a valuable prior or firmware setting, not automatically an independently accurate physical measurement.

Use synchronized raw command and measurement logs. Keep host-send, bus-send, receive, and sensor timestamps distinct wherever available. Store raw frames as well as decoded values so scaling errors can be corrected later. Each experiment should record initial temperature, supply condition, mounting, tool, payload, and firmware. Avoid using derived feedback torque as the sole independent reference for calibrating the torque scale that produced it.

| Experiment | Main quantities identified | Evidence and discriminating conditions |
|---|---|---|
| Small free-space steps and multisines | delay, bandwidth, damping, inertial combinations | Multiple directions, amplitudes, speeds and loads; synchronize command and observation clocks |
| Known-load holds and gentle torque ramps | effective output torque scale, friction, bias | Independent load cell or known lever/load; separate direction and pose effects |
| Slow reversals with small alternating loads | backlash, stiction, torsional compliance | Compare motor and output encoders when available; otherwise use independent output tracking |
| Controlled electrical characterization | resistance, inductance, current response | Confirm phase and current conventions; use appropriately instrumented manufacturer-supported access |
| Moderate repeated work followed by cooldown | effective thermal resistances/capacities | Several starting temperatures and loads; log ambient, mount and driver/winding channels |
| Multi-joint bus and supply load tests | jitter, observation age, voltage coupling | Compare idle, simultaneous motion and CPU/bus load; measure supply independently |
| Gripper aperture and contact-force sweeps | transmission mapping, friction, stiffness | Several apertures and directions with a force gauge; distinguish per-finger force from combined force |

Fit bounded parameters to trajectories, then evaluate on trials excluded from fitting. Keep an additional task-level holdout: loaded direction reversal, constrained grasp, and motion through compliant foliage. Model selection must consider force errors, onset timing, settling, slip, and failure outcomes alongside joint-angle error. Calibrating against one smooth trajectory can hide a model that fails precisely when contact begins.

Some parameters cannot be separated with the available signals. For example, motor torque scale and gearbox efficiency may appear only as a product; friction and an unknown load can have similar effects. Report identifiable combinations or uncertainty ranges instead of forcing every physical label to have a precise number. Experiment design should add measurements or excitation that distinguish competing explanations.[^1]

The AI can select experiments from this protocol, fit candidate models, inspect residuals, and propose the next discriminating test. It can also generate a synthetic trace with known parameters and check that the fitting pipeline recovers them. That verifies software plumbing only. Synthetic-to-synthetic agreement is not evidence of real-robot fidelity.

## Training under uncertainty

Before measurements, use an explicitly provisional ensemble of physically consistent models. Keep revision alternatives separate. Sample stable properties per robot or episode, allow temperature and supply state to evolve over time, and model fast disturbances as time-varying processes. Preserve correlations: resistance and temperature are coupled; independent arbitrary draws of resistance, current limit, and torque constant can describe an impossible actuator.

The policy may need recent observation/action history to infer delay or loading. Training can expose privileged simulator quantities to a teacher or critic, but the deployed actor must use signals the hardware can supply. Domain randomization should cover uncertainty left after calibration rather than substitute for calibration. Prior work has combined identification before policy learning with task-specific adaptation afterward; that provides a methodological precedent, not evidence that YAM transfer is already solved.[^15]

For strawberry dexterity, prioritize controller saturation and delay, gripper transmission/friction, small reversals, and compliant contact before motor switching ripple. Retain thermal limits for repeated harvesting. Improving the arm model does not resolve unknown berry damage limits, stem failure mechanics, or visual sensing errors; those remain separately identifiable parts of the complete task model.

## Next implementation milestone and acceptance evidence

Implement one wrist-joint bench and the linear gripper with the real command interface, finite current/voltage response, explicit transmission coordinates, and delayed observations. Preserve the current idealized model as a baseline. Use the parameter ledger to prevent unverified datasheet values from silently becoming hardware facts.

The bench should demonstrate unloaded response, load-limited holding, reversal lost motion, and delayed contact recovery under an identical command sequence. Its evidence must include actual position, requested position, effort, current estimate, voltage, temperature state, and timestamped command age. Halving the timestep must preserve the important conclusions. A separate repeated-duty test should show thermal evolution.

Do not enable this layer across all policy training until coordinate conversions, passivity, saturation, and reset/continuation semantics pass the bench checks. Hardware validation remains pending. This staged implementation produces a model that can be improved through measurements while keeping each added mechanism accountable to task-relevant evidence.

## Sources

[^1]: Russ Tedrake, [System Identification, Underactuated Robotics](https://underactuated.mit.edu/sysid.html), especially parameter identification, experiment design, and identifiability. Accessed September 9, 2026.
[^2]: I2RT, [YAM v1 motor configuration](https://github.com/i2rt-robotics/i2rt/blob/5b72c47239bd056d0fa6c1a39edeb0537c89443c/i2rt/robots/config/yam_v1.yml), pinned to the imported asset snapshot.
[^3]: I2RT, [motor constants and gearbox-ratio definitions](https://github.com/i2rt-robotics/i2rt/blob/5b72c47239bd056d0fa6c1a39edeb0537c89443c/i2rt/motor_drivers/utils.py).
[^4]: Shenzhen Damiao Technology, [DM-J4310-2EC V1.1 Geared Motor User Manual V1.2](https://github.com/dmBots/DM-J4310-2EC/blob/9ccbaf6fa43c1ffee4ca5fcc08b615c826e4fefb/manual/DM-J4310-2EC%20V1.1%20Geared%20Motor%20User%20Manual%20V1.2%202026-09-08.pdf), September 8, 2026, pp. 7–9 and 31. Manufacturer-hosted original; no manual redistributed in this repository.
[^5]: Shenzhen Damiao Technology, [DM-J4340-2EC Geared Motor User Manual V1.1](https://github.com/dmBots/DM-J4340-2EC/blob/986209a45dca29375faf190106eb00a36baa44e9/manual/DM-J4340-2EC%20%20Geared%20Motor%20User%20Manual%20V1.1%202026-09-08.pdf), September 8, 2026, pp. 7–9.
[^6]: Enactic, [English rendering of Damiao DM-J4340-2EC manual V1.0](https://damiao.enactic.ai/en/products/hardware/dm-j4340-2ec-v1.0/), original dated March 14, 2024. Used to expose revision differences, not silently override the newer manufacturer manual.
[^7]: I2RT, [linear gripper configuration](https://github.com/i2rt-robotics/i2rt/blob/5b72c47239bd056d0fa6c1a39edeb0537c89443c/i2rt/robots/config/linear_4310.yml) and [force mapping implementation](https://github.com/i2rt-robotics/i2rt/blob/5b72c47239bd056d0fa6c1a39edeb0537c89443c/i2rt/robots/utils.py).
[^8]: Google DeepMind, [MuJoCo 3.12 XML actuator reference](https://mujoco.readthedocs.io/en/3.12.0/XMLreference.html#actuator-dcmotor), electrical, thermal, controller and activation-state definitions.
[^9]: Shenzhen Damiao Technology, [DM4310 V1.1 original manual V1.0](https://damiao.enactic.ai/en/assets/files/dm-j4310-2ec-v1.1-zh-5d089e0b013d8e2fc203c5b670008a66.pdf), November 16, 2023, p. 5, MIT control architecture; manufacturer document hosted by Enactic.
[^10]: Google DeepMind, [MuJoCo backlash modeling](https://mujoco.readthedocs.io/en/3.12.0/modeling.html#backlash).
[^11]: Maxon, [Continuous operation range of BLDC motors](https://support.maxongroup.com/hc/en-us/articles/360000350014-Continuous-operation-range-of-BLDC-EC-Motors), August 29, 2024. General loss/thermal principles; not a source of Damiao parameter values.
[^12]: I2RT, [CAN motor driver](https://github.com/i2rt-robotics/i2rt/blob/5b72c47239bd056d0fa6c1a39edeb0537c89443c/i2rt/motor_drivers/dm_driver.py), [CAN interface](https://github.com/i2rt-robotics/i2rt/blob/5b72c47239bd056d0fa6c1a39edeb0537c89443c/i2rt/motor_drivers/can_interface.py), and [robot wrapper](https://github.com/i2rt-robotics/i2rt/blob/5b72c47239bd056d0fa6c1a39edeb0537c89443c/i2rt/robots/motor_chain_robot.py).
[^13]: Google DeepMind, [MuJoCo 3.12 changelog](https://mujoco.readthedocs.io/en/3.12.0/changelog.html), DC motor input-signature and controller changes.
[^14]: Enactic, [Damiao DM-J4340P-2EC register appendix](https://damiao.enactic.ai/en/products/hardware/dm-j4340p-2ec-v1.0/#appendix-register-list-and-range). Related variant; availability and timing must be confirmed on the installed motors.
[^15]: Wenhao Yu, Visak C. V. Kumar, Greg Turk, C. Karen Liu, [Sim-to-Real Transfer for Biped Locomotion](https://arxiv.org/abs/1903.01390), IROS 2019.
