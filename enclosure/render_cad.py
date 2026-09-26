"""Make PNG previews from the STEP assembly for the README."""
from pathlib import Path
import math

import cadquery as cq
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/images'
CAD = ROOT / 'production/cad'
SIZE = (1600, 1150)
BACKGROUND = np.array((249, 248, 245), dtype=np.uint8)

PARTS = {
    'pcbfirstdesign.step': (36, 99, 81),
    'leds.step': (219, 218, 206),
    'led-lenses.step': (246, 176, 84),
    'switches.step': (52, 55, 60),
    'battery.step': (188, 178, 151),
    'base-plate.step': (192, 203, 204),
    'switch-deck.step': (203, 213, 214),
    'display-flap-open.step': (196, 209, 211),
    'charger.step': (51, 53, 59),
    'hinges.step': (186, 143, 63),
    'display-board.step': (35, 88, 73),
    'display-bezel.step': (32, 34, 39),
    'display-glass.step': (35, 62, 77),
    'keycaps.step': (88, 94, 103),
    'knob.step': (50, 52, 57),
    'fasteners.step': (178, 179, 173),
}
ACRYLIC = {'base-plate.step', 'switch-deck.step', 'display-flap-open.step'}


def expand_edges(mask):
    expanded = mask.copy()
    expanded[1:] |= mask[:-1]
    expanded[:-1] |= mask[1:]
    expanded[:, 1:] |= mask[:, :-1]
    expanded[:, :-1] |= mask[:, 1:]
    return expanded


def load_parts():
    parts = {}
    light = np.array((0.38, -0.48, 0.79))
    for filename, color in PARTS.items():
        shape = cq.importers.importStep(str(CAD / filename)).val()
        if filename == 'pcbfirstdesign.step':
            shape = shape.translate((-82.5, 101.75, 0))
        vertices, triangles = shape.tessellate(0.8, 0.3)
        points = np.array([[v.x, v.y, v.z] for v in vertices], dtype=np.float32)
        faces = points[np.asarray(triangles, dtype=np.int32)]
        normals = np.cross(faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0])
        normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-7)
        shade = 0.73 + 0.27 * np.abs(normals @ light)
        colors = np.clip(np.asarray(color) * shade[:, None], 0, 255).astype(np.uint8)
        parts[filename] = (faces, colors)
    return parts


def render(parts, filename, elev, azim, names):
    width, height = SIZE
    angle, elevation = math.radians(azim), math.radians(elev)
    forward = np.array((math.cos(elevation) * math.cos(angle),
                        math.cos(elevation) * math.sin(angle), math.sin(elevation)))
    right = np.array((-math.sin(angle), math.cos(angle), 0.0))
    up = np.cross(forward, right)
    projected = np.concatenate([parts[name][0].reshape(-1, 3) for name in names])
    horizontal = projected @ right
    vertical = projected @ up
    scale = min(width * 0.88 / np.ptp(horizontal),
                height * 0.88 / np.ptp(vertical))
    center_x = (horizontal.min() + horizontal.max()) / 2
    center_y = (vertical.min() + vertical.max()) / 2
    image = np.empty((height, width, 3), dtype=np.uint8)
    image[:] = BACKGROUND
    depth = np.full((height, width), -np.inf, dtype=np.float32)
    part_id = np.zeros((height, width), dtype=np.uint8)
    acrylic_depth = np.full((height, width), -np.inf, dtype=np.float32)
    acrylic_color = np.zeros((height, width, 3), dtype=np.uint8)
    acrylic_id = np.zeros((height, width), dtype=np.uint8)

    for number, name in enumerate(names, 1):
        is_acrylic = name in ACRYLIC
        faces, colors = parts[name]
        px = width / 2 + (faces @ right - center_x) * scale
        py = height / 2 - (faces @ up - center_y) * scale
        pz = faces @ forward
        for xs, ys, zs, color in zip(px, py, pz, colors):
            x0 = max(0, int(math.floor(xs.min())))
            x1 = min(width, int(math.ceil(xs.max())) + 1)
            y0 = max(0, int(math.floor(ys.min())))
            y1 = min(height, int(math.ceil(ys.max())) + 1)
            if x0 >= x1 or y0 >= y1:
                continue
            denominator = ((ys[1] - ys[2]) * (xs[0] - xs[2])
                           + (xs[2] - xs[1]) * (ys[0] - ys[2]))
            if abs(denominator) < 1e-6:
                continue
            yy, xx = np.mgrid[y0:y1, x0:x1]
            xx = xx + 0.5
            yy = yy + 0.5
            a = ((ys[1] - ys[2]) * (xx - xs[2])
                 + (xs[2] - xs[1]) * (yy - ys[2])) / denominator
            b = ((ys[2] - ys[0]) * (xx - xs[2])
                 + (xs[0] - xs[2]) * (yy - ys[2])) / denominator
            c = 1 - a - b
            near = a * zs[0] + b * zs[1] + c * zs[2]
            tile_depth = (acrylic_depth if is_acrylic else depth)[y0:y1, x0:x1]
            visible = (a >= -1e-5) & (b >= -1e-5) & (c >= -1e-5) & (near > tile_depth)
            tile_depth[visible] = near[visible]
            if is_acrylic:
                acrylic_color[y0:y1, x0:x1][visible] = color
                acrylic_id[y0:y1, x0:x1][visible] = number
            else:
                image[y0:y1, x0:x1][visible] = color
                part_id[y0:y1, x0:x1][visible] = number

    front_acrylic = (acrylic_id != 0) & (acrylic_depth > depth)
    image[front_acrylic] = np.clip(
        image[front_acrylic].astype(np.float32) * 0.75
        + acrylic_color[front_acrylic].astype(np.float32) * 0.25, 0, 255
    ).astype(np.uint8)

    # Outline visible parts after depth testing; never draw tessellation edges.
    edges = np.zeros((height, width), dtype=bool)
    for axis in (0, 1):
        ids = np.roll(part_id, 1, axis=axis)
        edges |= (part_id != 0) & (ids != part_id)
    edges = expand_edges(edges) & (part_id != 0)
    image[edges] = (image[edges].astype(np.float32) * 0.62).astype(np.uint8)
    acrylic_edges = np.zeros((height, width), dtype=bool)
    visible_id = np.where(front_acrylic, acrylic_id, 0)
    for axis in (0, 1):
        acrylic_edges |= (visible_id != 0) & (np.roll(visible_id, 1, axis=axis) != visible_id)
    acrylic_edges = expand_edges(acrylic_edges) & front_acrylic
    image[acrylic_edges] = (image[acrylic_edges].astype(np.float32) * 0.7).astype(np.uint8)
    Image.fromarray(image).resize((1400, 1006), Image.Resampling.LANCZOS).save(OUT / filename)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    parts = load_parts()
    detailed = list(PARTS)
    render(parts, 'cad-overview.png', 42, -68, detailed)
    render(parts, 'cad-side.png', 16, 20, detailed)
    render(parts, 'cad-switch-led-placement.png', 62, -70,
           ['pcbfirstdesign.step', 'leds.step', 'led-lenses.step', 'switches.step'])
    render(parts, 'cad-battery.png', -22, -60, detailed)
