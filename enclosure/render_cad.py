"""Render the review STEP parts for the README (cadquery, matplotlib)."""
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

def add_part(faces_all, colors_all, filename, rgb, alpha=1.0, zoffset=0):
    shape = cq.importers.importStep(str(CAD / filename)).val()
    if filename == 'pcbfirstdesign.step':
        shape = shape.translate((-82.5, 101.75, 0))
    if zoffset:
        shape = shape.translate((0, 0, zoffset))
    verts, triangles = shape.tessellate(0.8, 0.3)
    points = np.array([[v.x, v.y, v.z] for v in verts])
    faces = points[np.array(triangles)]
    normals = np.cross(faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    normals /= np.maximum(lengths[:, None], 1e-9)
    light = np.array([0.3, -0.45, 0.84])
    illumination = np.clip(0.64 + 0.36 * (normals @ light), 0.32, 1)
    colors = np.clip(np.array(rgb)[None, :] * illumination[:, None], 0, 1)
    faces_all.extend(faces)
    colors_all.extend(np.column_stack((colors, np.full(len(colors), alpha))))

def render(filename, elev, azim, placement=False, show_panels=True):
    fig = plt.figure(figsize=(12, 8.4), dpi=125, facecolor='#f7f6f2')
    ax = fig.add_subplot(111, projection='3d', facecolor='#f7f6f2')
    faces_all, colors_all = [], []
    def add(filename, rgb, alpha=1.0):
        add_part(faces_all, colors_all, filename, rgb, alpha)
    add('pcbfirstdesign.step', (0.14, 0.39, 0.32))
    add('leds.step', (0.97, 0.68, 0.24))
    add('switches.step', (0.24, 0.25, 0.26), 0.28 if placement else 1)
    if not placement:
        add('battery.step', (0.75, 0.72, 0.61))
        if show_panels:
            add('base-plate.step', (0.64, 0.72, 0.75), 0.8)
            add('switch-deck.step', (0.61, 0.69, 0.72), 0.25)
            add('display-flap-open.step', (0.65, 0.73, 0.76), 0.55)
        add('charger.step', (0.23, 0.24, 0.27))
        add('hinges.step', (0.75, 0.57, 0.25))
        add('display-board.step', (0.12, 0.35, 0.29))
        add('display-bezel.step', (0.10, 0.11, 0.13))
        add('display-glass.step', (0.15, 0.25, 0.32))
        add('keycaps.step', (0.28, 0.30, 0.34))
        add('knob.step', (0.19, 0.20, 0.22))
        add('fasteners.step', (0.75, 0.75, 0.70))
        ax.set(xlim=(-7, 105), ylim=(-12, 128), zlim=(-14, 77))
        ax.set_box_aspect((112, 140, 91), zoom=0.95)
    else:
        ax.set(xlim=(-5, 100), ylim=(37, 92), zlim=(0, 22))
        ax.set_box_aspect((105, 55, 30), zoom=0.85)
    ax.add_collection3d(Poly3DCollection(faces_all, facecolors=colors_all, edgecolors='none'))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.savefig(OUT / filename, facecolor=fig.get_facecolor(), bbox_inches='tight', pad_inches=0.15)
    plt.close(fig)

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    render('cad-overview.png', 37, -70, show_panels=False)
    render('cad-side.png', 16, 20)
    render('cad-switch-led-placement.png', 62, -70, placement=True)
    render('cad-battery.png', -22, -60, show_panels=False)
