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

## d7c4dc7

### Changed
- serial.go: I rewrote the ReadByteStream function to sync on 0xAABB/0xCCDD headers rather than 128-byte chunks - this was Arnav's idea. Added pending buffer for the packet spanning, ResetInputBuffer() when we open a port to flush out existing content, and also the done channel for duration-based stopping, and the Claude-generated DummyConn for testing it without Python. 
- Also added the Run() function which basically routes logic packets over to the eventual decoder that we build and CAN packets just straight to Python over TCP. 
- Added structs for LogicPackets and CANPackets. Also parseLogicPacket and parseCANPacket functions, and sequence drop detection. 
- Changed the bound checks in parse.go from >= 8 to >8, since there are 8 channels. 
- Commented out CAN from protocol switch and pins parsing since the bxCAN handles that. 
- In test.py, changed it a bit to generate correct 516-byte logic packets and variable-length CAN packets matching actual protocol. We actually don't use RLE encoding, even tho it was a great idea, so now it's raw sequential samples at 1MHz/115200 baud.

## ef28400d

### Changed

- **UPDATE:** The version in the last commit works. I'm just dumb and ran `go install` on an older version, and so the path variable was running the old version rather than the new version. The latest code works as expected.

## 53628d3

### Added

- All commit stuff from before included
- Added the initial code to get the CLI argument parsing and program configuration working.
- Added code for the `internal/serial` package, but it isn't reading the data off of the test python script just yet.
    - The Python script works. Running the `socat` script on ports `/dev/ttyUSB0` and `/dev/ttyUSB1` works, python script connects to the first port successfully, and `screen /dev/ttyUSB1 9600` successfully prints the random stuff onto the screen.
    - In the serial package code, I've added a logging print line which seemingly does not print. I do not know entirely why, but I'm assuming it is because of an overlooked portion of how goroutines function. 
- Once the serial code is complete, next comes the decoding, in `internal/decoder/<protocol name>`.
