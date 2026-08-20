# Oxide Keys

An 8-key macro pad with rotary encoder, OLED display, and RGB underglow, to be built entirely in Rust on the Raspberry Pi Pico W.

## What It Does
- 8 Cherry MX mechanical keys for custom shortcuts
- Metal-knurled rotary encoder for volume/scrolling
- OLED display showing active layer
- WS2812B RGB underglow with warm amber tones
- USB HID, works on any computer without drivers

## Design
- Controller: Raspberry Pi Pico W (RP2040)
- Firmware: Rust with `rp-hal`, `usb-device`, `embedded-hal`
- Wiring: See `/design` folder for schematic
- Enclosure: Black gloss acrylic base plate + M2 standoffs

## BOM
See `BOM.csv` for full parts list with verified Australian suppliers. Equivalent of 105 USD.
