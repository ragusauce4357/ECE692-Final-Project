package decoder

import (
	"log"

	"github.com/ragusauce4357/ECE692-Final-Project/SignalDecoder/internal/config"
	"github.com/ragusauce4357/ECE692-Final-Project/SignalDecoder/internal/logging"
)

// Stores a byte decoded from a UART channel, along with the timestamp.
// The timestamp is the time in us, which in go can represent more seconds than
// we could ever need.
type UARTByte struct {
	Data      byte
	Timestamp float64
}

// Struct for decoded uart packets. Stores one complete 516 byte packet
// of data.
type DecodedUARTPacket struct {
	TX []UARTByte
	RX []UARTByte
}

// Function to decode a UART packet, returns a DecodedUARTPacket struct pointer. The function
// expects a 8N1 signal on both lines, and will first do an RLE, then decode as expected.
// It is implemented as a state machine. Find the diagram and a example at docs/uart.md
//
// To be used by serial.Run() to ultimately decode a stream of packets.
func DecodeUART(packet []byte, cfg *config.Config) *DecodedUARTPacket {
	preamble := "[DecodeUART]: "

	log.Println(logging.StatLog(preamble) + "Beginning UART Decoding...")

	// Bit-shift right by 12 to get MSB of pins (TX).
	// Bit-shift right by 8, and AND with 0xF to get 2nd MSB (RX)
	txPin := uint8(cfg.Pins >> 12)
	rxPin := uint8(cfg.Pins>>8) & 0xF

	// Initialize return object and local timestamp. This will effectively implement RLE,
	// since as long as the TX and RX pins stay the same, the timestamp is incremented.
	ret := &DecodedUARTPacket{}

	var localTimestamp float64 = 0
	samplesPerBit := cfg.SampleRate / cfg.Baud
	timePerSample := (1.0 / float64(cfg.SampleRate)) * 1000000

	// State constants
	const (
		IDLE = iota
		START_BIT
		DATA_BITS
		STOP_BIT
	)

	txState := IDLE
	var txCurrentByte byte
	var txByteCount uint8
	var txSampleCounter uint

	rxState := IDLE
	var rxCurrentByte byte
	var rxByteCount uint8
	var rxSampleCounter uint

	halfway := uint(samplesPerBit / 2)

	//masks for tx and rx used to get the high/low of each line
	txMask := uint8(1 << (txPin - 1))
	rxMask := uint8(1 << (rxPin - 1))

	// For loop to iterate through all the samples
	for _, sample := range packet {
		// Get high/low of each line

		txHigh := (sample & txMask) != 0
		rxHigh := (sample & rxMask) != 0

		// Switch case to handle the states, and extracting the bytes.
		// In hindsight, could've probably wrapped this in a function, which
		// could be applied to both TX and RX, but whatever.
		switch txState {
		case IDLE:
			// When the tx pin is pulled low, to signal start of transmission
			if !txHigh {
				txState = START_BIT
				txCurrentByte = 0x00
				txByteCount = 0
				txSampleCounter = 0
			}
		case START_BIT:
			// As long as txSampleCounter is less than samplesPerBit, and TX doesn't become 1, do nothing
			// If txSampleCounter exceeds samplesPerBit, or TX becomes 1, switch to DATA_BITS, and set
			// txSampleCounter to 0.
			if txSampleCounter >= samplesPerBit || txHigh {
				txState = DATA_BITS
				txSampleCounter = 0
			}

			txSampleCounter++
		case DATA_BITS:
			// Capture and shift in the value of TX if txSampleCounter == int(samplesPerBit / 2)
			if txSampleCounter == halfway {
				txCurrentByte >>= 1
				if txHigh {
					txCurrentByte |= 0x80
				}
				txByteCount++
			}

			// If we're at the end of a bit
			if txSampleCounter == samplesPerBit {
				txSampleCounter = 0
			}

			txSampleCounter++

			// Change states if we've captured 8 bits
			if txByteCount == 8 {
				txState = STOP_BIT
				txSampleCounter = 20
			}
		case STOP_BIT:
			// Save byte and timestamp
			if txSampleCounter == 20 {
				ret.TX = append(ret.TX, UARTByte{
					Data:      txCurrentByte,
					Timestamp: localTimestamp,
				})
				txSampleCounter = 0
			}

			if txHigh {
				txState = IDLE
			}
		}

		// literally copy paste the tx version, and replace tx with rx.
		switch rxState {
		case IDLE:
			// When the rx pin is pulled low, to signal start of transmission
			if !rxHigh {
				rxState = START_BIT
				rxCurrentByte = 0x00
				rxByteCount = 0
				rxSampleCounter = 0
			}
		case START_BIT:
			// As long as rxSampleCounter is less than samplesPerBit, and RX doesn't become 1, do nothing
			// If rxSampleCounter exceeds samplesPerBit, or RX becomes 1, switch to DATA_BITS, and set
			// rxSampleCounter to 0.
			if rxSampleCounter >= samplesPerBit || rxHigh {
				rxState = DATA_BITS
				rxSampleCounter = 0
			}

			rxSampleCounter++
		case DATA_BITS:
			// Capture and shift in the value of RX if rxSampleCounter == int(samplesPerBit / 2)
			if rxSampleCounter == halfway {
				rxCurrentByte >>= 1
				if rxHigh {
					rxCurrentByte |= 0x80
				}
				rxByteCount++
			}

			// If we're at the end of a bit
			if rxSampleCounter == samplesPerBit {
				rxSampleCounter = 0
			}

			rxSampleCounter++

			// Change states if we've captured 8 bits
			if rxByteCount == 8 {
				rxState = STOP_BIT
				rxSampleCounter = 20
			}
		case STOP_BIT:
			// Save byte and timestamp
			if rxSampleCounter == 20 {
				ret.RX = append(ret.RX, UARTByte{
					Data:      rxCurrentByte,
					Timestamp: localTimestamp,
				})
				rxSampleCounter = 0
			}

			if rxHigh {
				rxState = IDLE
			}
		}

		localTimestamp += timePerSample
	}

	log.Println(logging.StatLog(preamble) + "UART Decoding complete")

	return ret
}
