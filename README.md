# Oxide Keys

A mini game console with 8 keys and a display, which has the ability to play very simple games to kill time and also a fun way to integrate Rust (the language I am learning).
The hardware is mainly composed of an 8-key mini game player with rotary encoder, LCD display that folds on a hinge, and RGB underglow on the Raspberry Pi Pico W, where I aim to include as much Rust as I can in this project.

![Oxide Keys Pcb Board](docs/images/oxidekeyspcb.png)
![Wokwi CI](https://github.com/ttdgp6b7sy-ai/oxide-keys/actions/workflows/wokwi.yml/badge.svg)

## CAD views
![Oxide Keys with the parts in place](docs/images/cad-overview.png)
![Oxide Keys CAD from the side](docs/images/cad-side.png)
![Switches and LEDs on the PCB](docs/images/cad-switch-led-placement.png)
![Battery below the PCB](docs/images/cad-battery.png)

[Assembly STEP](production/cad/OxideKeys-review-assembly-detailed.step) · [Enclosure SVG](enclosure/Oxidekeysenclosure.svg)

Production files: [CAD](production/cad/) · [UF2 firmware](production/firmware/oxide-keys.uf2) · [firmware source package](production/firmware/firmware-source.zip) · [Gerbers](production/gerbers.zip). I added the switches, LEDs, keycaps, display, knob, battery and hinges to the CAD. The extra switches and LEDs in the BOM are spares. I still need to test fit the acrylic and hinges when I get the parts.

The display linked in [BOM.csv](BOM.csv) is an 8-bit Arduino shield, but my PCB and Rust code use SPI. I also found two PCB issues: SW5 has no ground, and the display header joins GPIO16 and GPIO19 while its other pins don't match the Rust code. I need to sort out the board and choose an SPI display before building it. The 1N4148 pack in the BOM also isn't on the PCB.

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
