# Testing

For simple preliminary testing

## Hello World! hexdump

Running `generate_bin.py` generates the following binary. It emulates sending the character string `Hello World!\0` over a UART TX line on channel 1 (LSB of the masked n shifted IDR register), at a baud rate of 9600, with the signal being oversampled at 100kHz. On the STM's side, the following will happen:

- DMA will oversample the signal (at some frequency TBD) and read the IDR register into a memory buffer.
- The CPU will then read that memory buffer, obtain the channel bits alone, and run a RLE algorithm (very minimal byte comparison). It will then byte pack into a new memory buffer, following the format: `[Data (1 byte)] [Duration (0-255)]`, where the duration is the number of bytes that remained the same throughout the oversampling period.
- Once we have 30 such pairs (60 bytes), the CPU will prepend a header (`0xAABB`) as well as a Sequence (1 byte, counting 0-255) which will simply count up (to find lost packets), and then *append* an XOR checksum as the very last byte. Thus, the complete 64 byte packet which will be sent over USB to the laptop will look like the following:
    - `[Header 0xAABB] [Sequence # (0 - 255)] [30 Pairs of [Channel State (1B)] [Duration (1B)]] [Checksum (XOR or all 63 previous bytes)]`

`generate_bin.py` will run the aforementioned simulation, and print the output to a binary file. The `test.py` is a little more complicated and is explained below. Since it's running at 9600 baud, and being sampled at 100kHz, there are roughly 10 samples per RLE packet, which matches the 0x0a which appears all over the hexdump. The table below contains the first 192 bytes manually parsed back into the "Hello World!" string.

```hexdump
00000000: aabb 0000 0a01 0a00 0a00 0a01 0a00 0a00 
00000010: 0a00 0a00 0a01 0a01 0a00 0a00 0a01 0a00 
00000020: 0a01 0a00 0a01 0a01 0a00 0a01 0a01 0a00 
00000030: 0a00 0a00 0a01 0a01 0a00 0a01 0a01 0a11 
00000040: aabb 0100 0a00 0a00 0a01 0a01 0a00 0a01 
00000050: 0a01 0a01 0a01 0a00 0a00 0a01 0a00 0a00 
00000060: 0a00 0a00 0a00 0a00 0a01 0a00 0a01 0a00 
00000070: 0a01 0a01 0a01 0a00 0a01 0a01 0a00 0a10 
00000080: aabb 0201 0a01 0a01 0a01 0a00 0a01 0a01 
00000090: 0a01 0a00 0a00 0a01 0a00 0a00 0a01 0a01 
000000a0: 0a00 0a01 0a01 0a00 0a00 0a00 0a01 0a01 
000000b0: 0a00 0a00 0a01 0a00 0a00 0a00 0a00 0a12 
000000c0: aabb 0301 0a00 0a00 0a00 0a00 0a01 0a00 
000000d0: 0a00 0a00 0a00 0a00 0a00 0a00 0a00 0a01 
000000e0: ff01 ff00 0000 0000 0000 0000 0000 0000 
000000f0: 0000 0000 0000 0000 0000 0000 0000 0012 
```

In the 30 pairs of channel state and duration, the duration bytes have been omitted. Additionally, the 30 channel states are in binary.

| Location | Header | Sequence \# | 30 Channel States | XOR Checksum |
|:--------:|:------:|:-----------:|:-----------------:|:------------:|
| 00000000 |  aabb  | 00 | 010010000110010101101100011011 | 11 |
| 00000040 |  aabb  | 01 | 000110111100100000010101110110 | 10 |
| 00000080 |  aabb  | 02 | 111101110010011011000110010000 | 12 |

Concatenating the channel states into just channel one, and converting to hex gives: `48656c6c6f20576f726c64`, which is ascii for: `Hello World`.

## Using `test.py`

I haven't tested this yet, and the code for `test.py` came from Gemini; I've only read it over. Also the hexdump worked as expected with only a few tweaks so I expect this to work correctly too. 

First, you'll have to be on a linux device with `socat` installed (`sudo apt install socat` on debian/ubuntu). Then, run `socat.sh` with root permissions, and giving two serial ports as cli arguments. One example is shown below (assuming USB0 and USB1 aren't already taken up).

```bash
sudo bash ./socat.sh /dev/ttyUSB0 /dev/ttyUSB1
```

This command will use socat to create a bidirectional serial bridge between USB0 and USB1. By running `test.py`, and connecting it to `/dev/ttyUSB0`, you should be able to connect the main Go program to `/dev/ttyUSB1` and read the Hello World from there.

Simply put, `test.py` emulates the STM as realistically as possible. Although it only emulates UART, which should be enough for our purposes. 
