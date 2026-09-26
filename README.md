# Oxide Keys

A mini game console with 8 keys and a display, which has the ability to play very simple games to kill time and also a fun way to integrate Rust (the language I am learning).
The hardware is mainly composed of an 8-key mini game player with rotary encoder, LCD display that folds on a hinge, and RGB underglow on the Raspberry Pi Pico W, where I aim to include as much Rust as I can in this project.

![Oxide Keys Pcb Board](docs/images/oxidekeyspcb.png)
![Wokwi CI](https://github.com/ttdgp6b7sy-ai/oxide-keys/actions/workflows/wokwi.yml/badge.svg)

## CAD views
![Board with eight switches and caps, display, knob and fasteners; acrylic hidden to show the components](docs/images/cad-overview.png)
![Acrylic enclosure and display flap from the side](docs/images/cad-side.png)
![Eight LEDs beside the switch footprints, with the deck removed and switch housings transparent](docs/images/cad-switch-led-placement.png)
![Battery location under the PCB](docs/images/cad-battery.png)

[Assembly STEP](production/cad/OxideKeys-review-assembly-detailed.step) · [Enclosure SVG](enclosure/Oxidekeysenclosure.svg) · [Gerbers](production/gerbers.zip) · [Firmware UF2](production/firmware/oxide-keys.uf2)

The STEP assembly shows the eight Cherry MX2A Orange switches (`SW1`–`SW8`),
eight SK6812MINI LEDs (`D1`–`D8`), eight blank keycaps, encoder knob, battery,
TP4056 charger IC, display board, two brass hinges, acrylic plates, four M2
standoffs and fasteners. The KiCad export supplies the PCB, Pico W, buzzer,
encoder, header and the components that have 3D models. The LEDs sit toward
one edge of each switch rather than directly under its stem. Spare parts,
shipping, raw sheet and wire stock are purchase quantities, not fitted parts.

**Display mismatch:** the BOM links to the MAR2406 Arduino shield. Its [manual](https://www.lcdwiki.com/res/MAR2406/2.4inch_Arduino_8BIT_Module_MAR2406_User_Manual_EN.pdf)
specifies an 8-bit parallel interface and a 72.2 × 52.7 mm board. The schematic
and Rust firmware instead use an SPI ILI9341 module. The CAD now represents the
listed shield's board size and screen area on a larger flap, but it will not
operate from the current display wiring. The 1N4148 pack in the BOM also has
no fitted footprint on the current PCB.

The added parts are named review geometry, not manufacturer STEP files.
Battery placement beneath the PCB uses 10 mm standoffs; switch clips in 3 mm
acrylic, light path, hinge mounting and clearances still need measurements or a
physical test fit. Do not cut the enclosure or buy the parallel display as a
drop-in replacement for the SPI module on the basis of these renders.

## Demo
No physical build yet but the image above shows the PCB board to be made.

![Oxide Keys running in simulation](firmware/wokwi-demo.gif)

## Quickstart
Hardware was made on KiCad, with the PCB board and schematics, you can open hardware/pcb to view this. The cargo build was made from firmware and can be cargo built, cd firmware && cargo build. Also the Cad enclosure utilises the mount standoffs instead of being 3d in enclosure/


## Features that I will implement
- The switches are designed so that each key is important in navigating the screen where I want to create a launcher which you can scroll through a section of simple games similar to pong and space invader that I create. These keys will be assigned certain roles in the future such as selecting, navigation (mimicking the hjkl keys etc), and the amount of keys allows a wide use-case in games that I will develop specifically for this device.
- The lights underneath the keys will be an amber glow until pressed in which they will react in a white colour once pressed.
- Want the encoder knob to be used to scroll on the idle screen/Launcher.

## Design
- Uses a pico W as the controller.
- firmware stack includes embedded hal, probers and rp2040 hal. It lives in firmware/ and builds with cargo build
- display sits on a hinge now
- fullparts list is in [BOM.csv](BOM.csv).
- the cad enclosure that I am incorporating uses a 2d laser cut acrylic with mounted standoffs in between. Meaning that I can still incorporate cool aesthetics with the layer being transparent on purpose.

## Todo
The potential of the encoder knob in some games is something I want to explore.

## Credits
credits to stardance for inspo + help.
