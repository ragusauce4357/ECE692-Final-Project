"""
decoder.py
This file has our constants, packet parsing, 
and protocol decoders: UART, SPI, I2C, CAN (just testing).

"""

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
BG     = "#0B0F1A"
PANEL  = "#0F1520"
BORDER = "#1E2D40"
GRID   = "#1A2233"
AXIS   = "#2A3A50"
TXT    = "#8899AA"
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

# Continue with Packet Parsing, 
# Helpers, Decoders, and Decode Engine that orchestrates the decoders