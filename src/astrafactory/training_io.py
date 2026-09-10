"""Small atomic checkpoint writes: never destroy the last good PPO checkpoint."""
from pathlib import Path
import os, shutil

def save_policy(policy, path):
    path = Path(path).with_suffix('.zip')
    path.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(path.parent).free < 16 * 1024**2:
        raise OSError('Less than 16 MB free; preserving existing checkpoints.')
    temporary = path.with_name(path.stem + '.pending.zip')
    policy.save(temporary)
    with temporary.open('rb') as f:
        os.fsync(f.fileno())
    temporary.replace(path)
    return path
