"""
Topium Dice Market

A small Python market simulator built around a simple random engine:
coin flips choose direction, dice rolls choose movement size.

The engine generates raw 1-minute candles, aggregates those candles into
higher timeframes, and displays the result as an interactive candlestick chart
with VWAP bands.
"""

import random
import csv
import tkinter as tk
from tkinter import filedialog, messagebox
from dataclasses import dataclass
from datetime import datetime, timedelta

from matplotlib.figure import Figure
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


APP_BG = "#070A0F"
PANEL_BG = "#0D111A"
CARD_BG = "#121826"
CHART_BG = "#0B1118"
GRID = "#1F2937"
TEXT = "#D7DEE9"
MUTED = "#8A93A6"
GREEN = "#22C7A9"
RED = "#FF4D5E"
BLUE = "#3B82F6"
CYAN = "#38BDF8"
PURPLE = "#A78BFA"
ORANGE = "#F59E0B"
YELLOW = "#FBBF24"
BORDER = "#243044"
WHITE = "#FFFFFF"
TRACK_BG = "#273244"
TRACK_FILL = "#3B82F6"
KNOB = "#D7DEE9"


TIMEFRAMES = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "45m": 45,
    "1h": 60,
    "2h": 120,
    "4h": 240,
    "1D": 1440,
    "1W": 10080,
    "1M": 43200,  # simple 30-day month approximation
}


@dataclass
class Candle:
    index: int
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    rolls: str = ""


class SmoothSlider(tk.Frame):
    """Small custom slider so the controls do not look like old Tkinter sliders."""

    def __init__(self, parent, variable, minimum, maximum, step, width=150, height=22, bg=PANEL_BG):
        super().__init__(parent, bg=bg)

        self.variable = variable
        self.minimum = float(minimum)
        self.maximum = float(maximum)
        self.step = float(step)
        self.width = width
        self.height = height
        self.pad = 8
        self.bg = bg
        self.is_int = isinstance(variable, tk.IntVar)

        self.canvas = tk.Canvas(
            self,
            width=self.width,
            height=self.height,
            bg=self.bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.canvas.pack(fill="x", expand=True)

        self.canvas.bind("<Button-1>", self.on_mouse)
        self.canvas.bind("<B1-Motion>", self.on_mouse)
        self.canvas.bind("<Configure>", lambda event: self.redraw())
        self.variable.trace_add("write", lambda *_: self.redraw())

        self.redraw()

    def clamp(self, value):
        return max(self.minimum, min(self.maximum, value))

    def snap(self, value):
        if self.step > 0:
            value = round((value - self.minimum) / self.step) * self.step + self.minimum

        value = self.clamp(value)

        if self.is_int:
            return int(round(value))

        return round(value, 4)

    def value_to_x(self, value):
        usable = max(1, self.canvas.winfo_width() - self.pad * 2)
        ratio = (float(value) - self.minimum) / (self.maximum - self.minimum)
        return self.pad + usable * ratio

    def x_to_value(self, x):
        usable = max(1, self.canvas.winfo_width() - self.pad * 2)
        ratio = (x - self.pad) / usable
        value = self.minimum + ratio * (self.maximum - self.minimum)
        return self.snap(value)

    def on_mouse(self, event):
        self.variable.set(self.x_to_value(event.x))

    def redraw(self):
        self.canvas.delete("all")

        width = max(1, self.canvas.winfo_width())
        center_y = self.height // 2
        left = self.pad
        right = width - self.pad
        value = self.clamp(float(self.variable.get()))
        knob_x = self.value_to_x(value)

        self.canvas.create_line(
            left,
            center_y,
            right,
            center_y,
            fill=TRACK_BG,
            width=7,
            capstyle="round",
        )

        self.canvas.create_line(
            left,
            center_y,
            knob_x,
            center_y,
            fill=TRACK_FILL,
            width=7,
            capstyle="round",
        )

        self.canvas.create_oval(
            knob_x - 6,
            center_y - 6,
            knob_x + 6,
            center_y + 6,
            fill=KNOB,
            outline=WHITE,
            width=1,
        )


class TopiumDiceMarket:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Topium Dice Market")
        self.root.geometry("1230x750")
        self.root.minsize(1040, 650)
        self.root.configure(bg=APP_BG)

        self.starting_price = 1000.0
        self.price = self.starting_price
        self.start_time = datetime.now().replace(second=0, microsecond=0)
        self.next_index = 0

        # The engine always stores raw 1-minute candles; the chart aggregates them when needed.
        self.candles: list[Candle] = []
        self.display_candles: list[Candle] = []

        self.running = False
        self.after_id = None
        self.chart_ready = False

        self.dice_scale = tk.DoubleVar(value=1.0)
        self.coin_bias = tk.IntVar(value=0)
        self.speed_ms = tk.IntVar(value=120)
        self.visible_bars = tk.IntVar(value=120)
        self.timeframe = tk.StringVar(value="1m")

        self.vwap_enabled = tk.BooleanVar(value=True)
        self.band1_enabled = tk.BooleanVar(value=True)
        self.band2_enabled = tk.BooleanVar(value=True)
        self.band3_enabled = tk.BooleanVar(value=True)
        self.indicator_y_values = []

        # View state.
        self.auto_follow = True
        self.view_start = 0
        self.pan_active = False
        self.pan_start_x = None
        self.pan_start_view = 0

        self.timeframe_buttons = {}

        self.build_ui()
        self.build_chart()
        self.chart_ready = True
        self.update_chart()
        self.update_stats()
        self.update_timeframe_buttons()

    # -----------------------------
    # UI
    # -----------------------------
    def build_ui(self):
        shell = tk.Frame(self.root, bg=APP_BG)
        shell.pack(fill="both", expand=True, padx=14, pady=14)

        header = tk.Frame(shell, bg=APP_BG)
        header.pack(fill="x", pady=(0, 10))

        left_header = tk.Frame(header, bg=APP_BG)
        left_header.pack(side="left")

        tk.Label(
            left_header,
            text="Topium Dice Market",
            bg=APP_BG,
            fg=TEXT,
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")

        tk.Label(
            left_header,
            text="Coin flip + dice roll market simulator",
            bg=APP_BG,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w")

        self.status_label = tk.Label(
            header,
            text="● STOPPED",
            bg=APP_BG,
            fg=YELLOW,
            font=("Segoe UI", 12, "bold"),
        )
        self.status_label.pack(side="right")

        toolbar = tk.Frame(
            shell,
            bg=PANEL_BG,
            padx=12,
            pady=12,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        toolbar.pack(fill="x", pady=(0, 8))

        actions = tk.Frame(toolbar, bg=PANEL_BG)
        actions.pack(side="left", padx=(0, 16))

        self.toggle_button = self.make_button(actions, "START", self.toggle, GREEN, width=12)
        self.toggle_button.grid(row=0, column=0, padx=(0, 8))

        self.make_button(actions, "STEP", self.step_once, BLUE, width=9).grid(row=0, column=1, padx=(0, 8))
        self.make_button(actions, "+10", lambda: self.generate_many(10), BLUE, width=7).grid(row=0, column=2, padx=(0, 8))
        self.make_button(actions, "RESET", self.reset, RED, width=9).grid(row=0, column=3, padx=(0, 8))
        self.make_button(actions, "RESET VIEW", self.reset_view, "#475569", width=11).grid(row=0, column=4, padx=(0, 8))
        self.make_button(actions, "EXPORT", self.export_csv, "#334155", width=9).grid(row=0, column=5)

        controls = tk.Frame(toolbar, bg=PANEL_BG)
        controls.pack(side="left", fill="x", expand=True)

        self.add_control(controls, "Dice Scale", "movement multiplier", self.dice_scale, 0.1, 10.0, 0.1, 0)
        self.add_control(controls, "Coin Bias", "up chance tilt", self.coin_bias, -40, 40, 1, 1, "%")
        self.add_control(controls, "Speed", "delay per 1m candle", self.speed_ms, 20, 1000, 20, 2, " ms")
        self.add_control(controls, "Visible Bars", "zoom/chart width", self.visible_bars, 30, 300, 10, 3)

        stats = tk.Frame(toolbar, bg=PANEL_BG)
        stats.pack(side="right", padx=(16, 0))

        self.price_card = self.stat_card(stats, "PRICE", "1000.00", GREEN, 0)
        self.change_card = self.stat_card(stats, "CHANGE", "+0.00%", TEXT, 1)
        self.bars_card = self.stat_card(stats, "BARS", "0", TEXT, 2)
        self.view_card = self.stat_card(stats, "VIEW", "LIVE", YELLOW, 3)

        self.build_timeframe_bar(shell)

        body = tk.Frame(shell, bg=APP_BG)
        body.pack(fill="both", expand=True)

        chart_panel = tk.Frame(
            body,
            bg=PANEL_BG,
            padx=8,
            pady=8,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        chart_panel.pack(side="left", fill="both", expand=True)

        self.chart_container = chart_panel

        side = tk.Frame(
            body,
            bg=PANEL_BG,
            width=285,
            padx=12,
            pady=12,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        side.pack(side="right", fill="y", padx=(12, 0))
        side.pack_propagate(False)

        tk.Label(
            side,
            text="HOW TO USE",
            bg=PANEL_BG,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        help_text = (
            "Drag chart left/right to pan\n"
            "Mouse wheel to zoom\n"
            "Reset View returns to live\n"
            "Timeframes aggregate 1m candles"
        )

        tk.Label(
            side,
            text=help_text,
            bg=CARD_BG,
            fg=MUTED,
            justify="left",
            anchor="nw",
            padx=8,
            pady=8,
            font=("Segoe UI", 8),
            highlightbackground=BORDER,
            highlightthickness=1,
        ).pack(fill="x", pady=(0, 10))

        tk.Label(
            side,
            text="INDICATORS",
            bg=PANEL_BG,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        indicators_box = tk.Frame(
            side,
            bg=CARD_BG,
            padx=8,
            pady=8,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        indicators_box.pack(fill="x", pady=(0, 10))

        self.add_indicator_toggle(indicators_box, "VWAP", self.vwap_enabled)
        self.add_indicator_toggle(indicators_box, "Band 1", self.band1_enabled)
        self.add_indicator_toggle(indicators_box, "Band 2", self.band2_enabled)
        self.add_indicator_toggle(indicators_box, "Band 3", self.band3_enabled)

        tk.Label(
            side,
            text="LAST 1M CANDLE ROLLS",
            bg=PANEL_BG,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        self.rolls_label = tk.Label(
            side,
            text="-",
            bg=CARD_BG,
            fg=TEXT,
            justify="left",
            anchor="nw",
            padx=8,
            pady=8,
            font=("Consolas", 8),
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        self.rolls_label.pack(fill="x", pady=(0, 10))

        tk.Label(
            side,
            text="MARKET INFO",
            bg=PANEL_BG,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        self.info_label = tk.Label(
            side,
            text="",
            bg=CARD_BG,
            fg=MUTED,
            justify="left",
            anchor="nw",
            padx=8,
            pady=8,
            font=("Segoe UI", 8),
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        self.info_label.pack(fill="x")

    def build_timeframe_bar(self, parent):
        bar = tk.Frame(
            parent,
            bg=PANEL_BG,
            padx=10,
            pady=8,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        bar.pack(fill="x", pady=(0, 8))

        tk.Label(
            bar,
            text="TIMEFRAMES",
            bg=PANEL_BG,
            fg=MUTED,
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(0, 10))

        for tf in TIMEFRAMES.keys():
            button = tk.Button(
                bar,
                text=tf,
                command=lambda value=tf: self.set_timeframe(value),
                bg=CARD_BG,
                fg=TEXT,
                activebackground=BLUE,
                activeforeground=WHITE,
                relief="flat",
                bd=0,
                width=5,
                height=1,
                cursor="hand2",
                font=("Segoe UI", 9, "bold"),
            )
            button.pack(side="left", padx=(0, 5))
            self.timeframe_buttons[tf] = button

    def make_button(self, parent, text, command, color, width=10):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg=WHITE,
            activebackground=color,
            activeforeground=WHITE,
            relief="flat",
            bd=0,
            height=2,
            width=width,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
        )

    def add_control(self, parent, title, subtitle, variable, low, high, step, column, suffix=""):
        box = tk.Frame(parent, bg=PANEL_BG)
        box.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 14, 0))
        parent.grid_columnconfigure(column, weight=1)

        top = tk.Frame(box, bg=PANEL_BG)
        top.pack(fill="x")

        tk.Label(
            top,
            text=title.upper(),
            bg=PANEL_BG,
            fg=TEXT,
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left")

        value_label = tk.Label(
            top,
            text="",
            bg=PANEL_BG,
            fg=WHITE,
            font=("Segoe UI", 9, "bold"),
        )
        value_label.pack(side="right")

        tk.Label(
            box,
            text=subtitle,
            bg=PANEL_BG,
            fg=MUTED,
            font=("Segoe UI", 7),
        ).pack(anchor="w", pady=(0, 5))

        SmoothSlider(
            box,
            variable=variable,
            minimum=low,
            maximum=high,
            step=step,
            width=150,
            height=22,
            bg=PANEL_BG,
        ).pack(fill="x")

        def refresh(*_):
            value = variable.get()
            if isinstance(variable, tk.IntVar):
                value_label.config(text=f"{int(value)}{suffix}")
            else:
                value_label.config(text=f"{float(value):.2f}{suffix}")

            if variable is self.visible_bars and getattr(self, "chart_ready", False):
                self.auto_follow = True
                self.update_chart()
                self.update_stats()

        variable.trace_add("write", refresh)
        refresh()

    def add_indicator_toggle(self, parent, text, variable):
        row = tk.Frame(parent, bg=CARD_BG)
        row.pack(fill="x", pady=(0, 6))

        check = tk.Checkbutton(
            row,
            text=text,
            variable=variable,
            command=self.update_chart,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BG,
            activeforeground=TEXT,
            selectcolor=PANEL_BG,
            bd=0,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        )
        check.pack(anchor="w")

    def stat_card(self, parent, title, value, color, column):
        card = tk.Frame(
            parent,
            bg=CARD_BG,
            padx=10,
            pady=7,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        card.grid(row=0, column=column, padx=(0 if column == 0 else 6, 0))

        tk.Label(
            card,
            text=title,
            bg=CARD_BG,
            fg=MUTED,
            font=("Segoe UI", 7, "bold"),
        ).pack(anchor="w")

        label = tk.Label(
            card,
            text=value,
            bg=CARD_BG,
            fg=color,
            font=("Segoe UI", 11, "bold"),
            width=8,
            anchor="w",
        )
        label.pack(anchor="w")
        return label

    # -----------------------------
    # Chart
    # -----------------------------
    def build_chart(self):
        self.fig = Figure(figsize=(9, 6), facecolor=CHART_BG)
        self.ax = self.fig.add_subplot(111)

        self.ax.set_facecolor(CHART_BG)
        self.ax.set_axisbelow(True)
        self.ax.grid(True, color=GRID, alpha=0.55, linewidth=0.8)
        self.ax.tick_params(colors=MUTED, labelsize=9)

        for spine in self.ax.spines.values():
            spine.set_color(CHART_BG)

        self.ax.yaxis.tick_right()
        self.ax.set_ylabel("Price", color=MUTED)

        self.wicks = LineCollection([], linewidths=1.25, zorder=4)
        self.bodies = PolyCollection([], closed=True, zorder=5)

        self.ax.add_collection(self.wicks)
        self.ax.add_collection(self.bodies)

        # Subtle reference line for the original starting price.
        self.start_line = self.ax.axhline(
            self.starting_price,
            color="#40516A",
            linestyle="-",
            linewidth=0.9,
            alpha=0.65,
            zorder=1,
        )

        self.start_tag = self.ax.annotate(
            "",
            xy=(0.005, self.starting_price),
            xycoords=("axes fraction", "data"),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            ha="left",
            color=MUTED,
            fontsize=7,
            fontweight="normal",
            bbox=dict(boxstyle="round,pad=0.18", fc="#121826", ec="#40516A", alpha=0.28),
            clip_on=True,
            zorder=8,
        )

        # VWAP and deviation bands.
        self.vwap_line, = self.ax.plot([], [], color=CYAN, linewidth=1.7, alpha=0.98, zorder=7)
        self.u1_line, = self.ax.plot([], [], color=BLUE, linewidth=1.05, alpha=0.85, linestyle="-.", zorder=6)
        self.l1_line, = self.ax.plot([], [], color=BLUE, linewidth=1.05, alpha=0.85, linestyle="-.", zorder=6)
        self.u2_line, = self.ax.plot([], [], color=PURPLE, linewidth=0.95, alpha=0.75, linestyle="--", zorder=5)
        self.l2_line, = self.ax.plot([], [], color=PURPLE, linewidth=0.95, alpha=0.75, linestyle="--", zorder=5)
        self.u3_line, = self.ax.plot([], [], color=ORANGE, linewidth=0.85, alpha=0.65, linestyle=":", zorder=4)
        self.l3_line, = self.ax.plot([], [], color=ORANGE, linewidth=0.85, alpha=0.65, linestyle=":", zorder=4)

        self.band1_fill = PolyCollection([], closed=True, color=BLUE, alpha=0.035, zorder=1)
        self.band2_fill = PolyCollection([], closed=True, color=PURPLE, alpha=0.025, zorder=1)
        self.band3_fill = PolyCollection([], closed=True, color=ORANGE, alpha=0.018, zorder=1)

        self.ax.add_collection(self.band3_fill)
        self.ax.add_collection(self.band2_fill)
        self.ax.add_collection(self.band1_fill)

        self.price_line = self.ax.axhline(
            self.price,
            color=GREEN,
            linestyle="--",
            linewidth=1,
            alpha=0.8,
            zorder=2,
        )

        self.price_tag = self.ax.annotate(
            "",
            xy=(1, self.price),
            xycoords=("axes fraction", "data"),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            ha="left",
            color=WHITE,
            fontsize=9,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.25", fc=GREEN, ec=GREEN, alpha=0.95),
            clip_on=False,
            zorder=8,
        )

        self.empty_text = self.ax.text(
            0.5,
            0.5,
            "Press START or STEP to generate candles",
            transform=self.ax.transAxes,
            ha="center",
            va="center",
            color=MUTED,
            fontsize=13,
        )

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_container)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Basic chart navigation.
        self.canvas.mpl_connect("button_press_event", self.on_chart_press)
        self.canvas.mpl_connect("button_release_event", self.on_chart_release)
        self.canvas.mpl_connect("motion_notify_event", self.on_chart_motion)
        self.canvas.mpl_connect("scroll_event", self.on_chart_scroll)

    # -----------------------------
    # Timeframes
    # -----------------------------
    def set_timeframe(self, timeframe):
        if timeframe not in TIMEFRAMES:
            return

        self.timeframe.set(timeframe)
        self.auto_follow = True
        self.view_start = 0
        self.update_timeframe_buttons()
        self.update_chart()
        self.update_stats()

    def update_timeframe_buttons(self):
        active = self.timeframe.get()

        for tf, button in self.timeframe_buttons.items():
            if tf == active:
                button.config(bg=BLUE, fg=WHITE, activebackground=BLUE)
            else:
                button.config(bg=CARD_BG, fg=TEXT, activebackground=BLUE)

    def aggregate_candles(self):
        tf_minutes = TIMEFRAMES.get(self.timeframe.get(), 1)

        if not self.candles:
            return []

        if tf_minutes == 1:
            return list(self.candles)

        grouped = []
        current = None
        current_bucket = None

        for candle in self.candles:
            bucket = candle.index // tf_minutes

            if bucket != current_bucket:
                if current is not None:
                    grouped.append(current)

                current_bucket = bucket
                current = Candle(
                    index=candle.index,
                    timestamp=candle.timestamp,
                    open=candle.open,
                    high=candle.high,
                    low=candle.low,
                    close=candle.close,
                    volume=candle.volume,
                    rolls="Aggregated timeframe candle",
                )
            else:
                current.high = max(current.high, candle.high)
                current.low = min(current.low, candle.low)
                current.close = candle.close
                current.volume += candle.volume

        if current is not None:
            grouped.append(current)

        return grouped

    # -----------------------------
    # Chart update
    # -----------------------------
    def get_visible_slice(self):
        self.display_candles = self.aggregate_candles()
        total = len(self.display_candles)
        count = int(self.visible_bars.get())

        if total == 0:
            return []

        count = max(10, min(count, max(total, count)))

        if self.auto_follow:
            self.view_start = max(0, total - count)

        self.view_start = max(0, min(self.view_start, max(0, total - count)))
        return self.display_candles[self.view_start:self.view_start + count]

    def update_chart(self):
        visible = self.get_visible_slice()
        n = len(visible)
        tf = self.timeframe.get()

        self.empty_text.set_visible(n == 0)
        self.ax.set_title(
            f"FAKEUSD - {tf} - Coin/Dice Engine",
            color=TEXT,
            fontsize=13,
            fontweight="bold",
            loc="left",
            pad=12,
        )

        if n == 0:
            self.wicks.set_segments([])
            self.bodies.set_verts([])
            self.clear_indicator_data()
            self.ax.set_xlim(-1, 10)
            self.ax.set_ylim(self.starting_price - 50, self.starting_price + 50)
            self.start_line.set_ydata([self.starting_price, self.starting_price])
            self.start_tag.xy = (0.005, self.starting_price)
            self.start_tag.set_text(f"{self.starting_price:.0f}")
            self.price_tag.set_text("")
            self.canvas.draw()
            return

        wicks = []
        bodies = []
        colors = []

        for i, candle in enumerate(visible):
            color = GREEN if candle.close >= candle.open else RED
            colors.append(color)

            wicks.append([(i, candle.low), (i, candle.high)])

            low_body = min(candle.open, candle.close)
            high_body = max(candle.open, candle.close)

            if high_body - low_body < 0.05:
                high_body = low_body + 0.05

            left = i - 0.32
            right = i + 0.32

            bodies.append([
                (left, low_body),
                (left, high_body),
                (right, high_body),
                (right, low_body),
            ])

        self.wicks.set_segments(wicks)
        self.wicks.set_colors(colors)

        self.bodies.set_verts(bodies)
        self.bodies.set_facecolors(colors)
        self.bodies.set_edgecolors(colors)

        self.update_indicator_data(list(range(n)), visible)

        lows = [c.low for c in visible]
        highs = [c.high for c in visible]

        y_values = lows + highs + [self.starting_price] + self.indicator_y_values
        price_min = min(y_values)
        price_max = max(y_values)
        pad = max((price_max - price_min) * 0.15, 10)

        self.ax.set_xlim(-1, n)
        self.ax.set_ylim(price_min - pad, price_max + pad)

        last = visible[-1]
        price_color = GREEN if last.close >= last.open else RED

        distance = last.close - self.starting_price
        distance_percent = (distance / self.starting_price) * 100

        self.start_line.set_ydata([self.starting_price, self.starting_price])
        self.start_tag.xy = (0.005, self.starting_price)
        self.start_tag.set_text(f"{self.starting_price:.0f}  {distance_percent:+.1f}%")

        self.price_line.set_ydata([last.close, last.close])
        self.price_line.set_color(price_color)

        self.price_tag.xy = (1, last.close)
        self.price_tag.set_text(f"{last.close:.2f}")
        self.price_tag.get_bbox_patch().set_facecolor(price_color)
        self.price_tag.get_bbox_patch().set_edgecolor(price_color)

        step = max(1, n // 8)
        ticks = list(range(0, n, step))
        labels = [self.format_time_label(visible[i].timestamp) for i in ticks]

        self.ax.set_xticks(ticks)
        self.ax.set_xticklabels(labels, color=MUTED, rotation=0)

        self.canvas.draw()

    def format_time_label(self, timestamp):
        tf_minutes = TIMEFRAMES.get(self.timeframe.get(), 1)

        if tf_minutes < 60:
            return timestamp.strftime("%H:%M")
        if tf_minutes < 1440:
            return timestamp.strftime("%d %H:%M")
        if tf_minutes < 10080:
            return timestamp.strftime("%m-%d")
        return timestamp.strftime("%Y-%m-%d")

    # -----------------------------
    # Indicators
    # -----------------------------
    def calculate_vwap_bands(self, candles):
        vwap = []
        upper_1 = []
        lower_1 = []
        upper_2 = []
        lower_2 = []
        upper_3 = []
        lower_3 = []

        cumulative_volume = 0.0
        cumulative_price_volume = 0.0
        cumulative_price2_volume = 0.0

        for candle in candles:
            typical_price = (candle.high + candle.low + candle.close) / 3.0
            volume = float(getattr(candle, "volume", 1))

            cumulative_volume += volume
            cumulative_price_volume += typical_price * volume
            cumulative_price2_volume += (typical_price ** 2) * volume

            if cumulative_volume <= 0:
                current_vwap = typical_price
                std_dev = 0.0
            else:
                current_vwap = cumulative_price_volume / cumulative_volume
                mean_square = cumulative_price2_volume / cumulative_volume
                variance = max(0.0, mean_square - current_vwap ** 2)
                std_dev = variance ** 0.5

            vwap.append(current_vwap)
            upper_1.append(current_vwap + std_dev)
            lower_1.append(current_vwap - std_dev)
            upper_2.append(current_vwap + 2 * std_dev)
            lower_2.append(current_vwap - 2 * std_dev)
            upper_3.append(current_vwap + 3 * std_dev)
            lower_3.append(current_vwap - 3 * std_dev)

        return vwap, upper_1, lower_1, upper_2, lower_2, upper_3, lower_3

    def band_polygon(self, x, upper, lower):
        if len(x) < 2:
            return []
        return [list(zip(x, upper)) + list(zip(reversed(x), reversed(lower)))]

    def clear_indicator_data(self):
        for line in (
            self.vwap_line,
            self.u1_line,
            self.l1_line,
            self.u2_line,
            self.l2_line,
            self.u3_line,
            self.l3_line,
        ):
            line.set_data([], [])

        self.band1_fill.set_verts([])
        self.band2_fill.set_verts([])
        self.band3_fill.set_verts([])
        self.indicator_y_values = []

    def update_indicator_data(self, x, candles):
        vwap_on = self.vwap_enabled.get()
        band1_on = self.band1_enabled.get()
        band2_on = self.band2_enabled.get()
        band3_on = self.band3_enabled.get()

        if not (vwap_on or band1_on or band2_on or band3_on):
            self.clear_indicator_data()
            return

        # VWAP is calculated from the full selected-timeframe history, not only the visible window.
        full_vwap, full_u1, full_l1, full_u2, full_l2, full_u3, full_l3 = self.calculate_vwap_bands(self.display_candles)

        start = self.view_start
        end = start + len(candles)

        vwap = full_vwap[start:end]
        u1 = full_u1[start:end]
        l1 = full_l1[start:end]
        u2 = full_u2[start:end]
        l2 = full_l2[start:end]
        u3 = full_u3[start:end]
        l3 = full_l3[start:end]

        self.indicator_y_values = []

        if vwap_on:
            self.vwap_line.set_data(x, vwap)
            self.indicator_y_values.extend(vwap)
        else:
            self.vwap_line.set_data([], [])

        if band1_on:
            self.u1_line.set_data(x, u1)
            self.l1_line.set_data(x, l1)
            self.band1_fill.set_verts(self.band_polygon(x, u1, l1))
            self.indicator_y_values.extend(u1)
            self.indicator_y_values.extend(l1)
        else:
            self.u1_line.set_data([], [])
            self.l1_line.set_data([], [])
            self.band1_fill.set_verts([])

        if band2_on:
            self.u2_line.set_data(x, u2)
            self.l2_line.set_data(x, l2)
            self.band2_fill.set_verts(self.band_polygon(x, u2, l2))
            self.indicator_y_values.extend(u2)
            self.indicator_y_values.extend(l2)
        else:
            self.u2_line.set_data([], [])
            self.l2_line.set_data([], [])
            self.band2_fill.set_verts([])

        if band3_on:
            self.u3_line.set_data(x, u3)
            self.l3_line.set_data(x, l3)
            self.band3_fill.set_verts(self.band_polygon(x, u3, l3))
            self.indicator_y_values.extend(u3)
            self.indicator_y_values.extend(l3)
        else:
            self.u3_line.set_data([], [])
            self.l3_line.set_data([], [])
            self.band3_fill.set_verts([])

    # -----------------------------
    # Chart movement
    # -----------------------------
    def on_chart_press(self, event):
        if event.inaxes != self.ax or event.button != 1 or event.xdata is None:
            return

        self.pan_active = True
        self.pan_start_x = event.xdata
        self.pan_start_view = self.view_start

    def on_chart_release(self, event):
        self.pan_active = False
        self.pan_start_x = None

    def on_chart_motion(self, event):
        if not self.pan_active or event.inaxes != self.ax or event.xdata is None:
            return

        total = len(self.display_candles)
        count = int(self.visible_bars.get())

        if total <= count:
            return

        delta = int(round(self.pan_start_x - event.xdata))
        new_start = self.pan_start_view + delta
        max_start = max(0, total - count)

        self.view_start = max(0, min(new_start, max_start))
        self.auto_follow = self.view_start >= max_start

        self.update_chart()
        self.update_stats()

    def on_chart_scroll(self, event):
        if event.inaxes != self.ax:
            return

        current = int(self.visible_bars.get())

        if event.button == "up":
            new_value = int(current * 0.85)
        else:
            new_value = int(current * 1.15)

        new_value = max(20, min(300, new_value))
        self.visible_bars.set(new_value)

        if len(self.display_candles) > new_value:
            self.auto_follow = False
            self.view_start = max(0, min(self.view_start, len(self.display_candles) - new_value))

        self.update_chart()
        self.update_stats()

    def reset_view(self):
        self.auto_follow = True
        self.update_chart()
        self.update_stats()

    # -----------------------------
    # Market logic
    # -----------------------------
    def make_candle(self):
        dice_scale = float(self.dice_scale.get())
        bias = int(self.coin_bias.get())
        up_probability = max(0.05, min(0.95, 0.50 + bias / 100))

        open_price = self.price
        current = open_price
        high = open_price
        low = open_price
        volume_score = 0
        roll_lines = []

        for move_number in range(1, 6):
            is_up = random.random() < up_probability
            direction = 1 if is_up else -1
            dice = random.randint(1, 6)
            movement = direction * dice * dice_scale

            current = max(1, current + movement)
            high = max(high, current)
            low = min(low, current)
            volume_score += dice

            arrow = "UP  " if is_up else "DOWN"
            sign = "+" if movement >= 0 else ""
            roll_lines.append(f"{move_number}: {arrow} | dice {dice} | {sign}{movement:.2f}")

        self.price = current

        volume = int(random.randint(700, 1600) + volume_score * random.randint(90, 220))

        candle = Candle(
            index=self.next_index,
            timestamp=self.start_time + timedelta(minutes=self.next_index),
            open=round(open_price, 2),
            high=round(high, 2),
            low=round(low, 2),
            close=round(current, 2),
            volume=volume,
            rolls="\n".join(roll_lines),
        )

        self.next_index += 1
        return candle

    def trim_candles(self):
        limit = 5000
        if len(self.candles) > limit:
            removed = len(self.candles) - limit
            self.candles = self.candles[-limit:]
            self.view_start = max(0, self.view_start - removed)

            # Re-index retained candles so timeframe buckets stay stable.
            for i, candle in enumerate(self.candles):
                candle.index = i
                candle.timestamp = self.start_time + timedelta(minutes=i)
            self.next_index = len(self.candles)

    def step_once(self):
        was_following = self.auto_follow

        self.candles.append(self.make_candle())
        self.trim_candles()

        if was_following:
            self.auto_follow = True

        self.update_chart()
        self.update_stats()

    def generate_many(self, amount):
        was_following = self.auto_follow

        for _ in range(amount):
            self.candles.append(self.make_candle())

        self.trim_candles()

        if was_following:
            self.auto_follow = True

        self.update_chart()
        self.update_stats()

    def loop(self):
        if not self.running:
            return

        self.step_once()
        delay = max(20, min(int(self.speed_ms.get()), 1000))
        self.after_id = self.root.after(delay, self.loop)

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        if self.running:
            return

        self.running = True
        self.toggle_button.config(text="STOP", bg=RED, activebackground=RED)
        self.status_label.config(text="● LIVE", fg=GREEN)
        self.loop()

    def stop(self):
        self.running = False
        self.toggle_button.config(text="START", bg=GREEN, activebackground=GREEN)
        self.status_label.config(text="● STOPPED", fg=YELLOW)

        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def reset(self):
        self.stop()
        self.price = self.starting_price
        self.start_time = datetime.now().replace(second=0, microsecond=0)
        self.next_index = 0
        self.candles.clear()
        self.display_candles.clear()
        self.view_start = 0
        self.auto_follow = True
        self.update_chart()
        self.update_stats()

    # -----------------------------
    # Stats / export
    # -----------------------------
    def update_stats(self):
        change = ((self.price - self.starting_price) / self.starting_price) * 100

        self.price_card.config(text=f"{self.price:.2f}")
        self.change_card.config(
            text=f"{change:+.2f}%",
            fg=GREEN if change >= 0 else RED,
        )
        self.bars_card.config(text=str(len(self.display_candles)))
        self.view_card.config(text="LIVE" if self.auto_follow else "PAST", fg=YELLOW if self.auto_follow else BLUE)

        if not self.candles:
            self.rolls_label.config(text="-")
        else:
            self.rolls_label.config(text=self.candles[-1].rolls)

        up_chance = max(0.05, min(0.95, 0.50 + int(self.coin_bias.get()) / 100)) * 100
        visible = self.get_visible_slice()

        if visible:
            visible_range = f"{self.format_time_label(visible[0].timestamp)} - {self.format_time_label(visible[-1].timestamp)}"
        else:
            visible_range = "-"

        distance = self.price - self.starting_price
        distance_percent = (distance / self.starting_price) * 100

        info = (
            f"Timeframe: {self.timeframe.get()}\n"
            f"1m candles: {len(self.candles)}\n"
            f"Bars shown: {len(self.display_candles)}\n"
            f"Start: {self.starting_price:.2f}\n"
            f"Current: {self.price:.2f}\n"
            f"Distance: {distance:+.2f} ({distance_percent:+.2f}%)\n"
            f"Up/Down: {up_chance:.1f}% / {100 - up_chance:.1f}%\n"
            f"Scale: {float(self.dice_scale.get()):.2f}\n"
            f"View: {'Live' if self.auto_follow else 'Past'}\n"
            f"Range: {visible_range}"
        )
        self.info_label.config(text=info)

    def export_csv(self):
        if not self.candles:
            messagebox.showwarning("No Data", "There are no candles to export yet.")
            return

        path = filedialog.asksaveasfilename(
            title="Export Candle Data",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )

        if not path:
            return

        displayed = self.aggregate_candles()

        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "timeframe",
                "index",
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "rolls",
            ])

            for candle in displayed:
                writer.writerow([
                    self.timeframe.get(),
                    candle.index,
                    candle.timestamp.isoformat(timespec="minutes"),
                    candle.open,
                    candle.high,
                    candle.low,
                    candle.close,
                    candle.volume,
                    candle.rolls.replace("\n", " | "),
                ])

        messagebox.showinfo("Export Complete", f"Saved {self.timeframe.get()} candle data to:\n{path}")


def main():
    root = tk.Tk()
    TopiumDiceMarket(root)
    root.mainloop()


if __name__ == "__main__":
    main()
