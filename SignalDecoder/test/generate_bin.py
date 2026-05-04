import test
import os

def generate_to_file(filename, iterations=1, tx_channel=1, mosi_channel=3, miso_channel=4, clk_channel=5, cs_channel=6, scl_channel=7, sda_channel=8):
    """
    Generates logic and CAN packets and writes them to a binary file
    for offline testing without a virtual COM port.
    """
    logic_seq = 0
    can_seq = 0
    uart_message = b"Hello World!\x00"
    spi_message = b"SPI Test"
    i2c_message = b"I2C Test"

    with open(filename, 'wb') as f:
        print(f"[*] Generating {iterations} iteration(s)...")

        for _ in range(iterations):
            # generate and write a logic packet
            uart_samples = test.generate_uart_samples(uart_message, tx_channel)
            spi_samples = test.generate_spi_samples(spi_message, mosi_channel, miso_channel, clk_channel, cs_channel)
            i2c_samples = test.generate_i2c_samples(i2c_message, scl_channel, sda_channel)
            merged = test.merge_samples([uart_samples, spi_samples, i2c_samples])
            
            
            logic_pkt = test.create_logic_packet(merged, logic_seq)
            f.write(logic_pkt)
            print(f"[+] Logic packet seq={logic_seq} ({len(logic_pkt)} bytes)")
            logic_seq = (logic_seq + 1) % 256

            # generate and write a CAN packet
            can_pkt = test.create_can_packet(
                can_seq,
                can_id=0x123,
                data=bytes([0xCA, 0xFE, 0xBA, 0xBE, 0xDE, 0xAD, 0xBE, 0xEF])
            )
            f.write(can_pkt)
            print(f"[+] CAN packet seq={can_seq} id=0x123 ({len(can_pkt)} bytes)")
            can_seq = (can_seq + 1) % 256

    print(f"[+] Done! Written to {filename} ({os.path.getsize(filename)} bytes)")

if __name__ == "__main__":
    output_file = "capture_test.bin"
    tx_channel = int(input("Enter TX channel number (1-8): "))
    mosi_channel = int(input('Enter SPI MOSI channel (1-8): '))
    miso_channel = int(input('Enter SPI MISO channel (1-8): '))
    clk_channel  = int(input('Enter SPI CLK channel (1-8): '))
    cs_channel   = int(input('Enter SPI CS channel (1-8): '))
    scl_channel  = int(input('Enter I2C SCL channel (1-8): '))
    sda_channel  = int(input('Enter I2C SDA channel (1-8): '))
    generate_to_file(output_file, iterations=5, tx_channel=tx_channel, mosi_channel=mosi_channel, miso_channel=miso_channel, clk_channel=clk_channel, cs_channel=cs_channel, scl_channel=scl_channel, sda_channel=sda_channel)