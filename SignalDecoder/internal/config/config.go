package config

import (
	"errors"
	"flag"
	"log"
	"slices"
	"strings"

	"github.com/ragusauce4357/ECE692-Final-Project/SignalDecoder/internal/logging"
	"go.bug.st/serial"
	bugst "go.bug.st/serial"
)

// For the constants, mapping protocol to a uint8.
type ProtocolType uint8

// Each pair of four bits maps to a channel, from LSB to MSB.
// There are 4 groups of 4 bits, which corresponds
// to the pins of that protocol. For each protocol:
//   - UART: tx=1,   rx=2
//   - SPI:  miso=1, mosi=2, clk=3, cs=4
//   - I2C:  sda=1,  scl=2
//   - CAN:  canh=1, canl=2
//
// Unused values are set to 0.
//
// For example: SPI with respective pins on channels 4, 3, 5, 1:
// ```
//   - 0b0100,0011,0101,0001
//     4    3    5    1
//   - 0x4351
//
// ```
//
// Order matters! So if cli argument is --port scl7sda1, the
// correct order is sda then scl, so the ProtocolPins would be
// ```
//   - 0b0001,0111,0000,0000
//     1    7    0    0
//   - 0x1700
//
// ```
//
// It is used internally only. Not exported to python script.
type ProtocolPins uint16

// Maps a protocol to an int
const (
	NONE ProtocolType = iota
	UART
	SPI
	I2C
	//CAN
)

// Config struct, specifies which port, duration, which protocol
// to decode (if any), and if so, which channels to use.
type Config struct {
	Port     string
	Duration float64
	SampleRate uint
	Protocol ProtocolType
	Pins     ProtocolPins
	Baud     uint
}

// Performs a logical xor of two bools.
// Funny how the language has no native support
// for this.
func xor(A, B bool) bool {
	return (!A && B) || (A && !B)
}

// Initializes all the flags, parses the flags, checks for
// invalidities, and if nothing's invalid, returns a pointer
// to a config struct.
//
// If there IS an error, it returns an error. It will not
// halt the program.
func GetConfig() (*Config, error) {
	preamble := "[GetConfig]: "

	var ret Config
	var err error

	port := flag.String("port", "", "Port at which to read data from the Logic Analyzer.")
	pins := flag.String("pins", "", "(Optional) Channels to use to perform protocol decoding.")
	duration := flag.Float64("duration", float64(0x0), "Duration (in ms) to run signal capture.")
	sampleRate := flag.Uint("sr", 0, "Sample rate (number of samples per second). Must be provided.")
	protocol := flag.String("protocol", "", "(Optional) Protocol to decode.")
	baudd := flag.Uint("baud", 0, "Baud rate. Use if decoding uart.")
	list := flag.Bool("list", false, "List available ports")

	flag.Parse()

	if *list {
		printPorts()
		return nil, errors.New(logging.ErrLog(preamble) + "Listed available ports.")
	}

	log.Print(logging.StatLog(preamble) + "Parsing arguments...")

	// Handle invalid inputs.
	if *port == "" {
		return nil, errors.New(logging.ErrLog(preamble) + "Must specify a port.")
	} else {
		ret.Port = *port
	}

	if *sampleRate == 0 {
		return nil, errors.New(logging.ErrLog(preamble) + "Must specify the logic analyzer's sample rate, as an integer.")
	} else {
		ret.SampleRate = *sampleRate
	}

	if *duration <= 0.0 {
		return nil, errors.New(logging.ErrLog(preamble) + "Must specify a (positive) duration.")
	} else {
		ret.Duration = float64(*duration)
	}

	// why doesn't this language have logical xor!
	// basically, one cannot exist w/o the other.
	if xor(*protocol == "", *pins == "") {
		return nil, errors.New(logging.ErrLog(preamble) + "Cannot use protocol without pin declaration and vice versa.")
	}

	// Check if port exists.
	ports, err := bugst.GetPortsList()

	if err != nil {
		return nil, errors.New(logging.ErrLog(preamble) + "Issues opening serial port")
	}

	if len(ports) == 0 {
		log.Println(logging.StatLog(preamble) + "No serial ports found via enumeration, proceeding anyway.")
	} else {
		if exists := slices.Contains(ports, *port); !exists {
			log.Printf(logging.StatLog(preamble)+"Port %s not found in enumeration, proceeding anyway.\n", *port)
		}
	}

	switch strings.ToUpper(*protocol) {
	case "":
		ret.Protocol = NONE
	case "UART":
		ret.Protocol = UART
		ret.Baud = *baudd
		if *baudd <= 0 {
			return nil, errors.New(logging.ErrLog(preamble) + "Must specify baud rate if decoding uart.")
		}
	case "SPI":
		ret.Protocol = SPI
	case "I2C":
		ret.Protocol = I2C

	// Commenting out CAN here since it's decoded in bxCAN now.
	// We can always revert if need be.
	/*
		case "CAN":
		 	ret.Protocol = CAN
	*/
	default:
		return nil, errors.New(logging.ErrLog(preamble) + "Unrecognized comm protocol.")
	}

	ret.Pins, err = parsePins(ret.Protocol, *pins)
	if err != nil {
		return nil, err
	}

	log.Print(logging.StatLog(preamble) + "CLI argument error checking complete.")

	return &ret, nil
}

// Call individual parsing function based on the protocol
func parsePins(p ProtocolType, pins string) (ProtocolPins, error) {
	preamble := "[parsePins]: "

	log.Print(logging.StatLog(preamble) + "Parsing pins argument...")
	switch p {
	case UART:
		ret, err := parseUART(pins)
		if err != nil {
			return 0, err
		} else {
			return ret, nil
		}
	case SPI:
		ret, err := parseSPI(pins)
		if err != nil {
			return 0, err
		} else {
			return ret, nil
		}
	case I2C:
		ret, err := parseI2C(pins)
		if err != nil {
			return 0, err
		} else {
			return ret, nil
		}
	// Commenting out CAN here since it's decoded in bxCAN now.
	// We can always revert if need be.
	/*
		case CAN:
			ret, err := parseCAN(pins)
			if err != nil {
				return 0, err
			} else {
				return ret, nil
			}
	*/
	case NONE:
		log.Print(logging.StatLog(preamble) + "No pin configuration provided. Proceeding.")
		return 0, nil
	default:
		return 0, errors.New(logging.ErrLog(preamble) + "Unknown protocol referenced.")
	}

	log.Print(logging.StatLog(preamble) + "Pin parsing complete.")

	return 0, nil
}

// Print a configuration. For debugging purposes.
func (a *Config) Print() {
	preamble := "[print] "

	log.Printf(logging.StatLog(preamble) + "Current configuration:\n")
	log.Printf(logging.StatLog(preamble)+"  Port:        %s\n", a.Port)
	log.Printf(logging.StatLog(preamble)+"  Duration:    %f\n", a.Duration)
	log.Printf(logging.StatLog(preamble)+"  Sample Rate: 0x%X\n", a.SampleRate)
	log.Printf(logging.StatLog(preamble)+"  Protocol:    %d\n", a.Protocol)
	log.Printf(logging.StatLog(preamble)+"  Pins:        0x%X\n", a.Pins)
}

func printPorts() {
	preamble := "[printPorts]: "

	ports, err := serial.GetPortsList()
	if err != nil {
		log.Fatal(err)
	}

	if len(ports) == 0 {
		log.Printf(logging.ErrLog(preamble) + "No serial ports found!")
	} else {
		for _, port := range ports {
			log.Printf(logging.StatLog(preamble)+"Found port: %v\n", port)
		}
	}
}
