package decoder

// The SPI decoder algorithm

// 1. Extract channel bits - from each sample byte, pull out the CLK, MOSI, MISO,
// CS (if we use) bits using the channel numbers from pins

// 2. As long as CS is low, the transaction is alive.
// 3. Watch for rising clock edges where CLK goes from 0 to 1
// 4. Sample MOSI and MISO on each clock edge
// 5. Collect 8 bits, so after 8 clock edges, assemble the byte MSB.
// 6. Repeat this as long as CS is low.
// 7. Return a slice of decoded transfers with timestamp, MISO, and MOSI byte.
import (
	"github.com/ragusauce4357/ECE692-Final-Project/SignalDecoder/internal/config"
)

type DecodedSPIPackets struct {
	Timestamp float64 //in us
	MOSI      byte
	MISO      byte
	Error     bool // if we get < 8 clock edges or if the transaction was incomplete.
}

//Mode explanation:
/*
Mode 0 (CPOL=0, CPHA=0): sample on rising edge, CLK idles low
Mode 1 (CPOL=0, CPHA=1): sample on falling edge, CLK idles low
Mode 2 (CPOL=1, CPHA=0): sample on falling edge, CLK idles high
Mode 3 (CPOL=1, CPHA=1): sample on rising edge, CLK idles high
*/
func DecodeSPI(samples []byte, pins config.ProtocolPins, mode int) []DecodedSPIPackets {

	//Example cli argument to help with the logic:
	//go run . --port /tmp/ttyV1 --protocol SPI --pins miso3mosi4clk5cs6 --duration 5000
	misoCH := byte((pins >> 12) & 0xF) //3
	mosiCH := byte((pins >> 8) & 0xF)  //4
	clkCH := byte((pins >> 4) & 0xF)   //5
	//this might be optional but
	csCH := byte(pins & 0xF) //6

	// So the channels determine what bit it is
	// Our arrangement is this below
	// PC0 PC1 PC2 PC3 PC4 PC5 PC6 PC6
	// CH1 CH2 CH3 CH4 CH5 CH6 CH7 CH8
	// B0  B1  B2  B3  B4  B5  B6  B7
	// Here, B0 is bit 0 and so on

	var prevCLK byte = 0
	//In case we use CS for real purposes. If its always 0, thats handled too
	var prevCS byte = 1

	var counter int = 0
	var misoStore byte
	var mosiStore byte
	var byteStart float64 = 0

	//if no CS, treat it as always tied low or active
	inTransaction := (csCH == 0)
	var results []DecodedSPIPackets

	for i, sample := range samples {
		miso := (sample >> (misoCH - 1)) & 1
		mosi := (sample >> (mosiCH - 1)) & 1
		clk := (sample >> (clkCH - 1)) & 1
		cs := byte(0)
		// handle CS
		if csCH != 0 {
			cs = (sample >> (csCH - 1)) & 1
		}

		// if CS falling edge then it's transaction start
		if prevCS == 1 && cs == 0 {
			byteStart = float64(i)
			inTransaction = true
			counter, mosiStore, misoStore = 0, 0, 0
		}

		//if it's a CS rising edge then the transaction is over
		// we flush everything to struct
		if prevCS == 0 && cs == 1 {
			if counter > 0 {
				transfer := DecodedSPIPackets{
					byteStart,
					mosiStore,
					misoStore,
					counter < 8, //only an error if its a partial byte
				}
				results = append(results, transfer)
			}
			inTransaction = false
			mosiStore, misoStore, counter = 0, 0, 0
		}

		// if its the correct clock edge based on SPI mode and we're in transaction
		rising_edge := prevCLK == 0 && clk == 1
		falling_edge := prevCLK == 1 && clk == 0
		sample_edge := (mode == 0 || mode == 3) && rising_edge || (mode == 1 || mode == 2) && falling_edge
		if inTransaction && cs == 0 && sample_edge {
			// sample
			if counter == 8 {
				transfer := DecodedSPIPackets{
					byteStart,
					mosiStore,
					misoStore,
					false,
				}
				results = append(results, transfer)
				counter, misoStore, mosiStore = 0, 0, 0
				byteStart = float64(i)
			}
			mosiStore = (mosiStore << 1) | mosi
			misoStore = (misoStore << 1) | miso
			counter += 1

		}
		prevCLK = clk
		prevCS = cs
	}

	// if samples ran out mid-transaction
	// like if we have leftover bytes that never got flushed
	// debug statement - log.Printf("[DecodeSPI]: end of samples - inTransaction=%v counter=%d", inTransaction, counter)
	if inTransaction && counter > 0 {
		results = append(results, DecodedSPIPackets{byteStart, mosiStore, misoStore, counter < 8})
	}
	return results

}
