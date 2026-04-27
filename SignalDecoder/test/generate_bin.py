import test
import os

def generate_to_file(filename, iterations=1, tx_channel=1):
    """
    Generates logic and CAN packets and writes them to a binary file
    for offline testing without a virtual COM port.
    """
    seq_num = 0
    message = b"Hello World!\x00"

    with open(filename, 'wb') as f:
        print(f"[*] Generating {iterations} iteration(s)...")

        for _ in range(iterations):
            # generate and write a logic packet
            samples = test.generate_uart_samples(message, tx_channel)
            logic_pkt = test.create_logic_packet(samples, seq_num)
            f.write(logic_pkt)
            print(f"[+] Logic packet seq={seq_num} ({len(logic_pkt)} bytes)")
            seq_num += 1

            # generate and write a CAN packet
            can_pkt = test.create_can_packet(
                seq_num,
                can_id=0x123,
                data=bytes([0xCA, 0xFE, 0xBA, 0xBE, 0xDE, 0xAD, 0xBE, 0xEF])
            )
            f.write(can_pkt)
            print(f"[+] CAN packet seq={seq_num} id=0x123 ({len(can_pkt)} bytes)")
            seq_num += 1

    print(f"[+] Done! Written to {filename} ({os.path.getsize(filename)} bytes)")

if __name__ == "__main__":
    output_file = "capture_test.bin"
    tx_channel = int(input("Enter TX channel number (1-8): "))
    generate_to_file(output_file, iterations=5, tx_channel=tx_channel)