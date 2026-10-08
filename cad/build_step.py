"""Build a review model from KiCad placements and the enclosure SVG.

Requires cadquery. Run from the repository root with:
    python cad/build_step.py

The component shapes below are placement and clearance models, not manufacturer
CAD. The BOM display is an 8-bit parallel Arduino shield; the circuit and Rust
firmware are wired for an SPI display, so this model does not validate function.
"""

from pathlib import Path
import re
import xml.etree.ElementTree as ET

import cadquery as cq


ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "cad/Oxidekeysenclosure.svg"
PCB_STEP = ROOT / "cad/pcbfirstdesign.step"
PCB_LAYOUT = ROOT / "pcb/pcbfirstdesign.kicad_pcb"
OUT = ROOT / "cad"
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
    neck = centered_box(14, 14, 3, x, y, 5)
    upper = centered_box(15.6, 15.6, 3.5, x, y, 8)
    stem = centered_box(4, 4, 3.5, x, y, 11.5)
    return lower.union(neck).union(upper).union(stem)


def led_model(x, y):
    """SK6812MINI package and visible window at the KiCad D1-D8 pads."""
    package = centered_box(3.5, 3.5, 1.1, x, y, 1.51)
    window = centered_box(2.2, 2.2, 0.15, x, y, 2.61)
    return package, window


def keycap_model(x, y):
    cap = (cq.Workplane("XY").workplane(offset=14.5).rect(18, 18)
           .workplane(offset=7).rect(15.4, 15.4).loft()
           .edges(">Z").fillet(0.45).translate((x, y, 0)))
    socket = centered_box(4.2, 4.2, 2, x, y, 14.5)
    return cap.cut(socket)


def open_flap(part):
    """Rotate parts mounted to the flap around its rear edge."""
    return part.translate((0, -BOARD_HEIGHT, -5)).rotate(
        (0, 0, 0), (1, 0, 0), 65
    ).translate((0, BOARD_HEIGHT, 5))


def display_parts():
    # The listed MAR2406 manual gives 72.20 x 52.70 mm board and
    # 48.96 x 36.72 mm active area. Thicknesses and connector positions
    # are review estimates until the purchased shield can be measured.
    x, y = 42.0, 126.35
    board = centered_box(72.2, 52.7, 1.6, x, y, 8.0)
    bezel = centered_box(55.0, 42.0, 2.2, x, y, 9.6)
    active = centered_box(48.96, 36.72, 0.35, x, y, 11.8)
    return (open_flap(board), open_flap(bezel), open_flap(active))


def hinge_model(x):
    # Two 25 x 15 mm decorative hinges, with illustrative leaves/pin.
    deck_leaf = centered_box(25, 7.2, 0.5, x, 87.8, 8.0)
    flap_leaf = open_flap(centered_box(25, 7.2, 0.5, x, 95.2, 8.0))
    pin = cq.Workplane("YZ").circle(1.1).extrude(25).translate(
        (x - 12.5, BOARD_HEIGHT, 8.5)
    )
    return deck_leaf.union(flap_leaf).union(pin)


def screw_model(x, y):
    shaft = cq.Workplane("XY").circle(0.95).extrude(22).translate((x, y, -13))
    head = cq.Workplane("XY").circle(2.1).extrude(1.4).translate((x, y, 8.5))
    return shaft.union(head)


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

    # 10 mm spacers leave room for a provisional 603450 battery envelope
    # beneath the board. Clearance to solder joints and leads is unverified.
    base = panel(base_group, -13.0, set())
    top = panel(top_group, 5.0, {f"rect{i}" for i in range(8, 17)} | {
        "buzzer_clearance", "controller_clearance"
    })
    flap = box_from_rect(dimensions(flap_group, "rect")[0], 5.0)
    # Illustrative open position around the back edge of the top sheet.
    flap = open_flap(flap)

    # KiCad's exported PCB is translated from its drawing origin. The board's
    # 97.75 x 91.5 mm outline then occupies x=0..97.75, y=0..91.5.
    pcb = cq.importers.importStep(str(PCB_STEP)).translate((-82.5, 101.75, 0))
    placed = placed_footprints()
    switches = {f"SW{n}": switch_model(*placed[f"SW{n}"]) for n in range(1, 9)}
    led_parts = {f"D{n}": led_model(*placed[f"D{n}"]) for n in range(1, 9)}
    leds = {ref: parts[0] for ref, parts in led_parts.items()}
    led_lenses = {ref: parts[1] for ref, parts in led_parts.items()}
    keycaps = {f"K{n}": keycap_model(*placed[f"SW{n}"]) for n in range(1, 9)}
    display_board, display_bezel, display_glass = display_parts()
    knob = cq.Workplane("XY").circle(5.75).extrude(14.5).translate(
        (*placed["RE1"], 12.0)
    )
    battery = centered_box(34, 50, 6, 48.875, 46.0, -9.5)
    charger = centered_box(4, 5, 1.75, *placed["U3"], 1.51)
    hinges = [hinge_model(x) for x in (22.5, 64.5)]
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
    for ref, part in switches.items():
        overlap = top.intersect(part)
        volume = sum(piece.Volume() for piece in overlap.solids().vals())
        if volume > 0.001:
            raise ValueError(f"Switch deck intersects {ref}: {volume:.3f} mm^3")

    spacers = []
    for circle in dimensions(base_group, "circle"):
        x, y = float(circle["cx"]), BOARD_HEIGHT - float(circle["cy"])
        spacers.append(cq.Workplane("XY").circle(2.5).circle(1.1).extrude(10).translate(
            (x, y, -10.0)
        ))
    fasteners = [screw_model(float(c["cx"]), BOARD_HEIGHT - float(c["cy"]))
                 for c in dimensions(base_group, "circle")]

    extras = []
    def include(part, name, color, group=None):
        extras.append((part, name, cq.Color(*color), group))
    for ref, part in keycaps.items():
        include(part, f"{ref} PBT blank keycap - nominal", (0.22, 0.24, 0.28), "keycaps")
    include(display_board, "MAR2406 8-bit display PCB - 72.2 x 52.7 mm", (0.12, 0.34, 0.28), "display-board")
    include(display_bezel, "MAR2406 display bezel - approximate", (0.09, 0.10, 0.12), "display-bezel")
    include(display_glass, "MAR2406 display active area - 48.96 x 36.72 mm", (0.16, 0.25, 0.31), "display-glass")
    include(knob, "11.5 x 14.5 mm encoder knob", (0.17, 0.18, 0.20), "knob")
    include(battery, "603450 LiPo 6 x 34 x 50 mm - provisional under-board placement", (0.72, 0.71, 0.63), "battery")
    include(charger, "U3 TP4056 charger IC - nominal SOIC-8", (0.22, 0.23, 0.25), "charger")
    for i, part in enumerate(hinges, 1):
        include(part, f"H{i} 25 x 15 mm brass hinge - illustrative", (0.68, 0.52, 0.20), "hinges")
    for i, part in enumerate(fasteners, 1):
        include(part, f"M2 nylon screw {i} - nominal", (0.74, 0.74, 0.69), "fasteners")
    for ref, part in led_lenses.items():
        include(part, f"{ref} LED lens", (0.94, 0.71, 0.39), "led-lenses")

    cq.exporters.export(base, str(OUT / "base-plate.step"))
    cq.exporters.export(top, str(OUT / "switch-deck.step"))
    cq.exporters.export(flap, str(OUT / "display-flap-open.step"))
    cq.exporters.export(cq.Compound.makeCompound([part.val() for part in switches.values()]), str(OUT / "switches.step"))
    cq.exporters.export(cq.Compound.makeCompound([part.val() for part in leds.values()]), str(OUT / "leds.step"))
    groups = {}
    for part, _, _, group in extras:
        groups.setdefault(group, []).append(part.val())
    for group, parts in groups.items():
        cq.exporters.export(cq.Compound.makeCompound(parts), str(OUT / f"{group}.step"))

    assembly = cq.Assembly(name="Oxide Keys review assembly")
    assembly.add(pcb, name="KiCad PCB export", color=cq.Color(0.12, 0.31, 0.24))
    for ref, part in switches.items():
        assembly.add(part, name=f"{ref} Cherry MX2A Orange - review geometry", color=cq.Color(0.18, 0.18, 0.19))
    for ref, part in leds.items():
        assembly.add(part, name=f"{ref} SK6812MINI housing - review geometry", color=cq.Color(0.85, 0.84, 0.78))
    for part, name, color, _ in extras:
        assembly.add(part, name=name, color=color)
    assembly.add(base, name="3mm base plate", color=cq.Color(0.78, 0.82, 0.85, 0.45))
    assembly.add(top, name="3mm switch deck", color=cq.Color(0.78, 0.82, 0.85, 0.45))
    assembly.add(flap, name="3mm display flap - open position", color=cq.Color(0.78, 0.82, 0.85, 0.45))
    for index, spacer in enumerate(spacers, 1):
        assembly.add(spacer, name=f"illustrative spacer {index}", color=cq.Color(0.68, 0.66, 0.62))
    # Full component geometry, saved as the repo's review assembly.
    detailed_step = OUT / "OxideKeys-review-assembly-detailed.step"
    assembly.save(str(detailed_step))


if __name__ == "__main__":
    main()
