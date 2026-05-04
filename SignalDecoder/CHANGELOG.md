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

## 10a24d3

### Added

- Added [internal/decoder/uart.go][10a24d3-01], which decodes UART signals.
- It can be tested using the test python script [test.py][10a24d3-02]
    - To run the test python script you must be on linux. First open a terminal and install socat. Then run smth like `sudo bash socat.sh /dev/ttyUSB0 /dev/ttyUSB1`
    - In another terminal, make a venv and pip install the requirements.txt file.
    - Then, run the test.py file and when prompted, enter `/dev/ttyUSB0`, along with a TX channel of ur choosing (there was a mistake in the code at this part, but was fixed in a later commit by Raghav, details below)
    - Finally navigate to wherever the SignalDecoder binary is, and run (replace tx pin w/ ur chosen tx pin):

```bash
./SignalDecoder -port /dev/ttyUSB1 -duration 5000 -protocol uart -pins tx1rx2 -sr 1000000
```
- *NOTE:* There was a mistake in the go code for the [uart decoder][10a24d3-01] on line 37 and 38. I had made the txPin variable just `uint8(cfg.Pins >> 12)`, but in the case of the pin not being in the form of $2^n$ (such as 3 or 5), the pin number is no longer its own mask (which worked for pins 1, 2, 4 etc purely coincidentally :skull:). Raghav fixed this in [commit 626f507][10a24d3-03] with the proper mask using bitshifts.

### Changed

- Modified serial.go slightly to account for the uart decoder.

<!-- Links for 10a24d3 -->

[10a24d3-01]: https://github.com/ragusauce4357/ECE692-Final-Project/blob/10a24d39958ca57625ff5bdbd0d67016dab30254/SignalDecoder/internal/decoder/uart.go
[10a24d3-02]: https://github.com/ragusauce4357/ECE692-Final-Project/blob/10a24d39958ca57625ff5bdbd0d67016dab30254/SignalDecoder/test/test.py
[10a24d3-03]: https://github.com/ragusauce4357/ECE692-Final-Project/blob/626f507ff57ffe92b840a3199ed55d379f2f0023/SignalDecoder/internal/decoder/uart.go

## 78fd5ad
- fixed the sequence tracking. Before it was tracking both the CAN and UART/SPI/I2C with the same sequence number, which caused dropped packet issues since seq numbers were being skipped CAN individually. Now added logic_seq and can_seq. 
- Also fixed the sequence drop calculation overflow. B4 it was going from 255 -> 1 but saying the differnece is -255, but now it correctly says the difference and is 255 -> 0. No longer false drops. 
- fixed the windows line endings in socat for WSL compatibility. 

Here's the transmitted packets from /tmp/ttyV0 - Virtual COM Port 0
[*] Sent CAN packet seq=0 id=0x123 (15 bytes)
[*] Sent logic packet seq=1 (516 bytes)
[*] Sent CAN packet seq=1 id=0x123 (15 bytes)
[*] Sent logic packet seq=2 (516 bytes)
[*] Sent CAN packet seq=2 id=0x123 (15 bytes)
[*] Sent logic packet seq=3 (516 bytes)

Here's the received packets from /tmp/ttyV1 - Virtual COM Port 1
2026/04/27 22:18:22 [parseLogicPacket]: Logic packet seq=27
2026/04/27 22:18:22 [parseCANPacket]: CAN packet seq=27 ID=0x123 DLC=8
2026/04/27 22:18:22 [parseLogicPacket]: Logic packet seq=28
2026/04/27 22:18:22 [parseCANPacket]: CAN packet seq=28 ID=0x123 DLC=8
2026/04/27 22:18:22 [parseLogicPacket]: Logic packet seq=29
2026/04/27 22:18:22 [parseCANPacket]: CAN packet seq=29 ID=0x123 DLC=8
2026/04/27 22:18:22 [parseLogicPacket]: Logic packet seq=30

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
