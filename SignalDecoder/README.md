# Signal Decoder

This is a signal decoder. Plan is that it'll be runnable as an executable, will monitor the port that you specify, and will decode incoming signals that *follow a certain bit-packed format*.

This project is a smaller part of a larger [Logic Analyzer][01] project that our ECE692 (Embedded Systems @ NJIT) group is doing. We haven't yet decided upon a format, will update this readme when we do.

## Plan

Below is how the flow of data within this application will work:

- Data will come in from the STM via a COM port in a continuous stream.The packets will follow the format `[Header 0xAABB] [Sequence # (0 - 255)] [30 Pairs of [Channel State (1B)] [Duration (1B)]] [Checksum (XOR or all 63 previous bytes)]`. Each of the 30 pairs will follow run length encoding. If the channel state changes, there will be a new point (out of 30). If the channel state doesn't change, the duration is incremented. It keeps getting incremented till it reaches 255, at which point a new data point is forced.
- The Go application will be invoked by the Python GUI (using something like a subprocess), with several command line options, including:
    - Which port to listen on (COM or /dev/tty\*)
    - Duration that the Go program should run for (capture period)
    - (Optional) Which signal decoding should be used (UART, I2C, SPI, or CAN)
    - (Optional) Which pins to use for said decoding. Required if using the signal decoding.
        - For UART: `--pins tx1rx2`
        - For SPI: `--pins miso1mosi2clk3` or `miso1mosi2clk3cs4`
        - For I2C: `--pins sda1scl2`
        - For CAN: `--pins canh1canl2`
        - where the numbers (1, 2, 3, ...) are the channel numbers.
        - For now only decoding one signal at a time.
    - Once the go program has run for the specified amount of time, it will exit by itself, and close the connection on the COM port and the socket.
- Once the program is invoked, it will listen to the port and do the following *if decoding is involved*:
    - Read one 64 byte input frame off the serial port's buffer, and parse it into a custom data format. This may be in `internal/serial/`.
    - The parsed frame should then be sent to a goroutine which handles decoding. That goroutine should be initialized with the correct decoding settings (what protocol and which channels). This may be in `internal/decoder`
    - Finally, the decoded frame (30 datapoints and values) must be sent in two packets (waveform and decoded packets) on a socket to communicate with the Python application.
        - From here, the python application will read the decoded packet, plot the waveform, and place the text (hex bytes, decoded from the signal) onto the waveform at the correct places.

## Proposed Project Structure:

```
logic-analyzer-go/
├── main.go             # Entry point: Orchestrates goroutines and channels
├── internal/
│   ├── serial/         # Handles bugst/go-serial and packet framing
│   ├── decoder/        # RLE expansion and protocol decoding (UART/SPI) 
│   ├── transport/      # Socket server to talk to Python
│   ├── config/         # Holds configuration struct for the entire runtime of the program 
│   └── logging/        # Small logging package, to easily color text either red or green.
├── go.mod
└── go.sum
``` 

<!-- Links -->
[01]: https://github.com/ragusauce4357/ECE692-Final-Project
