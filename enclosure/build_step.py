"""Build a review model from KiCad placements and the enclosure SVG.

Requires cadquery. Run from the repository root with:
    python enclosure/build_step.py

The component shapes below are placement and clearance models, not manufacturer
CAD. Measure the purchased parts, display, fasteners and hinges before cutting.
"""

from pathlib import Path
import gzip
import re
import shutil
import xml.etree.ElementTree as ET

import cadquery as cq


ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "enclosure/Oxidekeysenclosure.svg"
PCB_STEP = ROOT / "production/cad/pcbfirstdesign.step"
PCB_LAYOUT = ROOT / "hardware/pcb/pcbfirstdesign.kicad_pcb"
OUT = ROOT / "production/cad"
THICKNESS = 3.0
BOARD_WIDTH = 97.75
BOARD_HEIGHT = 91.5
NS = {"svg": "http://www.w3.org/2000/svg"}


def placed_footprints():
    """Read the board's top-level footprint anchors, in the STEP frame."""
    source = PCB_LAYOUT.read_text()
    blocks = re.findall(r"(?ms)^\t\(footprint .*?(?=^\t\(footprint |^\t\(gr_rect |\Z)", source)
    placed = {}
    for block in blocks:
        reference = re.search(r'\(property "Reference" "([^"]+)', block)
        anchor = re.search(r"\n\t\t\(at ([^)]+)\)", block)
        if reference and anchor:
            x, y = (float(v) for v in anchor.group(1).split()[:2])
            placed[reference.group(1)] = (x - 182.5, 201.75 - y)
    for prefix in ("SW", "D"):
        assert all(f"{prefix}{n}" in placed for n in range(1, 9)), prefix
    return placed


def centered_box(width, depth, height, x, y, bottom):
    return cq.Workplane("XY").box(width, depth, height).translate(
        (x, y, bottom + height / 2)
    )


def switch_model(x, y):
    """MX footprint clearance shape; upper housing rests on the 3 mm deck."""
    lower = centered_box(10, 10, 6.49, x, y, 1.51)
    upper = centered_box(15.6, 15.6, 3.5, x, y, 8)
    stem = centered_box(4, 4, 3.5, x, y, 11.5)
    return lower.union(upper).union(stem)


def led_model(x, y):
    """SK6812MINI package and visible window at the KiCad D1-D8 pads."""
    package = centered_box(3.5, 3.5, 1.1, x, y, 1.51)
    window = centered_box(2.2, 2.2, 0.15, x, y, 2.61)
    return package.union(window)


def dimensions(group, tag):
    return [dict(element.attrib) for element in group.findall(f"svg:{tag}", NS)]


def box_from_rect(rect, bottom):
    x, y = float(rect["x"]), float(rect["y"])
    w, h = float(rect["width"]), float(rect["height"])
    # KiCad STEP's Y axis is opposite the SVG's Y axis.
    return cq.Workplane("XY").box(w, h, THICKNESS).translate(
        (x + w / 2, BOARD_HEIGHT - y - h / 2, bottom + THICKNESS / 2)
    )


def cut_circles(part, circles, bottom):
    for circle in circles:
        x, y, r = (float(circle[k]) for k in ("cx", "cy", "r"))
        tool = cq.Workplane("XY").circle(r).extrude(THICKNESS + 2).translate(
            (x, BOARD_HEIGHT - y, bottom - 1)
        )
        part = part.cut(tool)
    return part


def panel(group, bottom, cut_rects):
    rects = dimensions(group, "rect")
    part = box_from_rect(rects[0], bottom)
    part = cut_circles(part, dimensions(group, "circle"), bottom)
    for rect in rects[1:]:
        if rect["id"] in cut_rects:
            x, y = float(rect["x"]), float(rect["y"])
            w, h = float(rect["width"]), float(rect["height"])
            tool = cq.Workplane("XY").box(w, h, THICKNESS + 2).translate(
                (x + w / 2, BOARD_HEIGHT - y - h / 2, bottom + THICKNESS / 2)
            )
            part = part.cut(tool)
    for path in group.findall("svg:path", NS):
        if path.attrib.get("id") != "header_switch_clearance":
            continue
        points = [
            (float(x), BOARD_HEIGHT - float(y))
            for x, y in re.findall(r"([\d.]+),([\d.]+)", path.attrib["d"])
        ]
        tool = cq.Workplane("XY").polyline(points).close().extrude(
            THICKNESS + 2
        ).translate((0, 0, bottom - 1))
        part = part.cut(tool)
    return part


def main():
    tree = ET.parse(SVG)
    base_group = tree.find(".//svg:g[@id='base_plate']", NS)
    top_group = tree.find(".//svg:g[@id='top_panel']", NS)
    flap_group = tree.find(".//svg:g[@id='lcd_flap']", NS)
    assert base_group is not None and top_group is not None and flap_group is not None
    OUT.mkdir(parents=True, exist_ok=True)

    # Base top is z=-6; the 6 mm spacers then end at the PCB underside (z=0).
    base = panel(base_group, -9.0, set())
    top = panel(top_group, 5.0, {f"rect{i}" for i in range(8, 17)} | {
        "buzzer_clearance", "controller_clearance"
    })
    flap = box_from_rect(dimensions(flap_group, "rect")[0], 5.0)
    # Illustrative open position around the back edge of the top sheet.
    flap = flap.translate((0, -BOARD_HEIGHT, -5)).rotate(
        (0, 0, 0), (1, 0, 0), 65
    ).translate((0, BOARD_HEIGHT, 5))

    # KiCad's exported PCB is translated from its drawing origin. The board's
    # 97.75 x 91.5 mm outline then occupies x=0..97.75, y=0..91.5.
    pcb = cq.importers.importStep(str(PCB_STEP)).translate((-82.5, 101.75, 0))
    placed = placed_footprints()
    switches = {f"SW{n}": switch_model(*placed[f"SW{n}"]) for n in range(1, 9)}
    leds = {f"D{n}": led_model(*placed[f"D{n}"]) for n in range(1, 9)}
    for n in range(1, 9):
        sx, sy = placed[f"SW{n}"]
        # D1-D8 are under the adjacent switch edge, not at the switch centre.
        led = min(leds, key=lambda ref: sum((a - b) ** 2 for a, b in zip(placed[ref], (sx - 2.5, sy - 7.45))))
        lx, ly = placed[led]
        assert abs(lx - (sx - 2.5)) < 0.4 and abs(ly - (sy - 7.45)) < 0.4, (f"SW{n}", led)
    for index, solid in enumerate(pcb.solids().vals()):
        overlap = top.intersect(cq.Workplane("XY").newObject([solid]))
        volume = sum(piece.Volume() for piece in overlap.solids().vals())
        if volume > 0.001:
            raise ValueError(f"Switch deck intersects KiCad STEP solid {index}: {volume:.3f} mm^3")

    spacers = []
    for circle in dimensions(base_group, "circle"):
        x, y = float(circle["cx"]), BOARD_HEIGHT - float(circle["cy"])
        spacers.append(cq.Workplane("XY").circle(2.5).circle(1.1).extrude(6).translate(
            (x, y, -6.0)
        ))

    cq.exporters.export(base, str(OUT / "base-plate.step"))
    cq.exporters.export(top, str(OUT / "switch-deck.step"))
    cq.exporters.export(flap, str(OUT / "display-flap-open.step"))
    cq.exporters.export(cq.Compound.makeCompound([part.val() for part in switches.values()]), str(OUT / "switches.step"))
    cq.exporters.export(cq.Compound.makeCompound([part.val() for part in leds.values()]), str(OUT / "leds.step"))

    assembly = cq.Assembly(name="Oxide Keys review assembly")
    assembly.add(pcb, name="KiCad PCB export", color=cq.Color(0.12, 0.31, 0.24))
    for ref, part in switches.items():
        assembly.add(part, name=f"{ref} Cherry MX2A Orange - review geometry", color=cq.Color(0.18, 0.18, 0.19))
    for ref, part in leds.items():
        assembly.add(part, name=f"{ref} SK6812MINI - review geometry", color=cq.Color(0.93, 0.76, 0.42))
    assembly.add(base, name="3mm base plate", color=cq.Color(0.78, 0.82, 0.85, 0.45))
    assembly.add(top, name="3mm switch deck", color=cq.Color(0.78, 0.82, 0.85, 0.45))
    assembly.add(flap, name="3mm display flap - open position", color=cq.Color(0.78, 0.82, 0.85, 0.45))
    for index, spacer in enumerate(spacers, 1):
        assembly.add(spacer, name=f"illustrative spacer {index}", color=cq.Color(0.68, 0.66, 0.62))
    # Keep the complete component geometry, while offering a smaller STEP that
    # opens directly in CAD programs and can be downloaded from the repo.
    detailed_step = OUT / "OxideKeys-review-assembly-detailed.step"
    assembly.save(str(detailed_step))
    with detailed_step.open("rb") as source, (OUT / "OxideKeys-review-assembly-detailed.step.gz").open("wb") as target:
        with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as compressed:
            shutil.copyfileobj(source, compressed)

    compact = cq.Assembly(name="Oxide Keys review assembly - component envelopes")
    pcb_solids = pcb.solids().vals()
    board = max(pcb_solids, key=lambda solid: solid.Volume())
    compact.add(board, name="PCB outline and holes", color=cq.Color(0.12, 0.31, 0.24))
    for index, solid in enumerate(pcb_solids, 1):
        if solid is board:
            continue
        bounds = solid.BoundingBox()
        envelope = cq.Workplane("XY").box(bounds.xlen, bounds.ylen, bounds.zlen).translate(
            ((bounds.xmin + bounds.xmax) / 2,
             (bounds.ymin + bounds.ymax) / 2,
             (bounds.zmin + bounds.zmax) / 2)
        )
        compact.add(envelope, name=f"Component envelope {index}", color=cq.Color(0.35, 0.35, 0.37))
    for ref, part in switches.items():
        compact.add(part, name=f"{ref} Cherry MX2A Orange - review geometry")
    for ref, part in leds.items():
        compact.add(part, name=f"{ref} SK6812MINI - review geometry")
    compact.add(base, name="3mm base plate")
    compact.add(top, name="3mm switch deck")
    compact.add(flap, name="3mm display flap - open position")
    for index, spacer in enumerate(spacers, 1):
        compact.add(spacer, name=f"Illustrative spacer {index}")
    compact.save(str(OUT / "OxideKeys-review-assembly.step"))


if __name__ == "__main__":
    main()
