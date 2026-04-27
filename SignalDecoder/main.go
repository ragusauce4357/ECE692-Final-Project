package main

import (
	"log"

	"github.com/ragusauce4357/ECE692-Final-Project/SignalDecoder/internal/config"
	"github.com/ragusauce4357/ECE692-Final-Project/SignalDecoder/internal/serial"
)

func main() {
	config, err := config.GetConfig()

	if err != nil {
		log.Fatal(err)
	}

	serial.VerifyReception(config)

	config.Print()
}
