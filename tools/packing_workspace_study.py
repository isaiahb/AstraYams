"""Compare net bowl cant angles before committing a new tool CAD.

Only the site orientation changes here: this is a kinematic design study, not
an assertion that the old visual net follows that new datum or has clearance.
"""
from pathlib import Path
import json
import numpy as np
import mujoco as mj
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/packing-workspace-v1'


def solve(m, d, goal, normal, start, margin=.10, trials=5):
    joints = [m.joint('right_' + j) for j in
              ['shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex', 'wrist_roll']]
    ids = np.array([j.qposadr[0] for j in joints])
    lo = np.array([j.range[0] + margin for j in joints])
    hi = np.array([j.range[1] - margin for j in joints])
    sid = m.site('packing_net_center').id
    rng = np.random.default_rng(180)

    def fun(q):
        d.qpos[ids] = q
        mj.mj_kinematics(m, d)
        return np.r_[100 * (d.site_xpos[sid] - goal),
                     10 * (d.site_xmat[sid].reshape(3, 3)[:, 2] - normal),
                     .0001 * (q - start)]

    best = None
    for k in range(trials):
        q = start if not k else rng.uniform(lo, hi)
        result = least_squares(fun, np.clip(q, lo, hi), bounds=(lo, hi), max_nfev=130)
        if best is None or np.linalg.norm(result.fun) < np.linalg.norm(best.fun):
            best = result
        if np.linalg.norm(result.fun[:6]) < .001:
            break
    fun(best.x)
    err = np.linalg.norm(d.site_xpos[sid] - goal)
    angle = np.rad2deg(np.arccos(np.clip(d.site_xmat[sid].reshape(3, 3)[:, 2] @ normal, -1, 1)))
    actual_margin = min(np.r_[best.x - lo, hi - best.x]) + margin
    return dict(position_error_mm=float(err * 1000), normal_error_deg=float(angle),
                joint_margin_deg=float(np.rad2deg(actual_margin)), q=best.x.tolist(),
                feasible=bool(err < .001 and angle < 1))


def main():
    OUT.mkdir(exist_ok=True, parents=True)
    p = ROOT / 'runs/tower-lift-v8/so101'
    m = mj.MjModel.from_xml_path(str(p / 'scene.xml'))
    d = mj.MjData(m)
    poses = np.load(p / 'layout/rollout.npz')['qpos'][::2]
    ids = [m.joint('right_' + j).qposadr[0] for j in
           ['shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex', 'wrist_roll']]
    results = []
    for cant in [-35, -20, 0, 20, 35]:
        q = Rotation.from_euler('y', cant, degrees=True).as_quat()
        m.site_quat[m.site('packing_net_center').id] = q[[3, 0, 1, 2]]
        m.site_sameframe[m.site('packing_net_center').id] = mj.mjtSameFrame.mjSAMEFRAME_NONE
        for i, (label, goal, normal) in enumerate([
            ('catch', [.012, .451, .789], [0, 0, 1]),
            ('container', [-.190, .171, .620], [0, 0, 1]),
            ('tip60', [-.190, .150, .645], [0, np.sin(np.pi/3), .5]),
        ]):
            d.qpos[:] = poses[min(i, 1)]
            record = dict(cant_deg=cant, pose=label, goal_m=goal, normal=normal,
                          **solve(m, d, np.array(goal), np.array(normal), d.qpos[ids].copy()))
            results.append(record)
            print(json.dumps(record), flush=True)
    (OUT / 'study.json').write_text(json.dumps(dict(
        scope='Site-only CAD design study. No changed tool geometry or contact validation.',
        results=results), indent=2) + '\n')


if __name__ == '__main__':
    main()
