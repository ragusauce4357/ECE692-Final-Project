"""
gui.py
ECE 692 Logic Analyzer — Entry point and MainWindow.

Dependencies:
    pip install PyQt5 pyqtgraph numpy

Usage:
    python gui.py           # live mode (connects to Go decoder via TCP)
    python gui.py --test    # test mode (simulated packets, no hardware needed)
"""

import sys
import json
import os
import argparse

import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QLabel, QToolBar, QSplitter, QTabWidget,
    QFileDialog, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont

import pyqtgraph as pg

from packets import (
    SAMPLE_RATE, DATA_CHUNK,
    BG, PANEL, BORDER, TXT, ACCENT, PROTO_COLORS
)
from transport import Simulator, Receiver, save_capture, load_capture
from display import WaveformWidget, CANTable, DecodePanel, ConnectionPanel


def load_config() -> dict:
    """Load config.json from the same directory as this file."""
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    try:
        with open(cfg_path) as f:
            return json.load(f)
    except Exception:
        return {}


# Main Window
class MainWindow(QMainWindow):
    def __init__(self, test_mode: bool = False):
        super().__init__()
        self.test_mode     = test_mode
        self._sim          = None
        self._recv         = None
        self._running      = False
        self._nsamp        = 0
        self._logic_buf    = []
        self._can_buf      = []
        self._status_state = "READY"
        self._autoscroll   = True

        self.setWindowTitle("ECE 692 Logic Analyzer")
        self.setMinimumSize(1280, 800)
        self._apply_theme()
        self._build_ui()
        self._build_toolbar()
        self._build_statusbar()
        self._apply_config()

    # Theme
    def _apply_theme(self):
        pg.setConfigOption("background", BG)
        pg.setConfigOption("foreground", TXT)
        pg.setConfigOption("antialias", True)
        #for checkmark on check boxes
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background:#000000; color:#CCCCCC;
                font-family:'Segoe UI',sans-serif; font-size:18px;
            }}
            QToolBar {{
                background:#0A0A0A; border-bottom:1px solid #222222;
                spacing:6px; padding:4px 8px;
            }}
            QPushButton {{
                background:#111111; color:#CCCCCC;
                border:1px solid #333333; border-radius:4px;
                padding:5px 14px; font-size:17px;
            }}
            QPushButton:hover {{ background:#1A1A1A; border-color:{ACCENT}; }}
            QPushButton:pressed {{ background:#080808; }}
            QPushButton#conn {{
                background:#001A0D; color:#00E5A0;
                border-color:#00A060; font-weight:bold;
            }}
            QPushButton#stop {{
                background:#1A0000; color:#FF4444;
                border-color:#882222; font-weight:bold;
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                background:#111111; color:#CCCCCC;
                border:1px solid #333333; border-radius:3px;
                padding:4px 6px; font-size:17px;
            }}
            QGroupBox {{
                border:1px solid #222222; border-radius:4px;
                margin-top:10px; color:#666666; font-size:16px;
            }}
            QGroupBox::title {{ subcontrol-origin:margin; left:8px; color:#666666; }}
            QSplitter::handle {{ background:#222222; }}
            QCheckBox {{ color:#CCCCCC; spacing:6px; font-size:17px; }}
            QCheckBox::indicator {{
                width:14px; height:14px;
                border:1px solid #333333; border-radius:2px; background:#111111;
            }}

            QCheckBox::indicator:checked {{
                border: 1px solid #00E5FF;
                background: transparent;
                image: url(checkmark.png);
            }}
            
            QLabel {{ color:#666666; font-size:17px; }}
            QLabel#val {{ color:#CCCCCC; font-family:'Courier New'; font-size:17px; }}
        """)

    # UI Layout
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        vsplit = QSplitter(Qt.Vertical)
        vsplit.setHandleWidth(3)
        vsplit.setOpaqueResize(True)
        self._wf = WaveformWidget()
        vsplit.addWidget(self._wf)

        bottom = QSplitter(Qt.Horizontal)
        bottom.setOpaqueResize(True)
        # CAN log
        can_wrap = QWidget()
        cl = QVBoxLayout(can_wrap)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        can_hdr = QLabel("  CAN FRAME LOG")
        can_hdr.setStyleSheet(f"""
            background:{PANEL}; color:{PROTO_COLORS['CAN']};
            font-size:15px; font-weight:bold; letter-spacing:2px;
            padding:4px 8px; border-bottom:1px solid {BORDER};
        """)
        self._can_tbl = CANTable()
        cl.addWidget(can_hdr)
        cl.addWidget(self._can_tbl)
        bottom.addWidget(can_wrap)

        # Settings panel
        sw = QWidget()
        sw.setMaximumWidth(300)
        sl = QVBoxLayout(sw)
        sl.setContentsMargins(8, 8, 8, 8)
        sl.setSpacing(8)
        self._decode_panel = DecodePanel()
        self._conn_panel   = ConnectionPanel()

        tabs = QTabWidget()
        tabs.addTab(self._conn_panel, "Connection")
        tabs.addTab(self._decode_panel, "Protocol Decode")
        sl.addWidget(tabs)

        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #222222;
                background: #000000;
            }

            QTabBar::tab {
                background: #111111;
                color: #CCCCCC;
                padding: 6px 12px;
                border: 1px solid #333333;
                border-bottom: none;
                min-width: 80px;
            }

            QTabBar::tab:selected {
                background: #222222;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-bottom: none;
            }

            QTabBar::tab:hover {
                background: #1A1A1A;
            }
        """)

        #sl.addWidget(self._decode_panel)
        #sl.addWidget(self._conn_panel)
        #sl.addStretch()
        bottom.addWidget(sw)
        bottom.setSizes([850, 300])

        vsplit.addWidget(bottom)
        vsplit.setSizes([560, 240])
        root.addWidget(vsplit)

        # Wire checkboxes
        self._decode_panel.measure_chk.stateChanged.connect(
            lambda s: self._wf.set_measure_mode(bool(s)))
        self._decode_panel.scroll_chk.stateChanged.connect(
            lambda s: setattr(self, "_autoscroll", bool(s)))
        self._decode_panel.clear_last_btn.clicked.connect(
            self._wf.clear_last_measure)
        self._decode_panel.clear_measures_btn.clicked.connect(
            self._wf.clear_all_measures)

    # Config
    def _apply_config(self):
        """Read config.json and pre-fill UI fields with default values."""
        cfg = load_config()
        if not cfg:
            return

        conn = cfg.get("connection", {})
        if conn.get("com_port"):
            self._conn_panel.com.setText(conn["com_port"])
        if conn.get("tcp_host"):
            self._conn_panel.host.setText(conn["tcp_host"])
        if conn.get("tcp_port"):
            self._conn_panel.port.setValue(conn["tcp_port"])
        if conn.get("go_binary"):
            self._conn_panel.go_path.setText(conn["go_binary"])

        cap = cfg.get("capture", {})
        if cap.get("view_window_ms"):
            self._decode_panel.win_spin.setValue(cap["view_window_ms"])
        if "auto_scroll" in cap:
            self._decode_panel.scroll_chk.setChecked(cap["auto_scroll"])

    # Toolbar
    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(16, 16))

        badge = QLabel("  TEST MODE  " if self.test_mode else "  LIVE  ")
        badge.setStyleSheet(f"""
            background:{'#0A2A10' if self.test_mode else '#0A1A2A'};
            color:{'#00FF80' if self.test_mode else ACCENT};
            border:1px solid {BORDER}; border-radius:3px;
            font-size:15px; font-weight:bold;
            letter-spacing:1px; padding:2px 8px;
        """)
        tb.addWidget(badge)
        tb.addSeparator()

        self._conn_btn = QPushButton("▶  Connect")
        self._conn_btn.setObjectName("conn")
        self._conn_btn.setMinimumWidth(100)
        self._conn_btn.clicked.connect(self._connect)
        tb.addWidget(self._conn_btn)

        self._stop_btn = QPushButton("■  Stop")
        self._stop_btn.setObjectName("stop")
        self._stop_btn.setMinimumWidth(80)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._disconnect)
        tb.addWidget(self._stop_btn)

        tb.addSeparator()

        save_btn = QPushButton("💾  Save")
        save_btn.clicked.connect(self._save)
        tb.addWidget(save_btn)

        load_btn = QPushButton("📂  Load")
        load_btn.clicked.connect(self._load)
        tb.addWidget(load_btn)

        tb.addSeparator()

        clr_btn = QPushButton("Clear")
        clr_btn.clicked.connect(self._clear)
        tb.addWidget(clr_btn)

        tb.addSeparator()

        self._lbl_l = QLabel("Logic: 0")
        self._lbl_c = QLabel("  CAN: 0")
        self._lbl_d = QLabel("  Dropped: 0")
        for lbl in (self._lbl_l, self._lbl_c, self._lbl_d):
            lbl.setObjectName("val")
            tb.addWidget(lbl)

        tb.addSeparator()
        tb.addWidget(QLabel("  Scroll: zoom  |  Drag: pan  |  Measure: click 2 pts"))

    # Status Bar
    def _build_statusbar(self):
        sb = self.statusBar()
        sb.setStyleSheet(f"""
            QStatusBar {{
                background:{PANEL}; border-top:1px solid {BORDER};
                color:{TXT}; font-size:15px;
            }}
        """)
        self._status_lbl = QLabel("Ready")
        sb.addPermanentWidget(self._status_lbl, 1)

        self._state_lbl = QLabel("● READY")
        self._state_lbl.setStyleSheet(
            "color:#00E5A0; font-weight:bold; font-family:'Courier New';")
        sb.addPermanentWidget(self._state_lbl)

        self._time_lbl = QLabel("  0.000 ms captured")
        self._time_lbl.setObjectName("val")
        sb.addPermanentWidget(self._time_lbl)

        self._rate_lbl = QLabel(f"  {SAMPLE_RATE//1000} kSa/s")
        self._rate_lbl.setObjectName("val")
        sb.addPermanentWidget(self._rate_lbl)

    def _set_state(self, state: str):
        self._status_state = state
        colors = {"READY": "#00E5A0", "RUNNING": ACCENT,
                  "STOPPED": "#FF9100", "WAITING": "#FFEA00"}
        color = colors.get(state, TXT)
        self._state_lbl.setText(f"● {state}")
        self._state_lbl.setStyleSheet(
            f"color:{color}; font-weight:bold; font-family:'Courier New';")

    # Connect and Disconnect
    def _connect(self):
        if self.test_mode:
            self._sim = Simulator()
            self._sim.logic_ready.connect(self._on_logic)
            self._sim.can_ready.connect(self._on_can)
            self._sim.start()
            self._status_lbl.setText("Test mode — simulating packets")
        else:
            host     = self._conn_panel.host.text().strip()
            port     = self._conn_panel.port.value()
            binary   = self._conn_panel.go_path.text().strip()
            com      = self._conn_panel.com.text().strip()
            duration = self._conn_panel.duration.value()
            protocol = self._conn_panel.protocol.currentText()
            pins     = self._conn_panel.pins.text().strip()

            if not binary:
                self._status_lbl.setText("Set Go binary path first")
                return

            protocol = "" if protocol == "None" else protocol

            self._recv = Receiver(host, port, binary, com, duration, protocol, pins)
            self._recv.logic_ready.connect(self._on_logic)
            self._recv.can_ready.connect(self._on_can)
            self._recv.status_changed.connect(self._status_lbl.setText)
            self._recv.stats_updated.connect(self._on_stats)
            self._recv.start()

        self._conn_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._running = True
        self._set_state("RUNNING")

    def _disconnect(self):
        self._running = False
        if self._sim:
            self._sim.stop()
            self._sim.wait()
            self._sim = None
        if self._recv:
            self._recv.stop()
            self._recv.wait()
            self._recv = None
        self._conn_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status_lbl.setText("Stopped")
        self._set_state("STOPPED")

    def _clear(self):
        self._wf.clear_all()
        self._can_tbl.setRowCount(0)
        self._nsamp = 0
        self._logic_buf.clear()
        self._can_buf.clear()
        self._time_lbl.setText("  0.000 ms captured")
        self._set_state("READY")

    # Save and Load
    def _save(self):
        if not self._logic_buf:
            QMessageBox.information(self, "Nothing to save",
                                    "Capture some data first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save capture", "", "JSON capture (*.json)")
        if path:
            ok = save_capture(path, self._logic_buf, self._can_buf)
            self._status_lbl.setText(
                f"Saved to {path}" if ok else "Save failed")

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load capture", "", "JSON capture (*.json)")
        if not path:
            return
        logic_chunks, can_frames, sr = load_capture(path)
        if logic_chunks is None:
            QMessageBox.warning(self, "Load failed", "Could not read capture file.")
            return
        self._clear()
        for chunk in logic_chunks:
            self._on_logic(chunk)
        for frame in can_frames:
            self._on_can(frame)
        self._status_lbl.setText(f"Loaded {path}")
        self._set_state("STOPPED")

    # Packet Handlers
    def _on_logic(self, samples: np.ndarray):
        self._nsamp += len(samples)
        self._logic_buf.append(samples.copy())

        # Cap buffer to selected memory depth
        depth_map = {"5 ms": 5, "10 ms": 10, "50 ms": 50,
                     "100 ms": 100, "500 ms": 500}
        depth_ms = depth_map.get(
            self._decode_panel.sample_depth.currentText(), 10)
        max_chunks = max(1, int((SAMPLE_RATE * depth_ms / 1000) // DATA_CHUNK))
        while len(self._logic_buf) > max_chunks:
            self._logic_buf.pop(0)

        self._time_lbl.setText(f"  {self._nsamp/SAMPLE_RATE*1e3:.1f} ms captured")
        self._wf.ingest(samples)

        if self._autoscroll:
            self._wf.scroll_to(
                self._nsamp / SAMPLE_RATE * 1e6,
                self._decode_panel.win_spin.value() * 1000)

        self._lbl_l.setText(f"Logic: {len(self._logic_buf)} pkts")

    def _on_can(self, frame: dict):
        self._can_tbl.append(frame)
        self._can_buf.append(frame)
        if len(self._can_buf) > 500:
            self._can_buf.pop(0)
        t_us = self._nsamp / SAMPLE_RATE * 1e6
        # Draw synthetic CAN waveform pulse on CAN row
        self._wf.add_can_pulse(t_us, frame["dlc"])
        # Also add annotation label
        self._wf.add_annotation(8, t_us, f"0x{frame['id']:03X}", "CAN")
        self._lbl_c.setText(f"  CAN: {self._can_tbl.rowCount()} frames")
    
    def _on_stats(self, lc: int, cc: int, dc: int):
        self._lbl_l.setText(f"Logic: {lc} pkts")
        self._lbl_c.setText(f"  CAN: {cc} frames")
        self._lbl_d.setText(f"  Dropped: {dc}")
        if dc > 0:
            self._lbl_d.setStyleSheet("color:#FF4444;")

    def closeEvent(self, event):
        self._disconnect()
        super().closeEvent(event)


#  Entry Point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ECE 692 Logic Analyzer")
    parser.add_argument("--test", action="store_true",
                        help="Run with simulated packets (no hardware needed)")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("ECE 692 Logic Analyzer")
    win = MainWindow(test_mode=args.test)
    win.show()
    sys.exit(app.exec_())