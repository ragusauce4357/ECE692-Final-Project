import serial
import struct
import time

# Simulation Constants
BAUD_RATE = 115200
SAMPLE_COUNT = 512

# Logic packet headers
LOGIC_H1 = 0xAA
LOGIC_H2 = 0xBB

# CAN packet headers
CAN_H1 = 0xCC
CAN_H2 = 0xDD

def get_uart_bits(byte: int) -> list[int]:
    """
    Returns a list of 10 bits: 1 Start (0), 8 Data (LSB first), 1 Stop (1)
    """
    bits = [0]  # start bit
    for i in range(8):
        bits.append((byte >> i) & 1)  # LSB first
    bits.append(1)  # stop bit
    return bits

def generate_uart_samples(message: bytes, tx_channel: int) -> list[int]:
    """
    Generates 512 raw samples for a UART message on the given channel (1-8).
    Each sample byte has the TX bit set at the correct channel bit position.
    Sampling at 1MHz, 115200 baud = ~8.68 samples per bit.
    """
    SAMPLES_PER_BIT = int(1_000_000 / BAUD_RATE)
    bit_channel = tx_channel - 1  # convert channel 1-8 to bit 0-7

    raw_bits = []
    for byte in message:
        raw_bits.extend(get_uart_bits(byte))

    samples = []
    for bit in raw_bits:
        sample_byte = (bit << bit_channel) & 0xFF
        samples.extend([sample_byte] * SAMPLES_PER_BIT)

    # pad or truncate to exactly 512 samples
    samples = samples[:SAMPLE_COUNT]
    while len(samples) < SAMPLE_COUNT:
        # idle high on tx channel
        samples.append((1 << bit_channel) & 0xFF)

    return samples

def generate_spi_samples(message:bytes, mosi_channel: int, miso_channel: int, clk_channel: int, cs_channel: int) -> list[int]:
    """
    Generates 512 raw samples for a SPI message.
    Mode 0: CLK idles low, sample on rising edge. MSB first.
    MISO mirrors MOSI for loopback testing.
    ~164kHz SPI = ~6 samples per clock cycle at 1MHz sampling.
    
    """

    SAMPLES_PER_HALF_CYCLE = 3
    mosi_bit = mosi_channel - 1
    miso_bit = miso_channel - 1
    clk_bit = clk_channel - 1
    cs_bit = cs_channel -1 

    IDLE = (1 << cs_bit) # if CS high, then everything else low
    samples = []

    # idle before transaction
    for _ in range(2):
        samples.append(IDLE)

    # if CS low then transaction starts
    for byte in message:
        for bit_index in range(7, -1, -1):  # MSB first
            mosi_val = (byte >> bit_index) & 1
            miso_val = mosi_val  # loopback

            # CLK low phase
            sample_low = (mosi_val << mosi_bit) | (miso_val << miso_bit)
            for _ in range(SAMPLES_PER_HALF_CYCLE):
                samples.append(sample_low)

            # CLK high phase - decoder samples here
            sample_high = sample_low | (1 << clk_bit)
            for _ in range(SAMPLES_PER_HALF_CYCLE):
                samples.append(sample_high)

    # if CS high then transaction ends
    for _ in range(2):
        samples.append(IDLE)

    samples = samples[:SAMPLE_COUNT]
    while len(samples) < SAMPLE_COUNT:
        samples.append(IDLE)
    return samples


def generate_i2c_samples(message: bytes, scl_channel: int, sda_channel: int, addr: int = 0x52) -> list[int]:
    """
    Generates 512 raw samples for an I2C write transaction.
    100kHz I2C = 10 samples per bit at 1MHz sampling.
    Format: START | addr(7) + W(1) | ACK | data bytes | ACK each | STOP
    Since no real slave exists, ACK bit is high (NACK) — matches STM32 dummy addr behavior.
    SCL and SDA both idle high.
    """
    SAMPLES_PER_HALF = 1  # 5 samples per half cycle = 10 samples per bit = 100kHz

    scl_bit = scl_channel - 1
    sda_bit = sda_channel - 1

    IDLE = (1 << scl_bit) | (1 << sda_bit)  # both high

    def scl_high_sda_high(): return (1 << scl_bit) | (1 << sda_bit)
    def scl_high_sda_low():  return (1 << scl_bit)
    def scl_low_sda_high():  return (1 << sda_bit)
    def scl_low_sda_low():   return 0

    def clock_bit(sda_val: int) -> list[int]:
        """One full SCL clock cycle with SDA held constant."""
        sda_sample_low  = (sda_val << sda_bit)
        sda_sample_high = (sda_val << sda_bit) | (1 << scl_bit)
        result = []
        for _ in range(SAMPLES_PER_HALF):
            result.append(sda_sample_low)   # SCL low
        for _ in range(SAMPLES_PER_HALF):
            result.append(sda_sample_high)  # SCL high (decoder samples here)
        return result

    samples = []

    # Idle: both high
    for _ in range(2):
        samples.append(IDLE)

    # START: SDA falls while SCL is high
    for _ in range(SAMPLES_PER_HALF):
        samples.append(scl_high_sda_high())  # SCL high, SDA high
    for _ in range(SAMPLES_PER_HALF):
        samples.append(scl_high_sda_low())   # SCL high, SDA falls → START

    # Address byte: 7-bit addr + R/W=0 (write), MSB first
    addr_byte = (addr << 1) & 0xFF  # shift left, R/W=0
    for bit_index in range(7, -1, -1):
        bit_val = (addr_byte >> bit_index) & 1
        samples.extend(clock_bit(bit_val))

    # ACK bit: NACK since no real slave (SDA stays high)
    samples.extend(clock_bit(0))  # 0 = ACK

    # Data bytes
    for byte in message:
        for bit_index in range(7, -1, -1):  # MSB first
            bit_val = (byte >> bit_index) & 1
            samples.extend(clock_bit(bit_val))
        # ACK after each byte: NACK (no slave)
        samples.extend(clock_bit(0))

    # STOP: SDA rises while SCL is high
    for _ in range(SAMPLES_PER_HALF):
        samples.append(scl_high_sda_low())   # SCL high, SDA low
    for _ in range(SAMPLES_PER_HALF):
        samples.append(scl_high_sda_high())  # SCL high, SDA rises → STOP

    # Idle after
    for _ in range(2):
        samples.append(IDLE)

    samples = samples[:SAMPLE_COUNT]
    while len(samples) < SAMPLE_COUNT:
        samples.append(IDLE)

    return samples


def merge_samples(samples_list: list[list[int]]) -> list[int]:
    """Merges multiple channel sample lists by ORing each position."""
    merged = [0] * SAMPLE_COUNT
    for samples in samples_list:
        for i in range(SAMPLE_COUNT):
            merged[i] |= samples[i]
    return merged


def create_logic_packet(samples: list[int], seq: int) -> bytes:
    """
    Builds a 516-byte logic packet:
    [0xAA][0xBB][seq][512 samples][XOR checksum]
    """
    header = bytes([LOGIC_H1, LOGIC_H2])
    sequence = struct.pack('B', seq % 256)
    data = bytes(samples[:SAMPLE_COUNT])

    packet = header + sequence + data

    # XOR checksum over seq + samples (skip the 2 header bytes)
    checksum = 0
    for b in packet:
        checksum ^= b

    return packet + struct.pack('B', checksum)

def create_can_packet(seq: int, can_id: int, data: bytes) -> bytes:
    """
    Builds a CAN packet:
    [0xCC][0xDD][seq][ID_H][ID_L][DLC][0-8 data bytes][XOR checksum]
    """
    dlc = len(data)
    assert dlc <= 8, "CAN data cannot exceed 8 bytes"

    header = bytes([CAN_H1, CAN_H2])
    sequence = struct.pack('B', seq % 256)
    id_h = (can_id >> 8) & 0xFF
    id_l = can_id & 0xFF
    id_bytes = bytes([id_h, id_l])
    dlc_byte = struct.pack('B', dlc)

    packet = header + sequence + id_bytes + dlc_byte + data

    # XOR checksum over everything except the 2 header bytes
    checksum = 0
    for b in packet:
        checksum ^= b

    return packet + struct.pack('B', checksum)

if __name__ == "__main__":
    port_name    = input('Enter the virtual port (e.g., /tmp/ttyV0): ')
    tx_channel   = int(input('Enter UART TX channel (1-8): '))
    mosi_channel = int(input('Enter SPI MOSI channel (1-8): '))
    miso_channel = int(input('Enter SPI MISO channel (1-8): '))
    clk_channel  = int(input('Enter SPI CLK channel (1-8): '))
    cs_channel   = int(input('Enter SPI CS channel (1-8): '))
    scl_channel  = int(input('Enter I2C SCL channel (1-8): '))
    sda_channel  = int(input('Enter I2C SDA channel (1-8): '))

    try:
        ser = serial.Serial(port_name, baudrate=BAUD_RATE)
        print(f"[*] Simulation started on {port_name}...")
    except Exception as e:
        print(f"[!] Error opening port: {e}")
        exit(1)

    uart_message = b"Hello World!\x00"
    spi_message  = b"SPI Test"
    i2c_message  = b"I2C Test"
    logic_seq = 0
    can_seq   = 0

    try:
        while True:
            uart_samples = generate_uart_samples(uart_message, tx_channel)
            spi_samples  = generate_spi_samples(spi_message, mosi_channel, miso_channel, clk_channel, cs_channel)
            i2c_samples  = generate_i2c_samples(i2c_message, scl_channel, sda_channel)
            merged = merge_samples([uart_samples, spi_samples, i2c_samples])

            logic_pkt = create_logic_packet(merged, logic_seq)
            ser.write(logic_pkt)
            print(f"[*] Sent logic packet seq={logic_seq} ({len(logic_pkt)} bytes) [UART+SPI+I2C]")
            logic_seq = (logic_seq + 1) % 256

            can_pkt = create_can_packet(can_seq, can_id=0x123, data=bytes([0xCA, 0xFE, 0xBA, 0xBE, 0xDE, 0xAD, 0xBE, 0xEF]))
            ser.write(can_pkt)
            print(f"[*] Sent CAN packet seq={can_seq} id=0x123 ({len(can_pkt)} bytes)")
            can_seq = (can_seq + 1) % 256

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n[*] Simulation stopped.")
        ser.close()