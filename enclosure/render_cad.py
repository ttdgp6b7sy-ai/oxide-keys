"""Render actual STEP geometry to two README images (cadquery, matplotlib)."""
from pathlib import Path
import cadquery as cq
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/images'
CAD = ROOT / 'production/cad'

def add_part(ax, filename, rgb, alpha=1.0):
    shape = cq.importers.importStep(str(CAD / filename)).val()
    if filename == 'pcbfirstdesign.step':
        shape = shape.translate((-82.5, 101.75, 0))
    verts, triangles = shape.tessellate(0.8, 0.3)
    points = np.array([[v.x, v.y, v.z] for v in verts])
    faces = points[np.array(triangles)]
    normals = np.cross(faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    normals /= np.maximum(lengths[:, None], 1e-9)
    light = np.array([0.3, -0.45, 0.84])
    illumination = np.clip(0.64 + 0.36 * (normals @ light), 0.32, 1)
    colors = np.clip(np.array(rgb)[None, :] * illumination[:, None], 0, 1)
    ax.add_collection3d(Poly3DCollection(faces, facecolors=colors, edgecolors='none', alpha=alpha))

def render(filename, elev, azim):
    fig = plt.figure(figsize=(12, 8.4), dpi=125, facecolor='#f7f6f2')
    ax = fig.add_subplot(111, projection='3d', facecolor='#f7f6f2')
    add_part(ax, 'pcbfirstdesign.step', (0.14, 0.39, 0.32))
    add_part(ax, 'base-plate.step', (0.64, 0.72, 0.75), 0.8)
    add_part(ax, 'switch-deck.step', (0.61, 0.69, 0.72), 0.48)
    add_part(ax, 'display-flap-open.step', (0.65, 0.73, 0.76), 0.9)
    ax.set(xlim=(-15, 112), ylim=(-13, 157), zlim=(-15, 76))
    ax.set_box_aspect((127, 170, 91), zoom=0.88)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.savefig(OUT / filename, facecolor=fig.get_facecolor(), bbox_inches='tight', pad_inches=0.15)
    plt.close(fig)

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    render('cad-overview.png', 33, -70)
    render('cad-side.png', 16, 20)
