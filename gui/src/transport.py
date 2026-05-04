"""
transport.py

So here's the flow for the connection between the Go and Python programs

1) First, Python launches Go subprocess with CLI arguments
    - This is like port, duration, protocols, and pins

2) Then, Go opens the COM port and starts capturing

3) Go then streams these captured packets to Python 
over TCP socket for the capture duration. 

4) Once that duration is done, Go kills itself and \
Python closes the socket connection.

This program has the packet simulator (test mode), 
the TCP receiver thread, and capture save/load. 

"""


import socket
import time
import random
import json
import subprocess
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
 
from packets import (
    SAMPLE_RATE, DATA_CHUNK,
    parse_logic, parse_can
)


# TCP Receiver
# This launches Go and reads from its socket
# QThread basically lets us run the receiver on a background thread
# so the GUI is still responsive. Otherwise too laggy
class Receiver(QThread): 
    logic_ready = pyqtSignal(object)
    can_ready = pyqtSignal(object)
    status_changed = pyqtSignal(str)

    # params: logic_pkts count, can_frames count, dropped packets count
    stats_updated = pyqtSignal(int, int, int)   

    def __init__(self, host: str, port: int, 
                 go_binary: str, com_port: str, duration_ms: int,
                 protocol: str = "", pins: str = ""):
        
        super().__init__()
        self.host = host
        self.port = port
        self.go_binary = go_binary
        self.com_port = com_port
        self.duration_ms = duration_ms
        self.protocol = protocol
        self.pins = pins
        self._stop = False
        self._go_proc = None # holds the go subprocess once it's launched
        self._lc = self._cc = self._dc = 0 # sets logic count, CAN count, dropped count

    def _launch_go(self) -> bool:
        """
        Build CLI arguments and launch the Go decoder as a subprocess.
        """
        args = [
            self.go_binary, 
            "--port", self.com_port, 
            "--duration", str(self.duration_ms),
        ]

        if self.protocol and self.pins:
            args += ["--protocol", self.protocol, "--pins", self.pins]

        self.status_changed.emit(f"Launching the Go application: {' '.join(args)}")

        try: 
            self._go_proc = subprocess.Popen(args)
            time.sleep(1.0) # just giving Go a moment to open the socket
            return True
        except Exception as e:
            self.status_changed.emit(f"Failed to launch Go: {e}")
            return False
        
    def run (self):
        # Launch go subprocess 
        if not self._launch_go():
            return
        
        # Connect to Go's TCP
        self.status_changed.emit(f"Connecting to {self.host}:{self.port}…")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.host, self.port))
            sock.settimeout(0.5)
            self.status_changed.emit(f"Connected  {self.host}:{self.port}")
        except Exception as e:
            self.status_changed.emit(f"Connection failed: {e}")
            if self._go_proc:
                self._go_proc.terminate()
            return
        

        # read packets until Go exits or Go stops
        buf = b""
        while not self._stop:
            # check if Go has exited naturally
            # this means that our capture duration has finished.

            if self._go_proc and self._go_proc.poll() is not None: 
                self.status_changed.emit("Capture complete...Go exited")
                break

            try:
                chunk = sock.recv(4096) 
                if not chunk:
                    break
                buf += chunk
            except socket.timeout:
                continue
            except Exception as e:
                self.status_changed.emit(f"Socket error: {e}")
                break

            while len(buf) >= 3: 
                if buf[0] == 0xAA and buf[1] == 0xBB:
                    if len(buf) < 516:
                        break
                    res = parse_logic(buf[:516])
                    buf = buf[516:]
                    if res: 
                        self._lc += 1
                        self.logic_ready.emit(res[1])
                    else:
                        self._dc += 1

                elif buf[0] == 0xCC and buf[1] == 0xDD:
                    if len(buf) < 7:
                        break

                    dlc = buf[5]

                    packet_length = 7 + dlc
                    if len(buf) < packet_length:
                        break

                    res = parse_can(buf[:packet_length])
                    buf = buf[packet_length:]

                    if res: 
                        self._cc += 1
                        seq, cid, dlc, payload = res
                        self.can_ready.emit({
                            "seq": seq, "id":cid, "dlc": dlc, 
                            "data": payload, "time": time.time()
                        })

                    else: 
                        self._dc += 1

                else: 
                    buf = buf[1:]

            self.stats_updated.emit(self._lc, self._cc, self._dc)
 
        sock.close()

        if self._go_proc and self._go_proc.poll() is None:
            self._go_proc.terminate()
            
        self.status_changed.emit("Disconnected")

    def stop(self):
        self._stop = True


# Capture to save and load raw sample data to and from file
def save_capture(path: str, logic_chunks: list, can_frames: list,
                 sample_rate: int = SAMPLE_RATE) -> bool:
    """
    Save a capture session to a .json file.
    logic_chunks: list of np.ndarray (each 512 uint8)
    can_frames:   list of dicts (seq, id, dlc, data, time)
    This method returns True on success.
    """
    try:
        data = {
            "version": 1,
            "sample_rate": sample_rate,
            "logic": [chunk.tolist() for chunk in logic_chunks],
            "can": [
                {**f, "data": list(f["data"])} for f in can_frames
            ],
        }
        with open(path, "w") as fp:
            json.dump(data, fp)
        return True
    except Exception as e:
        print(f"Save failed: {e}")
        return False
 
def load_capture(path: str) -> tuple:
    """
    Load a capture from a .json file.
    Returns (logic_chunks, can_frames, sample_rate) or (None, None, None).
    """
    try:
        with open(path, "r") as fp:
            data = json.load(fp)
        logic_chunks = [np.array(c, dtype=np.uint8) for c in data["logic"]]
        can_frames   = [
            {**f, "data": bytes(f["data"])} for f in data["can"]
        ]
        sample_rate  = data.get("sample_rate", SAMPLE_RATE)
        return logic_chunks, can_frames, sample_rate
    except Exception as e:
        print(f"Load failed: {e}")
        return None, None, None
 






# Packet Simulator (just for testing)
class Simulator(QThread):
    logic_ready = pyqtSignal(object) #np.ndarray 512 uint8
    can_ready = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._stop = False
        self._ubyte = 0x41   # UART byte cycles through printable ASCII
        self._sbyte = 0x00   # SPI byte
        self._ibyte = 0x00   # I2C byte
        self._canseq = 0
 
    def _make_logic(self) -> np.ndarray:
        buf = np.zeros(DATA_CHUNK, dtype=np.uint8)
 
        # UART TX on bit1 (PC1): 115200 baud
        spb = int(SAMPLE_RATE / 115200)
        val = self._ubyte
        off = 5
        buf[:off] |= 0x02                    # idle high
        buf[off:off + spb] &= 0xFD           # start bit low
        for b in range(8):
            s = off + spb * (b + 1)
            e = min(s + spb, DATA_CHUNK)
            if s >= DATA_CHUNK:
                break
            if (val >> b) & 1:
                buf[s:e] |= 0x02
            else:
                buf[s:e] &= 0xFD
        buf[min(off + spb * 9, DATA_CHUNK - 1):] |= 0x02   # stop + idle
 
        # SPI CLK bit3, MOSI bit4, CS bit6: ~25kHz 
        sp = 40
        val2 = self._sbyte
        si = 20
        buf[si:si + 2] &= 0xBF              # CS low
        for b in range(8):
            s = si + b * sp
            m = s + sp // 2
            e = s + sp
            if e >= DATA_CHUNK:
                break
            buf[s:m] &= 0xF7                # CLK low
            buf[m:e] |= 0x08                # CLK high
            if (val2 >> (7 - b)) & 1:
                buf[s:e] |= 0x10
            else:
                buf[s:e] &= 0xEF            # MOSI low
        buf[si + 8 * sp:] |= 0x40          # CS high
 
        # I2C SDA bit7, SCL bit5: ~10kHz 
        ip = 50
        val3 = self._ibyte
        ii = 250
        if ii + 10 + 8 * ip + 10 < DATA_CHUNK:
            buf[ii:ii + 5] |= 0x80 | 0x20          # SDA + SCL high
            buf[ii + 5:ii + 10] &= 0x7F            # SDA falls (START)
            for b in range(8):
                s = ii + 10 + b * ip
                m = s + ip // 2
                e = s + ip
                if e >= DATA_CHUNK:
                    break
                buf[s:m] &= 0xDF                   # SCL low
                buf[m:e] |= 0x20                   # SCL high
                if (val3 >> (7 - b)) & 1:
                    buf[s:e] |= 0x80
                else:
                    buf[s:e] &= 0x7F               # SDA low
            stop_i = ii + 10 + 8 * ip
            if stop_i + 10 < DATA_CHUNK:
                buf[stop_i:stop_i + 5] |= 0x20    # SCL high
                buf[stop_i:stop_i + 5] &= 0x7F    # SDA low
                buf[stop_i + 5:stop_i + 10] |= 0x80  # SDA rises (STOP)
 
        self._ubyte  = ((self._ubyte - 0x20 + 1) % 95) + 0x20
        self._sbyte  = (self._sbyte + 1) & 0xFF
        self._ibyte  = (self._ibyte + 1) & 0xFF
        return buf.astype(np.uint8)
 
    def _make_can(self) -> dict:
        can_id = random.choice([0x100, 0x200, 0x3FF, 0x7E8, 0x123])
        dlc    = random.randint(1, 8)
        data   = bytes(random.randint(0, 255) for _ in range(dlc))
        seq    = self._canseq
        self._canseq = (self._canseq + 1) & 0xFF
        return {"seq": seq, "id": can_id, "dlc": dlc,
                "data": data, "time": time.time()}
 
    def run(self):
        while not self._stop:
            self.logic_ready.emit(self._make_logic())
            if self._canseq % 10 == 0:
                self.can_ready.emit(self._make_can())
            time.sleep(0.2)
 
    def stop(self):
        self._stop = True  