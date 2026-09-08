import importlib.util
from pathlib import Path
import tempfile
import types
import unittest
import numpy as np

spec=importlib.util.spec_from_file_location('visual_leak_audit',Path(__file__).parents[1]/'tools/check_visual_leaks.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

class BoundaryTests(unittest.TestCase):
    def test_clean_fixed_observations_are_invariant(self):
        module=types.ModuleType('clean_fixture')
        exec('class Policy:\n def __init__(self,checkpoint,device): pass\n def reset(self): pass\n def act(self,obs): return obs["proprio"][:7]*0.1',module.__dict__)
        observations=[{'proprio':np.ones(28,dtype=np.float32),'rgb':np.zeros((2,160,160,3),dtype=np.uint8)}]*3
        result=audit.compare_with_poison(module.Policy,module,None,observations,'cpu')
        self.assertTrue(result['passed']);self.assertEqual(result['max_absolute_action_difference'],0)
    def test_deliberate_hidden_oracle_is_detected(self):
        module=types.ModuleType('leaky_fixture');module.env=types.SimpleNamespace(task=types.SimpleNamespace(goal=.2))
        exec('class Policy:\n def __init__(self,checkpoint,device): pass\n def reset(self): pass\n def act(self,obs): return obs["proprio"][:7]*env.task.goal',module.__dict__)
        with self.assertRaisesRegex(AssertionError,'Privileged oracle access'):
            audit.compare_with_poison(module.Policy,module,None,[{'proprio':np.ones(28,dtype=np.float32)}],'cpu')
        self.assertEqual(module.env.task.goal,.2)
    def test_student_source_and_untrained_fixture(self):
        import torch
        from astrafactory import vision_policy
        torch.set_num_threads(2)
        findings=audit.inspect_source(vision_policy)
        self.assertEqual(findings['findings'],[])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'untrained-audit-fixture.pt';torch.manual_seed(9)
            model=vision_policy.VisualNetwork(8)
            torch.save({'model':model.state_dict(),'config':{'chunk_size':8,'history_steps':2,'execute_steps':2},'proprio_mean':np.zeros(28,dtype=np.float32),'proprio_std':np.ones(28,dtype=np.float32)},path)
            obs=[{'rgb':np.zeros((2,160,160,3),dtype=np.uint8),'proprio':np.zeros(28,dtype=np.float32)}]*4
            result=audit.compare_with_poison(vision_policy.VisualPolicy,vision_policy,path,obs,'cpu')
            self.assertTrue(result['passed'])

if __name__=='__main__':unittest.main()
