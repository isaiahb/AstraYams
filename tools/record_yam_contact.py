"""Record real free-peg contact tests; insertion is attempted only after grasp checks pass."""
from pathlib import Path
import argparse
import json
import numpy as np
import imageio.v2 as imageio
from PIL import Image, ImageDraw
try:
    from .check_yam_contact import validate, emit_step, ROOT, load_callable
except ImportError:
    from check_yam_contact import validate, emit_step, ROOT, load_callable


class VideoCapture:
    def __init__(self, out, mode, every, camera):
        self.out, self.mode, self.every, self.camera = out, mode, every, camera
        self.writer = None
        self.steps = 0
        self.last_image = None

    def __call__(self, env, row):
        self.steps += 1
        if self.steps != 1 and (self.steps-1) % self.every:
            return
        if self.writer is None:
            fps = 1 / (env.model.opt.timestep * env.frame_skip * self.every)
            self.writer = imageio.get_writer(self.out / f'{self.mode}.mp4', fps=fps, codec='libx264', quality=8)
        env.specification['camera'] = self.camera
        image = Image.fromarray(env.render())
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, image.width, 78), fill=(18, 27, 37))
        draw.text((18, 10), f'YAM  |  FREE PEG CONTACT PHYSICS  |  {self.mode.upper()}', fill='white', font_size=20)
        draw.text((18, 43), f"Scripted test   t={row['sim_time']:.2f}s   Peg z={1000*row['peg_z_m']:.1f}mm   Finger forces L/R={row['left_force_n']:.1f}/{row['right_force_n']:.1f}N", fill=(194,218,231), font_size=16)
        self.writer.append_data(np.asarray(image))
        self.last_image = image
        if self.steps == 1:
            image.save(self.out / f'{self.mode}-start.png')

    def close(self):
        if self.writer:
            self.writer.close()
            self.writer = None
        if self.last_image:
            self.last_image.save(self.out / f'{self.mode}-last-frame.png')


def main():
    from astrafactory.contact_env import ContactEnv
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task', default=str(ROOT / 'tasks/yam_contact_insertion'))
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--teacher', default='astrafactory.contact_env:teacher')
    p.add_argument('--out', type=Path, default=ROOT / 'runs/yam-contact-recording')
    p.add_argument('--every', type=int, default=2)
    p.add_argument('--camera', default='overview', help='Existing MJCF camera name; insertion gives a closer grasp/task view')
    p.add_argument('--insertion', action='store_true', help='Attempt insertion only after all three contact validations pass')
    args = p.parse_args()
    teacher = load_callable(args.teacher)
    if args.every < 1:
        p.error('--every must be positive')
    args.out.mkdir(parents=True, exist_ok=True)
    if any(args.out.iterdir()):
        p.error('Output directory must be empty')
    captures = {mode: VideoCapture(args.out, mode, args.every, args.camera) for mode in ['lift', 'drop', 'zero-friction']}
    try:
        report, traces = validate(args.task, args.seed, captures, args.teacher)
    finally:
        for capture in captures.values():
            capture.close()
    for mode, rows in traces.items():
        (args.out / f'{mode}-trace.json').write_text(json.dumps(rows))
    if args.insertion:
        if report['passed']:
            env = ContactEnv(args.task, render_mode='rgb_array')
            capture = VideoCapture(args.out, 'insertion-attempt', args.every, args.camera)
            rows = []
            try:
                obs, info = env.reset(seed=args.seed)
                for _ in range(env.horizon):
                    before = env.data.qpos.copy()
                    action = teacher(env)
                    if not np.array_equal(before, env.data.qpos):
                        raise AssertionError('Teacher assigned physical qpos')
                    obs, done, row = emit_step(env, action, obs, capture, info)
                    rows.append(row)
                    if done:
                        break
            finally:
                capture.close()
                env.close()
            report['insertion_attempt'] = {'is_success': bool(rows[-1].get('is_success', False)), 'steps': len(rows), 'last': rows[-1]}
            (args.out / 'insertion-trace.json').write_text(json.dumps(rows))
        else:
            report['insertion_attempt'] = {'skipped': 'Physical contact validation did not pass'}
    report['camera'] = args.camera
    report['video_alignment'] = 'Video frames show the post-step physics state; trace records pre-action and next observations'
    (args.out / 'report.json').write_text(json.dumps(report, indent=2))
    print('Contact validation passed:', report['passed'], flush=True)
    if args.insertion:
        print('Insertion:', report['insertion_attempt'].get('is_success', report['insertion_attempt'].get('skipped')), flush=True)


if __name__ == '__main__':
    main()
