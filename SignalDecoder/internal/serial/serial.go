package serial

import (
	"fmt"
	"log"
	"time"

	bugst "go.bug.st/serial"

	"github.com/ragusauce4357/ECE692-Final-Project/SignalDecoder/internal/config"
	"github.com/ragusauce4357/ECE692-Final-Project/SignalDecoder/internal/logging"
)

type Packet struct {
	ByteArray byte
	Length    uint
}

// Reads com port specified in Config struct for 128 bytes,
// and forwards the data along a go-channel called packetChan.
func ReadByteStream(config *config.Config, packetChan chan<- [128]byte, errorChan chan<- error) {
	preamble := "[ReadByteStream]: "

	// Configure the Port
	mode := &bugst.Mode{
		BaudRate: 9600, // Matches the python virtual com TESTING ONLY!!!
		DataBits: 8,
		Parity:   bugst.NoParity,
		StopBits: bugst.OneStopBit,
	}

	port, err := bugst.Open(config.Port, mode)
	if err != nil {
		errorChan <- fmt.Errorf(logging.ErrLog(preamble) + "Failed to open port %s: %v", config.Port, err)
	}
	log.Println(logging.StatLog(preamble) + "Opened port.")
	defer port.Close()

	// This prevents the goroutine from blocking indefinitely
	port.SetReadTimeout(time.Millisecond * 500)

	buffer := make([]byte, 128)
	bytesReadTotal := 0

	log.Printf(logging.StatLog(preamble) + "Started streaming from %s...", config.Port)

	for {
		n, err := port.Read(buffer[bytesReadTotal:])
		if n > 0 {
			bytesReadTotal += n

			if bytesReadTotal == 128 {
				var packet [128]byte
				copy(packet[:], buffer)
				packetChan <- packet
				bytesReadTotal = 0
			}
		}

		if err != nil {
			errorChan <- err
		}
	}
}

// Verifies the reception of bytes on the com port.
// 
// If testing without a microcontroller, use the python script
// in SignalDecoder/testing along with the socat script on 
// a linux device to emulate the LogicAnalyzer's output.
func VerifyReception(config *config.Config) error {
	preamble := "[VerifyReception]: "

	// Create the channel locally
	// We use a buffer of 20 to handle bursty serial traffic
	packetChan := make(chan [128]byte, 20)

	// Start goroutine and get data from packetChan
	go ReadByteStream(config, packetChan)

	// TODO some bs going on here hmm
	log.Printf(logging.StatLog(preamble) + "Monitoring started. Listening for 128-byte packets...\n")

	// Consume from buffer and print
	packetCount := 0
	for packet := range packetChan {
		packetCount++

		fmt.Printf(logging.StatLog(preamble) + "--- [Packet #%d] ---\n", packetCount)

		// Standard 16-byte hex grid for easy header spotting
		for i, b := range packet {
			fmt.Printf("%02X ", b)
			if (i+1)%16 == 0 {
				fmt.Println()
			}
		}
	}

	fmt.Println(logging.StatLog(preamble) + "Stream terminated.")
}
