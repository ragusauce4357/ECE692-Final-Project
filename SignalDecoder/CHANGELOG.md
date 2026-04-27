# Changelog for SignalDecoder

Put all SignalDecoder notes/changelog stuff here. Format adopted from [keepachangelog.com](https://keepachangelog.com).

```
## <date, or commit hash>

<notes>

### Added

### Changed

### Removed

## <older date/hash>
```

## 53628d3

### Added

- All commit stuff from before included
- Added the initial code to get the CLI argument parsing and program configuration working.
- Added code for the `internal/serial` package, but it isn't reading the data off of the test python script just yet.
    - The Python script works. Running the `socat` script on ports `/dev/ttyUSB0` and `/dev/ttyUSB1` works, python script connects to the first port successfully, and `screen /dev/ttyUSB1 9600` successfully prints the random stuff onto the screen.
    - In the serial package code, I've added a logging print line which seemingly does not print. I do not know entirely why, but I'm assuming it is because of an overlooked portion of how goroutines function. 
- Once the serial code is complete, next comes the decoding, in `internal/decoder/<protocol name>`.
