# Project etzee

The goal of this project is to create a highly modular, customizable, reparable, extendable and versatile keyboard ecosystem that caters to a wide range of users, from casual typists to creative professionals. Each module is an experiment in human–machine interaction, blending tactile, visual, and haptic feedback to create a customizable ecosystem of connected input devices. The envisioned ecosystem includes two main categories of devices:

Primary input devices, marked with b in their names for board

Accessory devices, marked with m in their names for module

The entire ecosystem is named etzee, inspired by the dot-dash pattern of Morse code reflected in the design of its magnetic pogo pin connectors used for data and power transfer. Communication between modules is standardized through the htoyto protocol (hello to you too), ensuring consistent interoperability across all components.

In the top view of any device, the right side always acts as the sender, and the left side always acts as the receiver, allowing modules to form a node chain that communicates like a bus. When a new module joins the bus, the system automatically triggers node enumeration, effectively performing dynamic node discovery and registration. The same process applies when a node is removed from the chain.

## Contribute

etzee is an open project for everyone who believe input devices can be more expressive. Join the experiment, build, modify, and extend the ecosystem in your own way.

Join the dicscusson on [Discord](https://discord.gg/uvSp9QrE)

## etzee b11

Traits:

- Monolith or split
- Bluetooth
- Hotswappable
- South facing LEDs
- Modular
- Programable
- Open source
- Sound producing
- Haptic enabled
- Slim and full thickness
- Battary powered
- Integrated dot matrix display
- ZMK support
- Magnetic connectors
- 5 or 6 columns per half

## etzee m0

Traits:

- USB C
- Haptic feedback dial
- Touch screen 240x240 round LCD

## etzee m9

Traits:

- USB C
- 3x3 mechanical keypad
- South facing LEDs
- LCD screen
