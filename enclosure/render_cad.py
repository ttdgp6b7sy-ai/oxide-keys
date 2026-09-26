"""Make PNG previews from the STEP assembly for the README."""
from pathlib import Path
import math

import cadquery as cq
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/images'
CAD = ROOT / 'production/cad'
SIZE = (1200, 900)
BACKGROUND = np.array((248, 247, 244), dtype=np.uint8)

PARTS = {
    'pcbfirstdesign.step': (36, 99, 81),
    'leds.step': (246, 174, 62),
    'switches.step': (55, 57, 62),
    'battery.step': (188, 178, 151),
    'base-plate.step': (192, 203, 204),
    'switch-deck.step': (203, 213, 214),
    'display-flap-open.step': (196, 209, 211),
    'charger.step': (51, 53, 59),
    'hinges.step': (186, 143, 63),
    'display-board.step': (35, 88, 73),
    'display-bezel.step': (32, 34, 39),
    'display-glass.step': (51, 83, 101),
    'keycaps.step': (85, 89, 98),
    'knob.step': (50, 52, 57),
    'fasteners.step': (178, 179, 173),
}


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


def render(parts, filename, elev, azim, names, bounds):
    width, height = SIZE
    angle, elevation = math.radians(azim), math.radians(elev)
    forward = np.array((math.cos(elevation) * math.cos(angle),
                        math.cos(elevation) * math.sin(angle), math.sin(elevation)))
    right = np.array((-math.sin(angle), math.cos(angle), 0.0))
    up = np.cross(forward, right)
    center = np.array(((bounds[0] + bounds[1]) / 2,
                       (bounds[2] + bounds[3]) / 2,
                       (bounds[4] + bounds[5]) / 2))
    corners = np.array([[x, y, z] for x in bounds[:2]
                        for y in bounds[2:4] for z in bounds[4:]]) - center
    scale = min(width * 0.86 / np.ptp(corners @ right),
                height * 0.84 / np.ptp(corners @ up))
    image = np.empty((height, width, 3), dtype=np.uint8)
    image[:] = BACKGROUND
    depth = np.full((height, width), -np.inf, dtype=np.float32)

    for name in names:
        faces, colors = parts[name]
        relative = faces - center
        px = width / 2 + (relative @ right) * scale
        py = height / 2 - (relative @ up) * scale
        pz = relative @ forward
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
            tile_depth = depth[y0:y1, x0:x1]
            visible = (a >= -1e-5) & (b >= -1e-5) & (c >= -1e-5) & (near > tile_depth)
            tile_depth[visible] = near[visible]
            image[y0:y1, x0:x1][visible] = color

    Image.fromarray(image).resize((1000, 750), Image.Resampling.LANCZOS).save(OUT / filename)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    parts = load_parts()
    detailed = list(PARTS)
    render(parts, 'cad-overview.png', 37, -70,
           [p for p in detailed if p not in ('base-plate.step', 'switch-deck.step', 'display-flap-open.step')],
           (-7, 105, -12, 128, -14, 77))
    render(parts, 'cad-side.png', 16, 20, detailed,
           (-7, 105, -12, 128, -14, 77))
    render(parts, 'cad-switch-led-placement.png', 62, -70,
           ['pcbfirstdesign.step', 'leds.step', 'switches.step'],
           (-5, 100, 37, 92, 0, 22))
    render(parts, 'cad-battery.png', -22, -60,
           [p for p in detailed if p not in ('base-plate.step', 'switch-deck.step', 'display-flap-open.step')],
           (-7, 105, -12, 128, -14, 77))
