# Changelog for GUI / Visualization

Put all GUI and visualization notes/changelog stuff here. Format adopted from [keepachangelog.com](https://keepachangelog.com).

```
## <date, or commit hash>

<notes>

### Added

### Changed

### Removed
```

---

## [Pending]: 2026-04-20

### Added

- Initial Python GUI using PyQt5 and pyqtgraph with 8-channel digital waveform display
- Working on software decoders for UART, SPI, and I2C: decoded bytes shown as hex annotations on the waveform. CAN is decoded by STM32 bxCAN hardware and displayed in a separate frame log table
- Working on crosshair cursor and time measurement tool (click two points to show Δt and frequency)
- We need TCP receiver thread to connect to Go decoder socket and parse incoming packets
- Added a test mode (`--test`) with simulated UART, SPI, I2C, and CAN packets for development without hardware
- Added Save/load capture sessions to `.json`
- Split into 4 modules: `gui.py`, `decoder.py`, `transport.py`, `display.py`
- `config.json`, `requirements.txt`



