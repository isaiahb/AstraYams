"""Observation-only visual action-chunk policy.

Runtime consumes only fixed-camera RGB and deployable joint/controller feedback.
No simulator, object pose, contacts, teacher, IK or task-phase dependencies.
"""
from collections import deque
from pathlib import Path
import numpy as np
import torch
from torch import nn


def resolve_device(device):
    if device=='auto':
        return 'cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu'
    if device not in ('cpu','mps','cuda'):raise ValueError('Expected cpu, mps, cuda, or auto')
    return device


class VisualNetwork(nn.Module):
    def __init__(self,chunk_size=8):
        super().__init__();self.chunk_size=chunk_size
        self.encoder=nn.Sequential(nn.Conv2d(3,16,5,stride=2,padding=2),nn.ReLU(),
            nn.Conv2d(16,32,3,stride=2,padding=1),nn.ReLU(),nn.Conv2d(32,48,3,stride=2,padding=1),nn.ReLU(),
            nn.AdaptiveAvgPool2d((4,4)),nn.Flatten(),nn.Linear(48*16,64),nn.ReLU())
        self.proprio_encoder=nn.Sequential(nn.Linear(28,64),nn.ReLU())
        self.memory=nn.GRU(192,128,batch_first=True)
        self.head=nn.Linear(128,chunk_size*7)
        self.register_buffer('action_scales',torch.tensor([.4]*6+[.5]))
    def forward(self,rgb,proprio):
        # rgb [batch,history,2,3,height,width], float [0,1].
        b,t,c,channels,h,w=rgb.shape
        if c!=2 or channels!=3 or proprio.shape!=(b,t,28):raise ValueError('Sensor contract mismatch')
        features=self.encoder(rgb.reshape(b*t*c,channels,h,w)).reshape(b,t,c*64)
        prop=self.proprio_encoder(proprio);memory,_=self.memory(torch.cat([features,prop],dim=-1))
        return torch.tanh(self.head(memory[:,-1]).reshape(b,self.chunk_size,7))*self.action_scales


class VisualPolicy:
    """Pure reset()/act(observation) interface; caller executes returned actions."""
    def __init__(self,checkpoint,device='cpu'):
        self.device=resolve_device(device)
        saved=torch.load(Path(checkpoint),map_location='cpu',weights_only=False)
        self.config=saved['config'];self.model=VisualNetwork(self.config['chunk_size'])
        self.model.load_state_dict(saved['model']);self.model.to(self.device).eval()
        self.mean=np.asarray(saved['proprio_mean'],dtype=np.float32);self.std=np.asarray(saved['proprio_std'],dtype=np.float32)
        self.reset()
    def reset(self):
        self.rgb_history=deque(maxlen=self.config['history_steps']);self.proprio_history=deque(maxlen=self.config['history_steps']);self.pending=deque()
    def act(self,observation):
        if isinstance(observation,dict):rgb,proprio=observation['rgb'],observation['proprio']
        else:rgb,proprio=observation.rgb,observation.proprio
        rgb=np.asarray(rgb);proprio=np.asarray(proprio,dtype=np.float32)
        if rgb.shape!=(2,160,160,3) or rgb.dtype!=np.uint8 or proprio.shape!=(28,) or not np.isfinite(proprio).all():raise ValueError('Expected RGBuint8[2,160,160,3] and finiteproprio28')
        if not self.rgb_history:
            for _ in range(self.config['history_steps']):self.rgb_history.append(rgb.copy());self.proprio_history.append(proprio.copy())
        else:self.rgb_history.append(rgb.copy());self.proprio_history.append(proprio.copy())
        if not self.pending:
            images=np.stack(self.rgb_history).transpose(0,1,4,2,3)[None]
            states=(np.stack(self.proprio_history)-self.mean)/self.std
            with torch.inference_mode():
                actions=self.model(torch.from_numpy(images).to(self.device,dtype=torch.float32)/255.,torch.from_numpy(states[None]).to(self.device)).cpu().numpy()[0]
            self.pending.extend(actions[:self.config['execute_steps']].copy())
        return np.asarray(self.pending.popleft(),dtype=np.float32).copy()
