class Reward:
    def __init__(self,env):self.env=env
    def reset(self):pass
    def __call__(self,action,info):return float(info["is_success"])*10.
