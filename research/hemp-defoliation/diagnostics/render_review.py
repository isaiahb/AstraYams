"""Rebuild the static review of the rejected mesh, never a motion replay."""
from pathlib import Path
import json
import shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OUT = BASE.parents[1] / 'runs/hemp-leaf-contact-v1'


def main():
    # Run leaf_contact.py --geometry-only first. Keep the mechanics source and
    # failure record unchanged, so the recorded experiment hash stays meaningful.
    data = np.load(OUT / 'geometry.npz')
    raw = data['raw_outline'] * 1000
    vertices = data['vertices'][:, :2] * 1000
    faces = data['faces']
    landmarks = np.loadtxt(BASE / 'reference-data/land_FUT75_2_12_4a_7.txt')
    axis = landmarks[17] - landmarks[-1]
    length = np.linalg.norm(axis)
    axis /= length
    transform = np.array([axis, [-axis[1], axis[0]]]).T * 110 / length
    landmarks = (landmarks - landmarks[-1]) @ transform

    def finish(fig, axes, name, title):
        for ax in axes:
            ax.set_aspect('equal')
            ax.set_xlabel('x (mm at assumed scale)')
            ax.set_ylabel('y (mm at assumed scale)')
            ax.spines[['top', 'right']].set_visible(False)
        fig.suptitle(title, fontsize=18)
        fig.tight_layout(rect=(0, 0, 1, .96))
        fig.savefig(OUT / name, dpi=150, bbox_inches='tight', pad_inches=.15)
        plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    axes[0].fill(*raw.T, color='#bfd0a1', ec='#819179', lw=.8)
    axes[0].set_title('Measured projected silhouette')
    axes[1].plot(*raw.T, color='#819179', lw=.8)
    colors = plt.get_cmap('tab10')
    for i in range(7):
        bases, tip = landmarks[i * 2:i * 2 + 2], landmarks[14 + i]
        axes[1].scatter(*bases.T, color=colors(i), s=16)
        axes[1].scatter(*tip, color=colors(i), s=20)
        axes[1].text(tip[0] + 1.5, tip[1], str(i + 1), color=colors(i))
        for base in bases:
            axes[1].plot([0, base[0]], [0, base[1]], '--', color=colors(i), lw=.8)
    axes[1].set_title('Seven leaflet landmarks; dashed bases are inferred')
    finish(fig, axes, 'leaflet-topology.png',
           'A projected outline does not establish a connected material sheet')

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    axes[0].fill(*raw.T, color='#bfd0a1', ec='#819179', lw=.8)
    axes[0].set_title('Published 2D outline')
    axes[1].triplot(*vertices.T, faces, color='#496d49', lw=.4)
    report = json.loads((OUT / 'geometry-report.json').read_text())
    axes[1].set_title(f"Rejected mesh: area difference {report['relative_area_difference']:.1%}")
    finish(fig, axes, 'outline-comparison.png',
           'Outline agreement does not validate anatomy or mechanics')
    shutil.copy2(HERE / 'review.html', OUT / 'index.html')
    print(OUT / 'index.html')


if __name__ == '__main__':
    main()
