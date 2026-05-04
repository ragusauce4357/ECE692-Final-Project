package config

import (
	"errors"
	"log"
	"regexp"
	"strconv"

	"github.com/ragusauce4357/ECE692-Final-Project/SignalDecoder/internal/logging"
)

// TODO make sure they're not the same channels

func match(re *regexp.Regexp, s string) string {
	m := re.FindStringSubmatch(s)
	if len(m) < 2 {
		return ""
	}
	return m[1]
}

// Parses a string of format "tx0rx1" into tx and rx
// channel numbers.
func parseUART(pins string) (ProtocolPins, error) {
	preamble := "[parseUART]: "

	log.Print(logging.StatLog(preamble) + "Parsing UART pins...")

	re_tx := regexp.MustCompile(`tx(\d+)`)
	re_rx := regexp.MustCompile(`rx(\d+)`)

	tx := match(re_tx, pins)
	rx := match(re_rx, pins)

	if tx == "" || rx == "" {
		return 0, errors.New(logging.ErrLog(preamble) + "Did not find channel numbers")
	}

	txStr, _ := strconv.Atoi(tx)
	rxStr, _ := strconv.Atoi(rx)

	txInt := ProtocolPins(txStr)
	rxInt := ProtocolPins(rxStr)

	log.Printf(logging.StatLog(preamble)+"Using channels %d, %d, for tx and rx\n", txInt, rxInt)

	if txInt > 8 || rxInt > 8 || txInt == 0 || rxInt == 0 {
		return 0, errors.New(logging.ErrLog(preamble) + "Channel number out of bounds")
	}

	if txInt == rxInt {
		return 0, errors.New(logging.ErrLog(preamble) + "Tx channel cannot equal rx channel")
	}

	txInt = txInt << 12
	rxInt = rxInt << 8

	log.Print(logging.StatLog(preamble) + "Completed UART pin parsing")

	return txInt | rxInt, nil
}

// Parses a string of format "miso0mosi1clk2" optionally with
// "cs3" into miso mosi clk and cs channel numbers.
func parseSPI(pins string) (ProtocolPins, error) {
	preamble := "[parseSPI]: "

	log.Print(logging.StatLog(preamble) + "Parsing SPI pins...")

	re_miso := regexp.MustCompile(`miso(\d+)`)
	re_mosi := regexp.MustCompile(`mosi(\d+)`)
	re_clk := regexp.MustCompile(`clk(\d+)`)
	re_cs := regexp.MustCompile(`cs(\d+)`)

	miso := match(re_miso, pins)
	mosi := match(re_mosi, pins)
	clk := match(re_clk, pins)
	cs := match(re_cs, pins)

	if miso == "" || mosi == "" || clk == "" {
		return 0, errors.New(logging.ErrLog(preamble) + "Did not find channel numbers")
	}

	misoInt, _ := strconv.Atoi(miso)
	mosiInt, _ := strconv.Atoi(mosi)
	clkInt, _ := strconv.Atoi(clk)
	var csInt int
	if cs == "" {
		csInt = 0
	} else {
		csInt, _ = strconv.Atoi(cs)
	}

	if misoInt > 8 || mosiInt > 8 || clkInt > 8 || csInt > 8 ||
		misoInt == 0 || mosiInt == 0 || clkInt == 0 {
		return 0, errors.New(logging.ErrLog(preamble) + "Channel number out of bounds")
	}

	arr := [4]int{misoInt, mosiInt, clkInt, csInt}

	visited := make(map[int]bool)
	for _, val := range arr {
		if visited[val] {
			return 0, errors.New(logging.ErrLog(preamble) + "Cannot have two or more pins on one channel.")
		}
		visited[val] = true
	}

	log.Printf(logging.StatLog(preamble)+"Using channels %d, %d, %d, %d, for miso, mosi, clk, and cs\n", misoInt, mosiInt, clkInt, csInt)

	misoInt = misoInt << 12
	mosiInt = mosiInt << 8
	clkInt = clkInt << 4

	log.Print(logging.StatLog(preamble) + "Completed SPI pin parsing")

	return ProtocolPins(misoInt | mosiInt | clkInt | csInt), nil
}

// Parses a string of format "sda0scl1" into sda and scl
// channel numbers.
func parseI2C(pins string) (ProtocolPins, error) {
	preamble := "[parseI2C]: "

	log.Print(logging.StatLog(preamble) + "Parsing I2C pins...")

	re_sda := regexp.MustCompile(`sda(\d+)`)
	re_scl := regexp.MustCompile(`scl(\d+)`)

	sda := match(re_sda, pins)
	scl := match(re_scl, pins)

	if sda == "" || scl == "" {
		return 0, errors.New(logging.ErrLog(preamble) + "Did not find channel numbers")
	}

	sdaInt, _ := strconv.Atoi(sda)
	sclInt, _ := strconv.Atoi(scl)

	log.Printf(logging.StatLog(preamble)+"Using channels %d, %d, for sda and scl\n", sdaInt, sclInt)

	if sdaInt > 8 || sclInt > 8 || sdaInt == 0 || sclInt == 0 {
		return 0, errors.New(logging.ErrLog(preamble) + "Channel number out of bounds")
	}

	if sdaInt == sclInt {
		return 0, errors.New(logging.ErrLog(preamble) + "Sda channel cannot equal scl channel")
	}

	sdaInt = sdaInt << 12
	sclInt = sclInt << 8

	log.Print(logging.StatLog(preamble) + "Completed I2C pin parsing.")

	return ProtocolPins(sdaInt | sclInt), nil
}

// Parses a string of format "canh0canl1" into canh and canl
// channel numbers.
// I commented this out since the decoding for CAN is done on the STM with bxCAN
// If needed, we can always revert to this. 
/*
func parseCAN(pins string) (ProtocolPins, error) {
	preamble := "[parseCAN]: "

	log.Print(logging.StatLog(preamble) + "Parsing CAN pins...")

	re_canh := regexp.MustCompile(`canh(\d+)`)
	re_canl := regexp.MustCompile(`canl(\d+)`)

	canh := match(re_canh, pins)
	canl := match(re_canl, pins)

	if canh == "" || canl == "" {
		return 0, errors.New(logging.ErrLog(preamble) + "Did not find channel numbers")
	}

	canhInt, _ := strconv.Atoi(canh)
	canlInt, _ := strconv.Atoi(canl)

	if canhInt >= 8 || canlInt >= 8 || canhInt == 0 || canlInt == 0 {
		return 0, errors.New(logging.ErrLog(preamble) + "Channel number out of bounds")
	}

	if canhInt == canlInt {
		return 0, errors.New(logging.ErrLog(preamble) + "Canh channel cannot equal canl channel")
	}

	log.Printf(logging.StatLog(preamble)+"Using channels %d, %d, for canh and canl\n", canhInt, canlInt)

	canhInt = canhInt << 12
	canlInt = canlInt << 8

	log.Print(logging.StatLog(preamble) + "Completed CAN pin parsing.")

	return ProtocolPins(canhInt | canlInt), nil
}
*/
