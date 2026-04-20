# Logic Analyzer — Python GUI

This is the Python visualization frontend. It connects to the [Go signal decoder](https://github.com/ragusauce4357/ECE692-Final-Project/tree/feature/SignalDecoder) via TCP socket and renders 8-channel digital waveforms with UART, SPI, I2C, and CAN protocol decode overlays.

Just some initial work. We'll have stuff to work on for later.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Test mode — simulated packets, no hardware needed
python gui.py --test

# Live mode — connects to Go decoder over TCP
python gui.py
```

## File Structure

| File | Description |
|------|-------------|
| `gui.py` | Entry point and main window |
| `decoder.py` | Constants, packet parsing, UART/SPI/I2C decoders |
| `transport.py` | TCP receiver, packet simulator, save/load |
| `display.py` | Waveform widget, CAN table, UI panels |
| `config.json` | User-editable runtime configuration |

## Configuration

We can edit the `config.json` file to set our default COM port, TCP host/port, baud rate, and which channels map to which protocol signals. Settings are loaded at startup and can also be changed from the UI.



## Packet Format

This ties back into the STM32 Firmware. The CAN bus has a header that's different than the logic headers (for UART, SPI, I2C) just for clarity. 
| Packet | Header | Seq | Payload | Checksum |
|--------|--------|-----|---------|----------|
| Logic  | `0xAA 0xBB` | 1B | 512 raw GPIO samples | XOR |
| CAN    | `0xCC 0xDD` | 1B | ID(2B) + DLC(1B) + data(0-8B) | XOR |

## Channel Map

This is pretty configurable, but here's a layout we can use. 

| Channel | Pin | Signal |
|---------|-----|--------|
| CH1 | PC1 | UART TX |
| CH2 | PC2 | UART RX |
| CH3 | PC3 | SPI CLK |
| CH4 | PC4 | SPI MOSI |
| CH5 | PC5 | SPI MISO |
| CH6 | PC6 | SPI CS |
| CH7 | PC7 | I2C SDA |
| CH8 | PC8 | I2C SCL |