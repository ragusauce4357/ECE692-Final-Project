package main

import (
	"log"
	//"net"

	"github.com/ragusauce4357/ECE692-Final-Project/SignalDecoder/internal/config"
	//"github.com/ragusauce4357/ECE692-Final-Project/SignalDecoder/internal/logging"
	"github.com/ragusauce4357/ECE692-Final-Project/SignalDecoder/internal/serial"
)

func main() {
	//preamble := "[main]: "

	// parse CLI args and validate
	cfg, err := config.GetConfig()
	if err != nil {
		log.Fatal(err)
	}

	cfg.Print()
	/*

		**TCP Listener: just uncomment this when Python integration is ready**
		// start TCP listener, Python will connect to this
		listener, err := net.Listen("tcp", ":8080")
		if err != nil {
			log.Fatal(logging.ErrLog(preamble) + "Failed to start TCP listener: " + err.Error())
		}
		defer listener.Close()
		log.Println(logging.StatLog(preamble) + "Waiting for Python to connect on port 8080...")

		// block until Python connects
		tcpConn, err := listener.Accept()
		if err != nil {
			log.Fatal(logging.ErrLog(preamble) + "Failed to accept TCP connection: " + err.Error())
		}
		defer tcpConn.Close()
		log.Println(logging.StatLog(preamble) + "Python connected.")
	*/

	//dummy TCP connection for testing COM port without Python
	tcpConn, _ := serial.NewDummyConn()
	// start the main capture loop
	if err := serial.Run(cfg, tcpConn); err != nil {
		log.Fatal(err)
	}

	// uncomment this too when Python is ready
	// log.Println(logging.StatLog(preamble) + "Capture complete. Exiting.")
}
