"""
display.py
All UI widgets: waveform display, CAN table, decode panel, connection panel.

Layout:
- Left QLabel column for channel names (avoids pyqtgraph rotated text bug)
- Right GraphicsLayoutWidget inside a QScrollArea for vertical scrolling
- 9 channels total: 8 GPIO + 1 synthetic CAN bus activity row
"""

import time
from collections import deque

import numpy as np
import pyqtgraph as pg

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QCheckBox,
    QDoubleSpinBox, QSpinBox, QLineEdit, QFileDialog,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QAbstractItemView, QSizePolicy, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from packets import (
    SAMPLE_RATE, DATA_CHUNK, MAX_DISP_SAMPLES,
    CHANNEL_NAMES, CHANNEL_COLORS, PROTO_COLORS,
    BG, PANEL, BORDER, GRID, AXIS, TXT, ACCENT
)

CH_HEIGHT   = 75
LABEL_WIDTH = 115
N_CHANNELS  = 9   # 8 GPIO + 1 CAN

CAN_CH      = 8   # index of synthetic CAN row
CAN_COLOR   = PROTO_COLORS["CAN"]

ALL_NAMES   = CHANNEL_NAMES + ["CAN  BUS"]
ALL_COLORS  = CHANNEL_COLORS + [CAN_COLOR]


# Color palette that cycles for each new measurement pair
MEASURE_COLORS = [
    "#FFD600",  # yellow
    "#00E5FF",  # cyan
    "#FF4081",  # pink
    "#69FF47",  # green
    "#FF9100",  # orange
    "#E040FB",  # purple
    "#00E676",  # mint
    "#FF1744",  # red
]


# ──────────────────────────────────────────────────────────────
#  MEASUREMENT PAIR
#  Stores one complete pair of vertical markers + horizontal
#  label line across all plots.
# ──────────────────────────────────────────────────────────────
class MeasurePair:
    def __init__(self, t1: float, t2: float, plots: list, color: str = "#FFD600"):
        self.t1 = t1
        self.t2 = t2
        self._plots  = plots
        self._lines1 = []   # solid vertical at t1
        self._lines2 = []   # solid vertical at t2
        self._hlabel = None # TextItem on middle plot

        for p in plots:
            l1 = pg.InfiniteLine(pos=t1, angle=90, movable=False,
                                 pen=pg.mkPen(color, width=1.5))
            l2 = pg.InfiniteLine(pos=t2, angle=90, movable=False,
                                 pen=pg.mkPen(color, width=1.5))
            p.addItem(l1)
            p.addItem(l2)
            self._lines1.append(l1)
            self._lines2.append(l2)

        # Horizontal dashed line + label only in the middle plot, at y=0.5
        mid_plot = plots[len(plots) // 2]
        dt = abs(t2 - t1)
        freq_str = f"  {1/(dt*1e-6):.1f} Hz" if dt > 0 else ""
        label_txt = f"Δt={dt:.1f}μs{freq_str}"

        # Single dashed horizontal line across the span in the middle plot only
        self._hline = pg.PlotDataItem(
            [min(t1, t2), max(t1, t2)], [0.5, 0.5],
            pen=pg.mkPen(color, width=0.8, style=Qt.DashLine))
        mid_plot.addItem(self._hline)
        self._hline_plot = mid_plot

        # Label sits on top of the dashed line (anchor bottom-center)
        self._hlabel = pg.TextItem(label_txt, color=color, anchor=(0.5, 1.0))
        self._hlabel.setFont(QFont("Courier New", 8))
        mid_t = (t1 + t2) / 2
        self._hlabel.setPos(mid_t, 0.5)
        mid_plot.addItem(self._hlabel)
        self._label_plot = mid_plot

    def remove(self):
        for i, p in enumerate(self._plots):
            try:
                p.removeItem(self._lines1[i])
                p.removeItem(self._lines2[i])
            except Exception:
                pass
        try:
            self._hline_plot.removeItem(self._hline)
            self._label_plot.removeItem(self._hlabel)
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────
#  WAVEFORM WIDGET
# ──────────────────────────────────────────────────────────────
class WaveformWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{BG};")

        self._plots   = []
        self._curves  = []
        self._anns    = [[] for _ in range(N_CHANNELS)]
        self._t_buf   = deque(maxlen=MAX_DISP_SAMPLES)
        self._ch_buf  = [deque(maxlen=MAX_DISP_SAMPLES) for _ in range(8)]
        self._can_buf = deque(maxlen=MAX_DISP_SAMPLES)   # synthetic CAN
        self._nsamp   = 0
        self._last_draw = 0.0

        # Crosshair
        self._vlines = []

        # Measure state
        self._measure_mode = False
        self._measure_t1   = None
        self._measure_color_idx = 0   # cycles through MEASURE_COLORS
        self._pending_lines1 = []   # lines for in-progress first click
        self._pending_lines2 = []
        self._measure_pairs: list[MeasurePair] = []

        self._build()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left label column ──────────────────────────────────
        
        label_col = QWidget()
        #label_col.setFixedWidth(LABEL_WIDTH)
        label_col.setStyleSheet(f"background:#000000; border-right:1px solid {BORDER};")
        lc = QVBoxLayout(label_col)
        lc.setContentsMargins(0, 0, 0, 0)
        lc.setSpacing(0)

        for i in range(N_CHANNELS):
            lbl = QLabel(ALL_NAMES[i])
            lbl.setFixedHeight(CH_HEIGHT)
            lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            lbl.setContentsMargins(8, 0, 4, 0)
            sep = "2px solid #FF9100" if i == CAN_CH else f"1px solid {BORDER}"
            lbl.setStyleSheet(f"""
                color: {ALL_COLORS[i]};
                font-family: 'Courier New';
                font-size: 16px;
                font-weight: bold;
                border-bottom: {sep};
                background: #000000;
            """)
            lc.addWidget(lbl)

        # Time axis spacer
        ts = QLabel("Time (μs)")
        ts.setFixedHeight(28)
        ts.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        ts.setContentsMargins(8, 0, 4, 0)
        ts.setStyleSheet(f"color:{TXT}; font-size:14px; background:#000000;")
        lc.addWidget(ts)
        root.addWidget(label_col)

        label_scroll = QScrollArea()
        label_scroll.setWidgetResizable(False)
        label_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        label_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        label_scroll.setFrameShape(QFrame.NoFrame)
        label_scroll.setWidget(label_col)
        label_scroll.setFixedWidth(LABEL_WIDTH)

        root.addWidget(label_scroll)

        # ── Right: scroll area containing pyqtgraph ────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.verticalScrollBar().setSingleStep(1)
        scroll.verticalScrollBar().setPageStep(20)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: #000000; }}
            QScrollBar:vertical {{
                background: #111111; width: 10px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: #333333; border-radius: 5px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        inner = QWidget()
        inner.setStyleSheet("background:#000000;")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)

        self._glw = pg.GraphicsLayoutWidget()
        self._glw.setBackground(BG)
        self._glw.ci.layout.setSpacing(0)
        self._glw.ci.layout.setContentsMargins(0, 0, 0, 0)
        # Fix total height so scroll works
        total_h = CH_HEIGHT * N_CHANNELS + 28
        inner.setFixedHeight(total_h)
        #self._glw.setMinimumHeight(total_h)
        #self._glw.setMaximumHeight(total_h)

        for i in range(N_CHANNELS):
            p = self._glw.addPlot(row=i, col=0)
            p.hideAxis("left")
            p.showAxis("bottom", i == N_CHANNELS - 1)
            if i == N_CHANNELS - 1:
                ax = p.getAxis("bottom")
                ax.setPen(pg.mkPen("#555555"))
                ax.setTextPen(pg.mkPen("#AAAAAA"))
                ax.setStyle(tickFont=QFont("Courier New", 9))
                ax.setHeight(28)
            else:
                p.hideAxis("bottom")

            p.setYRange(-0.2, 1.4)
            p.setMouseEnabled(x=True, y=False)
            p.setMenuEnabled(False)
            p.hideButtons()
            p.showGrid(x=True, y=False, alpha=0.08)
            p.setFixedHeight(CH_HEIGHT)
            # CAN row gets an orange top border feel via background
            if i == CAN_CH:
                p.getViewBox().setBackgroundColor(pg.mkColor(255, 150, 0, 12))
            elif i % 2 == 1:
                p.getViewBox().setBackgroundColor(pg.mkColor(255, 255, 255, 5))

            if i > 0:
                p.setXLink(self._plots[0])

            p.addItem(pg.InfiniteLine(
                pos=0.5, angle=0,
                pen=pg.mkPen(GRID, style=Qt.DashLine, width=0.5)))

            color = ALL_COLORS[i]
            curve = p.plot(
                pen=pg.mkPen(color=color, width=1.5),
                connect="finite")

            vl = pg.InfiniteLine(
                angle=90, movable=False,
                pen=pg.mkPen("#FFFFFF", width=0.7, style=Qt.DashLine))
            vl.setVisible(False)
            p.addItem(vl)
            self._vlines.append(vl)

            self._plots.append(p)
            self._curves.append(curve)
            

        # Cursor label on bottom plot
        self._cursor_lbl = pg.TextItem("", color="#CCCCCC", anchor=(0, 1))
        self._cursor_lbl.setFont(QFont("Courier New", 9))
        self._plots[-1].addItem(self._cursor_lbl)

        # Trigger marker
        self._trigger_line = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen("#FF1744", width=1.5))
        self._trigger_line.setVisible(False)
        self._plots[0].addItem(self._trigger_line)

        inner_layout.addWidget(self._glw)
        scroll.setWidget(inner)
        scroll.verticalScrollBar().setSingleStep(15)
        root.addWidget(scroll)

        #for synchronous scrolling
        scroll.verticalScrollBar().valueChanged.connect(
            label_scroll.verticalScrollBar().setValue
        )
        label_scroll.verticalScrollBar().valueChanged.connect(
            scroll.verticalScrollBar().setValue
        )

        self._glw.scene().sigMouseMoved.connect(self._on_mouse_move)
        self._glw.scene().sigMouseClicked.connect(self._on_mouse_click)

    # ── Mouse ────────────────────────────────────────────────
    def _scene_to_time(self, pos):
        for p in self._plots:
            if p.sceneBoundingRect().contains(pos):
                return p.getViewBox().mapSceneToView(pos).x()
        return None

    def _on_mouse_move(self, pos):
        t = self._scene_to_time(pos)
        if t is not None:
            for vl in self._vlines:
                vl.setVisible(True)
                vl.setPos(t)
            if self._measure_mode and self._measure_t1 is not None:
                dt = abs(t - self._measure_t1)
                freq = f"  {1/(dt*1e-6):.1f} Hz" if dt > 0 else ""
                self._cursor_lbl.setText(f"Δt={dt:.1f}μs{freq}")
                for l2 in self._pending_lines2:
                    l2.setPos(t)
            else:
                self._cursor_lbl.setText(f"{t:.1f} μs")
            self._cursor_lbl.setPos(t, -0.18)
        else:
            for vl in self._vlines:
                vl.setVisible(False)
            self._cursor_lbl.setText("")

    def _on_mouse_click(self, event):
        if not self._measure_mode:
            return
        t = self._scene_to_time(event.scenePos())
        if t is None:
            return

        if self._measure_t1 is None:
            # First click — place pending start lines
            self._clear_pending()
            self._measure_t1 = t
            color = MEASURE_COLORS[self._measure_color_idx % len(MEASURE_COLORS)]
            for p in self._plots:
                l1 = pg.InfiniteLine(pos=t, angle=90, movable=False,
                                     pen=pg.mkPen(color, width=1.5))
                l2 = pg.InfiniteLine(pos=t, angle=90, movable=False,
                                     pen=pg.mkPen(color, width=1.0,
                                                  style=Qt.DashLine))
                p.addItem(l1)
                p.addItem(l2)
                self._pending_lines1.append(l1)
                self._pending_lines2.append(l2)
        else:
            # Second click — finalise as a permanent MeasurePair
            color = MEASURE_COLORS[self._measure_color_idx % len(MEASURE_COLORS)]
            self._measure_color_idx += 1
            self._clear_pending()
            pair = MeasurePair(self._measure_t1, t, self._plots, color)
            self._measure_pairs.append(pair)
            self._measure_t1 = None
            self._cursor_lbl.setText("")

    def _clear_pending(self):
        for i, p in enumerate(self._plots):
            if i < len(self._pending_lines1):
                try:
                    p.removeItem(self._pending_lines1[i])
                    p.removeItem(self._pending_lines2[i])
                except Exception:
                    pass
        self._pending_lines1 = []
        self._pending_lines2 = []

    # ── Public API ───────────────────────────────────────────
    def set_measure_mode(self, enabled: bool):
        self._measure_mode = enabled
        if not enabled:
            self._clear_pending()
            self._measure_t1 = None

    def clear_all_measures(self):
        self._clear_pending()
        for pair in self._measure_pairs:
            pair.remove()
        self._measure_pairs = []
        self._measure_t1 = None
        self._measure_color_idx = 0

    def clear_last_measure(self):
        """Remove only the most recently completed measurement pair."""
        self._clear_pending()
        self._measure_t1 = None
        if self._measure_pairs:
            self._measure_pairs[-1].remove()
            self._measure_pairs.pop()
            self._measure_color_idx = max(0, self._measure_color_idx - 1)

    def set_trigger_marker(self, t_us: float):
        self._trigger_line.setPos(t_us)
        self._trigger_line.setVisible(True)

    def ingest(self, samples: np.ndarray):
        """Buffer samples, redraw at most every 100ms."""
        n   = len(samples)
        t0  = self._nsamp / SAMPLE_RATE * 1e6
        t_new = np.linspace(t0, t0 + n / SAMPLE_RATE * 1e6, n, endpoint=False)
        self._t_buf.extend(t_new.tolist())
        self._nsamp += n
        for ch in range(8):
            self._ch_buf[ch].extend(((samples >> (ch + 1)) & 1).tolist())
        # CAN stays at 0 (idle) by default
        self._can_buf.extend([0.0] * n)

        now = time.time()
        if now - self._last_draw >= 0.1:
            self._last_draw = now
            t = np.array(self._t_buf)
            for ch in range(8):
                d = np.array(self._ch_buf[ch], dtype=float)
                if len(d) == len(t) > 0:
                    self._curves[ch].setData(t, d)
            # CAN curve
            d_can = np.array(self._can_buf, dtype=float)
            if len(d_can) == len(t) > 0:
                self._curves[CAN_CH].setData(t, d_can)

    def add_can_pulse(self, t_us: float, dlc: int):
        """Draw a synthetic CAN frame pulse on the CAN row."""
        # CAN frame duration at 500kbps:
        # SOF(1) + ID(11) + control(6) + data(8*dlc) + CRC(15) + ACK(2) + EOF(7) = 42 + 8*dlc bits
        n_bits   = 42 + 8 * dlc
        dur_us   = n_bits * 2.0   # 2μs per bit at 500kbps
        t_end    = t_us + dur_us
        # Draw as two pulses: high for duration
        t_pts  = [t_us, t_us, t_end, t_end]
        d_pts  = [0.0,  1.0,  1.0,  0.0]
        item   = pg.PlotDataItem(
            t_pts, d_pts,
            pen=pg.mkPen(CAN_COLOR, width=1.5),
            connect="finite")
        self._plots[CAN_CH].addItem(item)
        self._anns[CAN_CH].append(item)
        if len(self._anns[CAN_CH]) > 100:
            self._plots[CAN_CH].removeItem(self._anns[CAN_CH].pop(0))

    def add_annotation(self, ch: int, t_us: float, label: str, proto: str):
        color = PROTO_COLORS.get(proto, "#FFF")
        txt   = pg.TextItem(label, color=color, anchor=(0.5, 1.0))
        txt.setFont(QFont("Courier New", 7))
        txt.setPos(t_us, 1.35)
        self._plots[ch].addItem(txt)
        self._anns[ch].append(txt)
        if len(self._anns[ch]) > 200:
            self._plots[ch].removeItem(self._anns[ch].pop(0))

    def clear_all(self):
        self._t_buf.clear()
        for b in self._ch_buf:
            b.clear()
        self._can_buf.clear()
        self._nsamp = 0
        for c in self._curves:
            c.setData([], [])
        for ch in range(N_CHANNELS):
            for item in self._anns[ch]:
                self._plots[ch].removeItem(item)
            self._anns[ch].clear()
        self._trigger_line.setVisible(False)
        self.clear_all_measures()

    def scroll_to(self, t_end_us: float, window_us: float):
        self._plots[0].setXRange(t_end_us - window_us, t_end_us, padding=0)

    @property
    def total_samples(self):
        return self._nsamp


# ──────────────────────────────────────────────────────────────
#  CAN FRAME TABLE
# ──────────────────────────────────────────────────────────────
class CANTable(QTableWidget):
    MAX_ROWS = 500

    def __init__(self):
        super().__init__()
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["Time", "ID", "DLC", "Data", "ASCII"])
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.horizontalHeader().setDefaultSectionSize(80)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setDefaultSectionSize(22)
        self.verticalHeader().hide()
        self.setShowGrid(False)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setStyleSheet(f"""
            QTableWidget {{
                background:{PANEL}; color:#C0D0E0;
                font-family:'Courier New'; font-size:16px;
                border:none;
                alternate-background-color:#0D0D0D;
                selection-background-color:#1A3050;
            }}
            QHeaderView::section {{
                background:#080808; color:{TXT};
                font-size:15px; font-weight:bold;
                border:none; border-bottom:1px solid {BORDER}; padding:4px;
            }}
            QScrollBar:vertical {{
                background:#111111; width:8px; border:none;
            }}
            QScrollBar::handle:vertical {{
                background:#333333; border-radius:4px; min-height:20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height:0px;
            }}
        """)

    def append(self, frame: dict):
        if self.rowCount() >= self.MAX_ROWS:
            self.removeRow(0)
        row = self.rowCount()
        self.insertRow(row)
        ts       = time.strftime("%H:%M:%S", time.localtime(frame["time"]))
        hex_id   = f"0x{frame['id']:03X}"
        data_hex = " ".join(f"{b:02X}" for b in frame["data"])
        ascii_s  = "".join(chr(b) if 32 <= b < 127 else "." for b in frame["data"])
        for col, val in enumerate([ts, hex_id, str(frame["dlc"]), data_hex, ascii_s]):
            item = QTableWidgetItem(val)
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            if col == 1:
                item.setForeground(QColor(PROTO_COLORS["CAN"]))
            self.setItem(row, col, item)
        self.scrollToBottom()


# ──────────────────────────────────────────────────────────────
#  DECODE PANEL
# ──────────────────────────────────────────────────────────────
class DecodePanel(QGroupBox):
    def __init__(self):
        super().__init__("Protocol Decode")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 4, 0, 0)
        outer.setSpacing(0)

        # Scroll area so the bottom panel doesn't need to be resized
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{
                background: #111111; width: 8px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: #333333; border-radius: 4px; min-height: 16px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        inner = QWidget()
        l = QGridLayout(inner)
        l.setSpacing(6)
        l.setContentsMargins(8, 4, 8, 8)

        self._uart_chk = QCheckBox("UART")
        self._uart_chk.setChecked(True)
        self._baud = QComboBox()
        self._baud.addItems(["9600","19200","38400","57600","115200","230400"])
        self._baud.setCurrentText("115200")
        l.addWidget(self._uart_chk, 0, 0)
        l.addWidget(QLabel("Baud:"), 0, 1)
        l.addWidget(self._baud, 0, 2)

        self._spi_chk = QCheckBox("SPI")
        self._spi_chk.setChecked(True)
        l.addWidget(self._spi_chk, 1, 0)

        self._i2c_chk = QCheckBox("I2C")
        self._i2c_chk.setChecked(True)
        l.addWidget(self._i2c_chk, 2, 0)

        can_lbl = QLabel("CAN  (decoded by STM32)")
        can_lbl.setStyleSheet(f"color:{PROTO_COLORS['CAN']};")
        l.addWidget(can_lbl, 3, 0, 1, 3)

        # Sample rate
        l.addWidget(QLabel("Sample rate:"), 4, 0)
        self.sample_rate = QComboBox()
        self.sample_rate.addItems(["100 kHz", "500 kHz", "1 MHz"])
        self.sample_rate.setCurrentText("1 MHz")
        l.addWidget(self.sample_rate, 4, 1, 1, 2)

        # Memory depth
        l.addWidget(QLabel("Mem depth:"), 5, 0)
        self.sample_depth = QComboBox()
        self.sample_depth.addItems(["5 ms", "10 ms", "50 ms", "100 ms", "500 ms"])
        self.sample_depth.setCurrentText("10 ms")
        l.addWidget(self.sample_depth, 5, 1, 1, 2)

        # View window
        l.addWidget(QLabel("View window:"), 6, 0)
        self.win_spin = QDoubleSpinBox()
        self.win_spin.setRange(0.5, 500)
        self.win_spin.setValue(10)
        self.win_spin.setSuffix(" ms")
        l.addWidget(self.win_spin, 6, 1, 1, 2)

        self.scroll_chk = QCheckBox("Auto-scroll")
        self.scroll_chk.setChecked(True)
        l.addWidget(self.scroll_chk, 7, 0, 1, 3)

        self.measure_chk = QCheckBox("⟷  Measure (click 2 points)")
        self.measure_chk.setStyleSheet(f"color:{PROTO_COLORS['SPI']};")
        l.addWidget(self.measure_chk, 8, 0, 1, 3)

        clr_last = QPushButton("↩  Reset last marker")
        clr_last.setStyleSheet("font-size:10px; padding:3px 6px;")
        l.addWidget(clr_last, 9, 0, 1, 3)
        self.clear_last_btn = clr_last

        clr_m = QPushButton("Clear all measurements")
        clr_m.setStyleSheet("font-size:15px; padding:3px 6px;")
        l.addWidget(clr_m, 10, 0, 1, 3)
        self.clear_measures_btn = clr_m

        scroll.setWidget(inner)
        outer.addWidget(scroll)


# ──────────────────────────────────────────────────────────────
#  CONNECTION PANEL
# ──────────────────────────────────────────────────────────────
class ConnectionPanel(QGroupBox):
    def __init__(self):
        super().__init__("Connection")
        l = QGridLayout(self)
        l.setSpacing(6)

        l.addWidget(QLabel("Go binary:"), 0, 0)
        self.go_path = QLineEdit()
        self.go_path.setPlaceholderText("path/to/SignalDecoder")
        l.addWidget(self.go_path, 0, 1)
        browse = QPushButton("…")
        browse.setMaximumWidth(28)
        browse.clicked.connect(self._browse)
        l.addWidget(browse, 0, 2)

        l.addWidget(QLabel("COM port:"), 1, 0)
        self.com = QLineEdit("COM3")
        l.addWidget(self.com, 1, 1, 1, 2)

        l.addWidget(QLabel("Duration:"), 2, 0)
        self.duration = QSpinBox()
        self.duration.setRange(100, 60000)
        self.duration.setValue(5000)
        self.duration.setSuffix(" ms")
        l.addWidget(self.duration, 2, 1, 1, 2)

        l.addWidget(QLabel("Protocol:"), 3, 0)
        self.protocol = QComboBox()
        self.protocol.addItems(["None", "uart", "spi", "i2c", "can"])
        l.addWidget(self.protocol, 3, 1, 1, 2)

        l.addWidget(QLabel("Pins:"), 4, 0)
        self.pins = QLineEdit()
        self.pins.setPlaceholderText("e.g. tx1rx2")
        l.addWidget(self.pins, 4, 1, 1, 2)

        l.addWidget(QLabel("TCP host:"), 5, 0)
        self.host = QLineEdit("127.0.0.1")
        l.addWidget(self.host, 5, 1, 1, 2)

        l.addWidget(QLabel("TCP port:"), 6, 0)
        self.port = QSpinBox()
        self.port.setRange(1024, 65535)
        self.port.setValue(5000)
        l.addWidget(self.port, 6, 1, 1, 2)

    def _browse(self):
        p, _ = QFileDialog.getOpenFileName(None, "Select Go binary")
        if p:
            self.go_path.setText(p)