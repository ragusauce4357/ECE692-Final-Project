# Dev Notes

## Status

| Feature | Status |
|---------|--------|
| 8-channel waveform display | Done |
| UART software decoder | Done |
| SPI software decoder | Done |
| I2C software decoder | Done |
| CAN frame log (from STM32 bxCAN) | Done |
| Crosshair cursor | Done |
| Time measurement tool | Done |
| Save / load captures | Done |
| Status indicator (READY/RUNNING/STOPPED) | Done |
| Test mode (simulated packets) | Done |
| TCP receiver (live mode) | Done |
| config.json integration | TODO |
| Trigger (software edge detect) | TODO |
| Position scrub slider | TODO |
| Go subprocess launch from GUI | TODO |

## Known Issues / TODOs

- `config.json` is created but it's not yet loaded at startup. We need to wire it into `gui.py` and `display.py` when it comes time.
- Simulated I2C uses bit5 for SCL instead of bit8 to avoid uint8 overflow — real hardware uses PC8 (bit8 of IDR), so the real decoder uses `scl_ch=7` which maps to bit8 correctly via `extract_ch()`
- UART decode only handles TX (CH1) right now — RX (CH2) can be added trivially

## Interface Contract with Go (avr34)

On Go, we need to implement a TCP socket server that:
1. Listens on a configurable port (default 5000)
2. Reads raw packets from the STM32 over the COM port
3. Forwards them as-is over the TCP socket to Python

Python handles all protocol decoding (UART/SPI/I2C) from raw samples.
CAN frames arrive pre-decoded from STM32 bxCAN, so the Go file would just forward the `0xCC 0xDD` packets.

Go CLI args (already implemented in SignalDecoder):
```
--port COM3 --duration 5000 --protocol uart --pins tx1rx2
```

## Packet Format Reference

Logic: `[0xAA][0xBB][seq 1B][512 raw bytes][XOR checksum]` = 516 bytes total
CAN:   `[0xCC][0xDD][seq 1B][ID_H][ID_L][DLC][0-8 data bytes][XOR checksum]`