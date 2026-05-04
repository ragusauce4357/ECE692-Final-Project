package serial

import (
	"fmt"
	"log"
	"net" //built in net package for TCP we'll use later
	"time"

	"github.com/ragusauce4357/ECE692-Final-Project/SignalDecoder/internal/config"
	"github.com/ragusauce4357/ECE692-Final-Project/SignalDecoder/internal/decoder"
	"github.com/ragusauce4357/ECE692-Final-Project/SignalDecoder/internal/logging"
	bugst "go.bug.st/serial"
)

const (
	LOGIC_H1          = 0xAA //first header byte
	LOGIC_H2          = 0xBB //second header byte
	CAN_H1            = 0xCC //first CAN header byte
	CAN_H2            = 0xDD //second CAN header byte
	SAMPLE_COUNT      = 512  //# of samples
	LOGIC_PACKET_SIZE = 516  //2 headers + 1 seq + 512 samples + 1 checksum

)

// This is the parsed logic packet with 512 samples raw
// We also have the sequence # for dropped packet detection
type LogicPacket struct {
	Seq     uint8
	Samples [SAMPLE_COUNT]byte
}

// This just holds what bxCAN already decoded for us on the STM
type CANPacket struct {
	Seq  uint8
	ID   uint16
	DLC  uint8
	Data []byte
}

/*
type Packet struct {
	ByteArray byte
	Length    uint
}
*/

// This is the original ReadByteStream we already had, but a few things added on top
// - sync on 0xAABB / 0xCCDD headers instead of fixed 128B chunks
// - stop when the done channel is closed (duration expired)
// - send raw validated byte slices along rawChan for further parsing

// Reads com port specified in Config struct for 128 bytes,
// and forwards the data along a go-channel called packetChan.
func ReadByteStream(cfg *config.Config, rawChan chan<- []byte, errorChan chan<- error, done <-chan struct{}) {
	preamble := "[ReadByteStream]: "

	// Configure the Port
	mode := &bugst.Mode{
		BaudRate: 115200, // we can use 9600 for the python virtual com TESTING ONLY!!!
		DataBits: 8,
		Parity:   bugst.NoParity,
		StopBits: bugst.OneStopBit,
	}

	port, err := bugst.Open(cfg.Port, mode)
	if err != nil {
		errorChan <- fmt.Errorf(logging.ErrLog(preamble)+"Failed to open port %s: %v", cfg.Port, err)
		return
	}
	log.Println(logging.StatLog(preamble) + "Opened port.")
	defer port.Close()

	// This prevents the goroutine from blocking indefinitely
	port.SetReadTimeout(time.Millisecond * 500)

	// Flush any bytes that arrived b4 we opened the port
	// prevents startup misalignment from
	if err := port.ResetInputBuffer(); err != nil {
		log.Println(logging.ErrLog(preamble) + "Failed to reset input buffer, proceeding anyway.")
	}
	log.Printf(logging.StatLog(preamble)+"Started streaming from %s...", cfg.Port)

	readBuf := make([]byte, 1024) //a large read buffer to capture 1024 bytes at a time
	var pending []byte

	//log.Printf(logging.StatLog(preamble)+"Started streaming from %s...", cfg.Port)

	for {
		select {
		case <-done:
			log.Println(logging.StatLog(preamble) + "Done signal received. Stopping.")
			return
		default:
		}
		n, err := port.Read(readBuf) // returns n bytes it actually read and any error
		if err != nil {
			errorChan <- err
			continue
		}
		if n == 0 {
			continue
		}

		// append the new bytes to any leftover from prev iteration
		// The ... slices it into bytes bc Go cant add a whole array to a few bytes
		pending = append(pending, readBuf[:n]...)

		for len(pending) >= 2 {
			if pending[0] == LOGIC_H1 && pending[1] == LOGIC_H2 {
				if len(pending) < LOGIC_PACKET_SIZE {
					break
				}

				raw := make([]byte, LOGIC_PACKET_SIZE)
				copy(raw, pending[:LOGIC_PACKET_SIZE])
				rawChan <- raw
				pending = pending[LOGIC_PACKET_SIZE:]
			} else if pending[0] == CAN_H1 && pending[1] == CAN_H2 {
				if len(pending) < 6 {
					break
				}
				dlc := pending[5]
				if dlc > 8 {
					log.Printf(logging.ErrLog(preamble)+"Invalid DLC: %d, skipping byte\n", dlc)
					pending = pending[2:] //skip 0xCC and 0xDD if its invalid
					continue
				}

				// technically 6 (2 header + 1 seq +  2 ID + 1 DLC) + 1 (checksum) + dlc
				canSize := 7 + int(dlc)
				if len(pending) < canSize {
					break
				}
				raw := make([]byte, canSize)
				copy(raw, pending[:canSize])
				rawChan <- raw
				pending = pending[canSize:]

			} else {
				pending = pending[1:]
			}
		}

	}
}

// this basically XORs all bytes and compares them with expected checksum byte
func validateChecksum(data []byte, expected byte) bool {
	//Note: Make sure to ignore the 0xAA and 0xBB when passing into data!!
	var xor byte = 0
	for _, b := range data {
		xor ^= b
	}
	return xor == expected
}

// this parses a raw 516-byte slice into a LogicPacket struct that I defined earleir
func parseLogicPacket(raw []byte) (*LogicPacket, error) {
	preamble := "[parseLogicPacket]: "

	//raw format: [0xAA][0xBB][seq][512 samples][checksum]
	if !validateChecksum(raw[0:515], raw[515]) {
		return nil, fmt.Errorf(logging.ErrLog(preamble) + "Checksum mismatch, dropping packet")
	}

	packet := &LogicPacket{
		Seq: raw[2],
	}
	copy(packet.Samples[:], raw[3:515]) //copies the sample elements into the packet

	log.Printf(logging.StatLog(preamble)+"Logic packet seq=%d\n", packet.Seq)
	return packet, nil
}

// this parses a raw CAN packet byte slice into a CANPacket struct
func parseCANPacket(raw []byte) (*CANPacket, error) {
	preamble := "[parseCANPacket]: "

	// raw: [0xCC][0xDD][seq][CAN_IDH][CAN_IDL][DLC][0-8 data bytes][checksum]
	dlc := raw[5]
	dataEnd := 6 + int(dlc)
	if !validateChecksum(raw[0:dataEnd], raw[dataEnd]) {
		return nil, fmt.Errorf(logging.ErrLog(preamble) + "Checksum mismatch, dropping packet")
	}
	packet := &CANPacket{
		Seq:  raw[2],
		ID:   uint16(raw[3])<<8 | uint16(raw[4]),
		DLC:  dlc,
		Data: raw[6:dataEnd],
	}

	log.Printf(logging.StatLog(preamble)+"CAN packet seq=%d ID=0x%X DLC=%d\n", packet.Seq, packet.ID, packet.DLC)
	return packet, nil

}

//Start ReadByteStream as a Go Routine.
// Consume the raw packets from rawChan, parses and validates them, route
// the logic packets to protocol decoders and CAN packets to Python straight over TCP.
// Stop it right after cfg.Duration (in ms)

func Run(cfg *config.Config, tcpConnection net.Conn) error {
	preamble := "[Run]: "

	rawChan := make(chan []byte, 20)
	errorChan := make(chan error, 20)
	done := make(chan struct{})

	go ReadByteStream(cfg, rawChan, errorChan, done)

	timer := time.AfterFunc(time.Duration(cfg.Duration)*time.Millisecond, func() {
		close(done)
	})
	defer timer.Stop()

	log.Printf(logging.StatLog(preamble)+"Running for %.0f ms\n", cfg.Duration)

	var lastLogicSeq uint8
	var lastCANSeq uint8
	firstLogic := true
	firstCAN := true

	for {
		select {
		case raw := <-rawChan:
			if len(raw) < 2 {
				continue
			}
			switch raw[0] {
			case LOGIC_H1:
				packet, err := parseLogicPacket(raw)
				if err != nil {
					log.Println(logging.ErrLog(preamble) + err.Error())
					continue
				}

				//track sequence
				if firstLogic {
					firstLogic = false
				} else if packet.Seq != lastLogicSeq+1 {
					log.Printf(logging.ErrLog(preamble)+"Logic: dropped %d packet(s) between seq %d and %d\n",
						int((int(packet.Seq)-int(lastLogicSeq)-1+256)%256), lastLogicSeq, packet.Seq)
				}
				lastLogicSeq = packet.Seq

				//Still TODO: Call decoder based on config.Protocol
				// like results := decoder.DecodeUART(packet.Samples[:], config.Pins)
				// then send results to python over TCP
				switch cfg.Protocol {
				case config.SPI:
					results := decoder.DecodeSPI(packet.Samples[:], cfg.Pins, 0)
					for _, transfer := range results {
						log.Printf(logging.StatLog(preamble)+"SPI transfer t=%.0fus MOSI=0x%02X MISO=0x%02X err=%v\n",
							transfer.Timestamp, transfer.MOSI, transfer.MISO, transfer.Error)
					}

				case config.UART:
					results := decoder.DecodeUART(packet.Samples[:], cfg)
					for _, transfer := range results.TX {
						log.Printf(logging.StatLog(preamble)+"UART transfer over tx: t=%.0fus TX=0x%02X",
							transfer.Timestamp, transfer.Data)
					}
				case config.I2C:
					offset := float64(packet.Seq) * 512.0
					results := decoder.DecodeI2C(packet.Samples[:], cfg.Pins, offset)
					for _, transfer := range results {
						log.Printf(logging.StatLog(preamble)+"I2C addr=0x%02X rw=%v data=%X acks=%v err=%v t=%.0fus\n",
							transfer.Addr, transfer.RW, transfer.Data, transfer.ACKs, transfer.Error, transfer.Timestamp)
					}
				default:
					log.Println("Protocol not found: " + string(cfg.Protocol))
				}

			case CAN_H1:
				packet, err := parseCANPacket(raw)
				if err != nil {
					log.Println(logging.ErrLog(preamble) + err.Error())
					continue
				}
				// sequence tracking
				if firstCAN {
					firstCAN = false
				} else if packet.Seq != lastCANSeq+1 {
					log.Printf(logging.ErrLog(preamble)+"CAN: dropped %d packet(s) between seq %d and %d\n",
						int((int(packet.Seq)-int(lastCANSeq)-1+256)%256), lastCANSeq, packet.Seq)
				}
				lastCANSeq = packet.Seq

				// forward CAN packet to Python over TCP
				fmt.Fprintf(tcpConnection, "CAN seq=%d id=0x%X dlc=%d data=%X\n",
					packet.Seq, packet.ID, packet.DLC, packet.Data)
			}
		case err := <-errorChan:
			log.Println(logging.ErrLog(preamble) + err.Error())

		case <-done:
			log.Println(logging.StatLog(preamble) + "Capture complete.")
			return nil
		}
	}

}

// **This is claude generated**
// DummyConn is a fake net.Conn for testing without Python.
// It discards all writes and returns empty reads.
type DummyConn struct{}

func NewDummyConn() (net.Conn, error) {
	return &DummyConn{}, nil
}

func (d *DummyConn) Write(b []byte) (n int, err error)  { return len(b), nil }
func (d *DummyConn) Read(b []byte) (n int, err error)   { return 0, nil }
func (d *DummyConn) Close() error                       { return nil }
func (d *DummyConn) LocalAddr() net.Addr                { return nil }
func (d *DummyConn) RemoteAddr() net.Addr               { return nil }
func (d *DummyConn) SetDeadline(t time.Time) error      { return nil }
func (d *DummyConn) SetReadDeadline(t time.Time) error  { return nil }
func (d *DummyConn) SetWriteDeadline(t time.Time) error { return nil }

/*
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

		fmt.Printf(logging.StatLog(preamble)+"--- [Packet #%d] ---\n", packetCount)

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
*/
