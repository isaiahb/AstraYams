"""Observe fruit contact exposure at physics rate; never infer a bruise threshold.

Rigid MuJoCo contacts have no measured tissue contact area. Contact distance is
solver overlap, not tissue strain. Calyx exposure remains separate from flesh.
"""
from collections import defaultdict
import math

import mujoco
import numpy as np


class FruitContactAudit:
    def __init__(self, model, force_floor_N=1e-6):
        self.model = model
        self.floor = float(force_floor_N)
        if not math.isfinite(self.floor) or self.floor < 0:
            raise ValueError('Contact detection floor must be finite and nonnegative')
        fruit_bodies = {int(model.geom_bodyid[g]) for g in range(model.ngeom)
                        if model.geom(g).name.startswith('berry_')}
        self.bodies = sorted(fruit_bodies)
        self.body_names = [model.body(b).name for b in self.bodies]
        self.regions = {}
        for g in range(model.ngeom):
            body = int(model.geom_bodyid[g])
            if body in fruit_bodies:
                name = model.geom(g).name
                region = 'flesh' if name.startswith('berry_') else 'calyx' if 'calyx' in name else 'other'
                self.regions[g] = (body, region)
        self.reset()

    def reset(self):
        self.pairs = {}
        self.samples = []
        self.previous_active = set()
        self.previous_time = None

    def sample(self, data, time_s, dt):
        if not math.isfinite(dt) or dt <= 0 or not math.isfinite(time_s):
            raise ValueError('Finite positive dt and finite time required')
        if self.previous_time is not None and time_s <= self.previous_time:
            raise ValueError('Sample exactly once per advancing physics step')
        self.previous_time = time_s
        contacts = defaultdict(list)
        # Negative geom IDs belong to flex contacts; do not index geom arrays with them.
        relevant = np.any(np.isin(data.contact.geom, list(self.regions)), axis=1)
        for i in np.flatnonzero(relevant):
            c = data.contact[i]
            force = np.zeros(6)
            mujoco.mj_contactForce(self.model, data, int(i), force)
            if not np.isfinite(force).all():
                raise ValueError('Non-finite contact force; exposure cannot be validated')
            normal = max(0., float(force[0]))
            if normal <= self.floor:
                continue
            tangential = float(np.linalg.norm(force[1:3]))
            for side, geom in enumerate(c.geom):
                if int(geom) not in self.regions:
                    continue
                body, region = self.regions[int(geom)]
                other = 1 - side
                if c.geom[other] >= 0:
                    counterpart = self.model.geom(int(c.geom[other])).name
                elif c.flex[other] >= 0:
                    counterpart = 'flex:' + (mujoco.mj_id2name(
                        self.model, mujoco.mjtObj.mjOBJ_FLEX, int(c.flex[other])) or str(c.flex[other]))
                else:
                    counterpart = 'unclassified'
                local = data.xmat[body].reshape(3, 3).T @ (c.pos - data.xpos[body])
                contacts[(body, region, counterpart)].append(
                    (normal, tangential, max(0., -float(c.dist)), c.pos.copy(), local))
        totals = np.zeros((len(self.bodies), 4))
        active = set(contacts)
        for key, values in contacts.items():
            body, region, counterpart = key
            normal = sum(x[0] for x in values)
            tangent = sum(x[1] for x in values)
            peak_point = max(values, key=lambda x: x[0])
            record = self.pairs.setdefault(key, dict(
                fruit=self.model.body(body).name, surface=region, counterpart=counterpart,
                contact_duration_s=0., normal_impulse_Ns=0., tangential_impulse_Ns=0.,
                peak_sum_normal_N=0., peak_point_normal_N=0., max_solver_overlap_m=0.,
                contact_onsets=0, first_contact_s=time_s, last_contact_s=time_s,
            ))
            record['contact_duration_s'] += dt
            record['normal_impulse_Ns'] += normal * dt
            record['tangential_impulse_Ns'] += tangent * dt
            record['contact_onsets'] += int(key not in self.previous_active)
            record['last_contact_s'] = time_s
            record['max_solver_overlap_m'] = max(record['max_solver_overlap_m'], max(x[2] for x in values))
            record['peak_sum_normal_N'] = max(record['peak_sum_normal_N'], normal)
            if peak_point[0] > record['peak_point_normal_N']:
                record.update(peak_point_normal_N=peak_point[0], peak_time_s=time_s,
                              peak_world_position_m=peak_point[3].tolist(),
                              peak_body_position_m=peak_point[4].tolist())
            k = self.bodies.index(body)
            totals[k, 0 if region == 'flesh' else 1] += normal
            totals[k, 2] += tangent
            totals[k, 3] = max(totals[k, 3], peak_point[0])
        self.previous_active = active
        self.samples.append((time_s, *totals.ravel()))

    def report(self):
        return dict(
            status='contact exposure measured in simulation; biological damage UNKNOWN',
            damage_probability=None, bruise_volume_mm3=None, contact_pressure_Pa=None,
            absorbed_tissue_energy_J=None,
            force_detection_floor_N=self.floor,
            pairs=sorted(self.pairs.values(), key=lambda x: x['peak_point_normal_N'], reverse=True),
            fruit_bodies=self.body_names,
            sample_columns=['time_s'] + [f'{b}/{k}' for b in self.body_names for k in
                            ['flesh_sum_normal_N', 'calyx_or_other_sum_normal_N',
                             'sum_tangential_N', 'peak_point_normal_N']],
            sample_count=len(self.samples),
            interpretation=[
                'Normal and tangential impulses integrate every physics step, including sustained loading and repeated contact.',
                'Scalar normal forces do not cancel when opposite sides squeeze a berry.',
                'Fruit-to-fruit exposure is attributed to each fruit; do not sum it as system energy.',
                'Contact onsets include numerical chatter; they are not validated separate impacts.',
                'No contact area, tissue strain, absorbed tissue energy or bruising law has been calibrated.',
                'Negative contact distance is solver overlap, not tissue indentation.',
            ],
        )
