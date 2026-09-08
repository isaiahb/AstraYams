"""Corrected downstream-label experiment; preserves v1/v2 source and weights."""
from pathlib import Path
import numpy as np
from astrafactory.contact_downstream_skills import observe, scaffold


def expert_label(env,kind='insert'):
    x=observe(env,kind);y=x[:6].copy()
    if kind=='insert':
        if np.linalg.norm(x[:2])>.04 or np.linalg.norm(x[3:6])>.08:y[2]=0.
        if env.task.force>32:y[2]=.4
    return y


class CorrectedInsertSkill:
    """Fitted linear feedback plus a trained 32x32 tanh residual network."""
    kind='insert'
    def __init__(self,checkpoint):
        self.checkpoint=str(Path(checkpoint))
        with np.load(checkpoint,allow_pickle=False) as d:self.params={k:d[k].copy() for k in d.files}
    def start(self,env):pass
    def correction(self,env):
        x=observe(env,'insert');p=self.params;y=x@p['weight']
        if 'w1' in p:
            z=(x-p['mean'])/p['std'];z=np.tanh(z@p['w1']+p['b1']);z=np.tanh(z@p['w2']+p['b2']);y+=z@p['w3']+p['b3']
        return y
    def act(self,env):return scaffold(env,'insert',self.correction(env))
    def handoff(self,env,info):return bool(info['is_success'])
