package decoder

/*
For I2C, we need to handle all of these states, so we can use a state machine.
IDLE: SCL and SDA are both High AFTER a STOP condition
START: SDA High to Low while SCL is High
DATA_BITS: Sample SDA on SCL rising edge, collect 8 bits
ACK: 9th clock pulse, SDA low = ACK, high = NACK
STOP: SDA Low to High while SCL is High (back to IDLE)
*/

type DecodedI2CPacket struct {
	Timestamp float64
	Addr      byte   // 7-bit address
	RW        bool   //write=0, read=1 (per I2C TI datasheet)
	Data      []byte //data bytes transmitted
	ACKs      []bool //one per byte (device addr ACK + register addr ACK + data ACK)
	Error     bool   //NACK on addr or incomplete transaction
}

//I2C algorithm (see meanings of the conditions up top)
// Wait for START condition
//Collect 9 bits on each SCL rising edge (DATA_BITS + ACK)
// First 9 bits = 7-bit address + RW bit + ACK
