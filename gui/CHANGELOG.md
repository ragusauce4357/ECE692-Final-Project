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

GUI stuff. Test it out for yourself by pulling from the branch and running **python gui.py --test**. 

## 48abe6b

### Added
- Blue checkmark for the check boxes on the protocol decode panel. Before a solid blue box was what appeared. I added a checkmark.png to the src for this
### Changed
- Instead of labels being resized and waveforms not, both waveforms and labels can’t be resized so the waveforms stay vertically aligned with their labels
- Scroll bar for the waveforms will always appear now if there isn’t enough space to fit everything. Before it wouldn’t always appear when it should've
- The connection panel and protocol decode panel are now tabbed in the bottom right corner rather than being separated by a splitter. Since they both occupy a small part of the screen, them using a splitter led to difficulty changing stuff in the protocol decode panel as resizing would exclusively shrink that panel and not the connections panel. Doing this required importing QTabWidget
- Resizing the different panels now appears visually as you drag the border and is not clunky like before


## 2f5993b

### Added 
- We have a functional GUI display that looks like a bootleg version of a real logic analyzer so far. 
- Compared to the initial version (not the previous commit), I added these things below. 
- Color-coded measurement pairs: each Δt measurement gets a unique color (cycles through yellow, cyan, pink, green, orange, purple, mint, red) so multiple measurements are easy to tell apart
- "Reset last marker" button so that it'll remove only the most recently placed measurement pair, without wiping everything. 
- Scroll area inside the settings panel so you can scroll through all controls without needing to drag the splitter to expand the bottom section
- Memory depth combo (Mem depth) is now functional: controls how many samples are kept in the logic buffer (5 ms to 500 ms). Previously it existed in the UI but had no effect

### Changed

- Simplified the measurement display: the horizontal dashed line and Δt/freq label now only appear once in the middle channel row (at the vertical midpoint), instead of repeating across every channel row. Label sits directly on top of the dashed line. Arnav and Will saw how bad it looked lol. 
- "Clear measurements" button renamed to "Clear all measurements" to distinguish it from the new reset-last button
- Renamed the decoder.py to packets.py (contains constants and packet parsing only -- no software decoders since Go handles UART/SPI/I2C)

### TO-DOs
- The display works but the bottom section expanding is super clunky and it's difficult to have to expand it each time to change a configuration, such as having to clear the measurements or changing the sample rate. So it's probably better to put some of those up top and also make the bottom section's expansion continuous rather than state based. This is kind of hard to explain over text, but I can show it in person. 
- We still have to work on building an artificial CAN waveform based on the times and data we receive from the CAN decoded frames. 
- A lot of finishing touches left on the GUI side to make it look good. But it matters more to get the system to work than for it to look attractive. 


## 5dc61cd

### Added

- Initial Python GUI using PyQt5 and pyqtgraph with 8-channel digital waveform display
- Working on software decoders for UART, SPI, and I2C: decoded bytes shown as hex annotations on the waveform. CAN is decoded by STM32 bxCAN hardware and displayed in a separate frame log table
- Working on crosshair cursor and time measurement tool (click two points to show Δt and frequency)
- We need TCP receiver thread to connect to Go decoder socket and parse incoming packets
- Added a test mode (`--test`) with simulated UART, SPI, I2C, and CAN packets for development without hardware
- Added Save/load capture sessions to `.json`
- Split into 4 modules: `gui.py`, `decoder.py`, `transport.py`, `display.py`
- `config.json`, `requirements.txt`



