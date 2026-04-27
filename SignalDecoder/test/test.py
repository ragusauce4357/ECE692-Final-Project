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
    for b in packet[2:]:
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
    for b in packet[2:]:
        checksum ^= b

    return packet + struct.pack('B', checksum)

if __name__ == "__main__":
    port_name = input('Enter the virtual port (e.g., COM5 or /dev/ttyUSB0): ')
    tx_channel = int(input('Enter TX channel number (1-8): '))

    try:
        ser = serial.Serial(port_name, baudrate=BAUD_RATE)
        print(f"[*] Simulation started on {port_name}...")
    except Exception as e:
        print(f"[!] Error opening port: {e}")
        exit(1)

    # "Hello World!\0"
    message = b"Hello World!\x00"
    seq_num = 0

    try:
        while True:
            # send a logic packet with UART samples
            samples = generate_uart_samples(message, tx_channel)
            logic_pkt = create_logic_packet(samples, seq_num)
            ser.write(logic_pkt)
            print(f"[*] Sent logic packet seq={seq_num} ({len(logic_pkt)} bytes)")
            seq_num += 1

            # send a CAN packet with fake data
            can_pkt = create_can_packet(seq_num, can_id=0x123, data=bytes([0xCA, 0xFE, 0xBA, 0xBE, 0xDE, 0xAD, 0xBE, 0xEF]))
            ser.write(can_pkt)
            print(f"[*] Sent CAN packet seq={seq_num} id=0x123 ({len(can_pkt)} bytes)")
            seq_num += 1

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n[*] Simulation stopped.")
        ser.close()