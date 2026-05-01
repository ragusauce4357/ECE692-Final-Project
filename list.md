# List of stuff to buy

> [!NOTE]
> This is a preliminary list, from Claude. We need to review everything, and update the list accordingly.
> Aim to order soon since digikey takes like a week to arrive after ordering.

## Core board:

1x Nucleo-F446RE

Level shifting:

1x TXS0108E (8 channel, general purpose)

## CAN bus:

1x SN65HVD230 CAN transceiver (3.3V compatible, works directly with F446RE)

Input protection (per channel, 8 channels):

8x 1kΩ resistors (series protection)
8x BAT54 Schottky diodes (clamping)

## I2C pull-ups:

2x 4.7kΩ resistors (SDA and SCL to 3.3V)

## Decoupling capacitors:

4x 100nF ceramic capacitors (one per IC: TXS0108E, PCA9306, SN65HVD230, and general power)
2x 10µF electrolytic capacitors (bulk decoupling on 3.3V and 5V rails)

## Connectors:

1x 2.54mm pitch pin header strip (probe inputs, at least 10 pins — 8 channels + 2 ground)
2x Arduino female header strips (to plug onto Nucleo)
1x 2-pin screw terminal or header for CANH/CANL

## PCB:

5x custom breakout PCB from JLCPCB (~$5 for 5)

## Enclosure:

(we can print these at the makerspace)

PLA or PETG filament (printed box ~70mm × 130mm footprint)
4x M3 brass heat-set inserts
4x M3x8mm screws (for lid)

## Testing:

1x Arduino Uno or spare STM32 Nucleo (signal generator for testing your decoders)
Jumper wires / grabber clips for probing

## Software (free):

STM32CubeIDE
STM32CubeMX
Python + pyserial + pyqtgraph
KiCad (PCB design)

## Order priority:

Nucleo-F446RE immediately — from DigiKey or Mouser
ICs and passives — DigiKey/Mouser, arrive in a few days
PCB — once KiCad design is done, order from JLCPCB, ~1.5 week lead time
Filament — only if nobody on team has it already
