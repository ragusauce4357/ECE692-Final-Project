package decoder

/*
START: SDA from High to Low while SCL is High
STOP: SDA from Low to High while SCL is High
DATA: SDA is sampled when SCL from Low to High
ACK/NACK: 9th clock pulse, SDA low means ACK, high means NACK
*/

import (
	"github.com/ragusauce4357/ECE692-Final-Project/SignalDecoder/internal/config"
)

type DecodedI2CPacket struct {
	Timestamp float64
	Addr      byte
	RW        bool //write = 0, read = 1 per datasheet
	Data      []byte
	ACKs      []bool //one per byte including address byte
	Error     bool   //NACK on address or incomplete transaction
}

/*
I2C Decoder Algorithm:
1. Wait for START (check above for conditions)
2. Collect 9 bits on each SCL rising edge (8 data/addr bits + 1 ACK bit)
3. First 9 bits = 7-bit addr + R/W bit + ACK
4. After that, 9-bit groups are data bytes + ACK
5. check for STOP
6. Repeated START - if there's another START after the STOP, then it's the next
transaction.
*/

func flushPacket(current DecodedI2CPacket, results []DecodedI2CPacket, withError bool, timestamp float64) (DecodedI2CPacket, []DecodedI2CPacket) {
	current.Error = current.Error || withError
	results = append(results, current)
	return DecodedI2CPacket{Timestamp: timestamp}, results
}

func DecodeI2C(samples []byte, pins config.ProtocolPins, offset float64) []DecodedI2CPacket {

	// pins: scl7sda8
	sdaCH := byte((pins >> 12) & 0xF) // bits [15:12] ← sda
	sclCH := byte((pins >> 8) & 0xF)  // bits [11:8]  ← scl

	sclMask := uint8(1 << (sclCH - 1))
	sdaMask := uint8(1 << (sdaCH - 1))

	// State constants
	const (
		IDLE = iota
		ADDR
		ADDR_ACK
		DATA
		DATA_ACK
	)

	state := IDLE

	var prevSCL, prevSDA byte

	var bitCount int
	var currentByte byte
	var currentPacket DecodedI2CPacket
	var results []DecodedI2CPacket

	for i, sample := range samples {
		scl := (sample & sclMask) >> (sclCH - 1)
		sda := (sample & sdaMask) >> (sdaCH - 1)

		timestamp := offset + float64(i)

		sclRising := prevSCL == 0 && scl == 1
		sdaRising := prevSDA == 0 && sda == 1
		sdaFalling := prevSDA == 1 && sda == 0

		//START Condition: SDA High to Low while SCL is High
		start := sdaFalling && scl == 1

		//STOP Condition: SDA Low to High while SCL is High
		stop := sdaRising && scl == 1

		switch state {
		case IDLE:
			if start {
				currentPacket = DecodedI2CPacket{Timestamp: timestamp}
				bitCount, currentByte = 0, 0
				state = ADDR
			}

		case ADDR:
			if start {
				//repeated START
				currentPacket = DecodedI2CPacket{Timestamp: timestamp}
				bitCount, currentByte = 0, 0
			} else if stop {
				currentPacket, results = flushPacket(currentPacket, results, true, timestamp)
				state = IDLE
			} else if sclRising {
				//shift each bit left and make room for the new SDA bit
				//at the LSB position
				currentByte = (currentByte << 1) | sda
				bitCount++
				if bitCount == 8 {
					currentPacket.Addr = currentByte >> 1
					currentPacket.RW = (currentByte & 0x1) == 1
					currentByte, bitCount = 0, 0
					state = ADDR_ACK //since 8 bits collected, next rising edge is ACK
				}
			}
		case ADDR_ACK:
			if start {
				currentPacket, results = flushPacket(currentPacket, results, true, timestamp)
				bitCount, currentByte = 0, 0
				state = ADDR
			} else if stop {
				currentPacket, results = flushPacket(currentPacket, results, true, timestamp)
				state = IDLE
			} else if sclRising {
				ack := sda == 0
				currentPacket.ACKs = append(currentPacket.ACKs, ack)
				if !ack {
					currentPacket.Error = true
				}
				bitCount, currentByte = 0, 0
				state = DATA
			}
		case DATA:
			if start {
				currentPacket, results = flushPacket(currentPacket, results, true, timestamp)
				bitCount, currentByte = 0, 0
				state = ADDR
			} else if stop {
				currentPacket, results = flushPacket(currentPacket, results, false, timestamp)
				state = IDLE
			} else if sclRising {
				currentByte = (currentByte << 1) | sda
				bitCount++
				if bitCount == 8 {
					currentPacket.Data = append(currentPacket.Data, currentByte)
					currentByte = 0
					state = DATA_ACK
				}
			}

		case DATA_ACK:
			if start {
				currentPacket, results = flushPacket(currentPacket, results, false, timestamp)
				bitCount, currentByte = 0, 0
				state = ADDR
			} else if stop {
				currentPacket, results = flushPacket(currentPacket, results, false, timestamp)
				state = IDLE
			} else if sclRising {
				ack := sda == 0
				currentPacket.ACKs = append(currentPacket.ACKs, ack)
				bitCount, currentByte = 0, 0
				state = DATA
			}

		}
		prevSCL = scl
		prevSDA = sda

	}

	// Flush incomplete transaction if samples ran out mid-transaction
	if state != IDLE && currentPacket.Addr != 0 {
		currentPacket, results = flushPacket(currentPacket, results, true, 0)
	}

	return results

}
