"""
packets.py
This file has our constants and packet parsing for logic and CAN packets.

"""
import numpy as np

# Constants
SAMPLE_RATE = 1_000_000
DATA_CHUNK = 512

# At 1 MHz, 200,000 samples means 
# 0.02s or 200ms of data visible at once
MAX_DISP_SAMPLES = 200_000

CHANNEL_NAMES = [
    "CH1  UART TX", "CH2  UART RX",
    "CH3  SPI CLK", "CH4  SPI MOSI",
    "CH5  SPI MISO", "CH6  SPI CS",
    "CH7  I2C SDA", "CH8  I2C SCL",
]

# Random tbh - just for UI purposes
CHANNEL_COLORS = [
    "#00E5FF", "#29B6F6",
    "#69FF47", "#FFEA00",
    "#FF9100", "#E040FB",
    "#FF1744", "#F5F5F5",
]

PROTO_COLORS = {
    "UART": "#00E5FF",
    "SPI":  "#69FF47",
    "I2C":  "#FFEA00",
    "CAN":  "#FF9100",
    "ERR":  "#FF1744",
}

# UI colors
BG     = "#000000"
PANEL  = "#0A0A0A"
BORDER = "#222222"
GRID   = "#1A1A1A"
AXIS   = "#333333"
TXT    = "#888888"
ACCENT = "#00E5FF"



# Packet Parsing

# XOR check - basically, the same loop is done in firmware
# If this matches the checksum byte, we're good.
def xor_check(data:bytes) -> int: 
    result = 0
    # Data can be like:
    # [0xAA, 0xBB, seq, sample0, sample1, ... sample 511]
    for byte in data:
        result ^= byte

    return result


def parse_logic(data:bytes):
    """
    Packet logic: [0xAA][0xBB][seq][512 samples][xor] = 516 bytes
    Here, we return a seq and a samples array if it's transmitted, or None if it failed
    """

    if len(data) < 516 or data [0] != 0xAA or data[1] != 0xBB:
        return None

    samples = np.frombuffer(data[3:515], dtype = np.uint8).copy()

    if xor_check(data[:515])!= data[515]:
        return None
    
    return data[2], samples


def parse_can(data:bytes):
    """
    CAN packet format: [0xCC][0xDD][seq][CANH_ID][CANL_ID][DLC][data 0-8][xor]
    Here, we return a seq, the can_id, dlc, and payload_bytes, or None if it failed
    """

    # The reason for < 7 is because with 0 data bytes, DLC = 0, and the min we have is still
    # 7 bytes.
    if len(data) < 7 or data[0] != 0xCC or data[1] != 0xDD:
        return None
    
    dlc = data[5]

    # CAN only allows 0-8 bytes per frame. So if the DLC is larger than 8, it's corrupted, 
    # so we drop it. 

    # Also, once we know how long the DLC is, the len(data) has to be 7 + dlc.
    if dlc > 8 or len(data) < 7 + dlc:
        return None

    if xor_check(data[:6 + dlc]) != data[6 + dlc]:
        return None
    
    return data[2], (data[3] << 8) | data[4], dlc, bytes(data[6:6 + dlc])


