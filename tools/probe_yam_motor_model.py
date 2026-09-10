"""Isolated engine capability checks, not a calibrated YAM or a robot rollout.

All constants below are illustrative. Operating-point qvel/activation assignments
are boundary conditions for constitutive-law checks, never policy execution.
Run with MuJoCo 3.12.0. No hardware commands, model upgrades or app edits.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import mujoco
import numpy as np


def make(extra: str = "", backlash: bool = False):
    gap = ('<joint name="gap" axis="0 0 1" limited="true" '
           'range="-0.005 0.005"/>') if backlash else ""
    xml = f'''<mujoco><compiler angle="radian"/>
      <option gravity="0 0 0" timestep="0.00005"/>
      <worldbody><body><joint name="j" axis="0 0 1" armature="0.01"/>
      {gap}<geom type="sphere" size="0.05" mass="1"/></body></worldbody>
      <actuator><dcmotor joint="j" resistance="1" motorconst="0.1 0.1"
      {extra}/></actuator></mujoco>'''
    m = mujoco.MjModel.from_xml_string(xml)
    return m, mujoco.MjData(m)


def run():
    if mujoco.__version__ != "3.12.0":
        raise RuntimeError("Re-audit DC motor semantics before changing MuJoCo version")
    checks = []

    def check(name, observed, expected, tolerance=1e-10, scope="constitutive law"):
        passed = bool(np.allclose(observed, expected, atol=tolerance, rtol=0))
        checks.append(dict(name=name, observed=float(observed), expected=float(expected),
                           absolute_tolerance=tolerance, passed=passed, scope=scope))

    m, d = make()
    d.ctrl[0] = 2
    mujoco.mj_forward(m, d)
    check("zero-speed voltage to torque: K*V/R", d.actuator_force[0], .2)
    d.qvel[0] = 10  # Prescribed operating point for back-EMF, not arm motion.
    mujoco.mj_forward(m, d)
    check("back-EMF: K*(V-K*speed)/R", d.actuator_force[0], .1)

    m, d = make('inductance="0.002 0"')
    d.ctrl[0] = 2
    mujoco.mj_forward(m, d)
    check("initial current rise: (V-R*i)/L", d.act_dot[0], 1000)
    d.act[0] = 2
    mujoco.mj_forward(m, d)
    check("steady current derivative at V/R", d.act_dot[0], 0)

    m, d = make('thermal="5 20 0 0.0039 25 25"')
    d.ctrl[0] = 2
    mujoco.mj_forward(m, d)
    check("cold heating derivative: V^2/(R*C)", d.act_dot[0], .2)
    d.act[0] = 50  # Winding temperature rise above ambient in this model.
    mujoco.mj_forward(m, d)
    hot_r = 1 + .0039 * 50
    check("hot voltage-driven torque", d.actuator_force[0], .2 / hot_r)
    check("hot heating minus cooling", d.act_dot[0], (4 / hot_r - 50 / 5) / 20)

    m, d = make('input="pos vel ff" controller="10 0 1 0 0 12"')
    d.ctrl[:] = [0, 0, .1]
    mujoco.mj_forward(m, d)
    check("three-input torque controller feedforward", d.actuator_force[0], .1)
    m, d = make(backlash=True)
    mujoco.mj_forward(m, d)
    check("two coaxial backlash coordinates", m.nv, 2, scope="compilation only")
    report = dict(
        mujoco_version=mujoco.__version__,
        status="capability_checks_only",
        hardware_calibrated=False,
        integrated_into_yam_environment=False,
        constants="Illustrative: R=1 ohm, K=0.1 Nm/A, L=2mH; not Damiao values",
        limitation="No trajectory, delay, backlash hysteresis or real-hardware validation",
        checks=checks,
        passed=all(c["passed"] for c in checks),
    )
    if not report["passed"]:
        raise AssertionError(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
