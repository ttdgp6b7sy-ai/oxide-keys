# Oxide Keys

A project with a display that has the ability to play very simple games to kill time and also a fun way to integrate Rust (the language I am learning).
The hardware is mainly composed of an 8-key mini game player with rotary encoder, LCD display, and RGB underglow on the Raspberry Pi Pico W, where I aim to include as much Rust as I can in this project.

<img width="764" height="560" alt="oxidekeys_wirediagram drawio(2)" src="https://github.com/user-attachments/assets/37bf9df5-a63c-40bd-98a6-ff536cb3bac4" />

## Demo
No physical build yet but the image above shows a diagram of the wiring.


## Quickstart
Hardware is not built yet. And the cargo build will be created once I can test it against the hardware.


## Features that I will implement
- The switches are designed so that each key is important in navigating the screen where I want to create a launcher which you can scroll through a section of simple games similar to pong and space invader that I create. These keys will be assigned certain roles in the future such as selecting, navigation (mimicking the hjkl keys etc), and the amount of keys allows a wide use-case in games that I will develop specifically for this device.
- The lights underneath the keys will be an amber glow until pressed in which they will react in a white colour once pressed.
- Want the encoder knob to be used to scroll on the idle screen/Launcher.

## Design
- Uses a pico W as the controller.
- firmware stack includes embedded hal, probers and rp2040 hal.
- fullparts list is in the BOM.csv - 101 USD.

## Todo
The potential of the encoder knob in some games is something I want to explore.

## How it works
Will explain once started.

## Credits
WIP.
