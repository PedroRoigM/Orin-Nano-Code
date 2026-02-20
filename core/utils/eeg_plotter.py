# src/utils/eeg_plotter.py
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from collections import deque
import time

class EEGPlotter:
    """
    Real-time visualization of raw EEG band powers and eSense metrics
    from NeuroSky MindWave Mobile 2.
    
    EEG bands: delta, theta, lowAlpha, highAlpha, lowBeta, highBeta, lowGamma, midGamma
    eSense:    attention, meditation (0-100 normalized by device)
    """

    BAND_KEYS = ["delta", "theta", "lowAlpha", "highAlpha", "lowBeta", "highBeta", "lowGamma", "midGamma"]
    ESENSE_KEYS = ["attention", "meditation"]
    WINDOW = 60  # samples in rolling window

    # Colors per band for visual distinction
    BAND_COLORS = ["#4C72B0", "#55A868", "#C44E52", "#8172B2",
                   "#CCB974", "#64B5CD", "#E08080", "#80C080"]
    ESENSE_COLORS = ["#FF6B35", "#A8DADC"]

    def __init__(self):
        plt.ion()
        self.fig = plt.figure(figsize=(16, 9))
        self.fig.suptitle("NeuroSky MindWave — Raw EEG Values", fontsize=13, fontweight='bold')
        gs = gridspec.GridSpec(3, 2, figure=self.fig, hspace=0.45, wspace=0.35)

        # Top-left: bar chart of current EEG band powers (log scale, raw values are huge)
        self.ax_bar = self.fig.add_subplot(gs[0, 0])
        self.ax_bar.set_title("Band Powers (current, log scale)")
        self.ax_bar.set_yscale("log")
        self._bars = self.ax_bar.bar(self.BAND_KEYS, [1]*8, color=self.BAND_COLORS)
        self.ax_bar.set_xticklabels(self.BAND_KEYS, rotation=30, ha='right', fontsize=8)
        self.ax_bar.set_ylabel("Raw power")

        # Top-right: eSense bar (0-100)
        self.ax_esense = self.fig.add_subplot(gs[0, 1])
        self.ax_esense.set_title("eSense Metrics (0–100)")
        self._esense_bars = self.ax_esense.bar(self.ESENSE_KEYS, [0, 0], color=self.ESENSE_COLORS)
        self.ax_esense.set_ylim(0, 100)
        self.ax_esense.axhline(50, color='gray', linestyle='--', linewidth=0.8, alpha=0.6)
        for bar in self._esense_bars:
            bar.set_edgecolor('black')

        # Middle row: rolling time series for each EEG band (normalized 0-1 per band for comparison)
        self.ax_bands = self.fig.add_subplot(gs[1, :])
        self.ax_bands.set_title("EEG Band Powers — Rolling window (normalized per band, for trend comparison)")
        self.ax_bands.set_ylim(0, 1.05)
        self.ax_bands.set_ylabel("Normalized (0–1 per band)")
        self.ax_bands.set_xlabel("Samples")
        self._band_history = {k: deque([0.0]*self.WINDOW, maxlen=self.WINDOW) for k in self.BAND_KEYS}
        self._band_mins = {k: 1e10 for k in self.BAND_KEYS}
        self._band_maxs = {k: 1.0  for k in self.BAND_KEYS}
        self._band_lines = {}
        x = np.arange(self.WINDOW)
        for i, key in enumerate(self.BAND_KEYS):
            line, = self.ax_bands.plot(x, list(self._band_history[key]),
                                       label=key, color=self.BAND_COLORS[i], linewidth=1.2)
            self._band_lines[key] = line
        self.ax_bands.legend(loc='upper left', ncol=4, fontsize=7)

        # Bottom row: attention & meditation time series (raw 0-100)
        self.ax_esense_ts = self.fig.add_subplot(gs[2, :])
        self.ax_esense_ts.set_title("Attention & Meditation — Rolling window")
        self.ax_esense_ts.set_ylim(0, 100)
        self.ax_esense_ts.set_ylabel("eSense value")
        self.ax_esense_ts.set_xlabel("Samples")
        self.ax_esense_ts.axhline(50, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
        self._esense_history = {k: deque([0.0]*self.WINDOW, maxlen=self.WINDOW) for k in self.ESENSE_KEYS}
        self._esense_lines = {}
        for i, key in enumerate(self.ESENSE_KEYS):
            line, = self.ax_esense_ts.plot(x, list(self._esense_history[key]),
                                            label=key, color=self.ESENSE_COLORS[i], linewidth=1.5)
            self._esense_lines[key] = line
        self.ax_esense_ts.legend(loc='upper left', fontsize=8)

        plt.tight_layout()
        plt.show(block=False)
        self._last_update = time.time()

    def update(self, eeg_values: dict):
        """
        Call this every iteration with the raw eeg_values dict
        (merged eegPower + eSense).
        """
        # --- Bar chart: raw band powers ---
        band_vals = [max(eeg_values.get(k, 1), 1) for k in self.BAND_KEYS]
        for bar, val in zip(self._bars, band_vals):
            bar.set_height(val)
        # Auto-scale log axis
        self.ax_bar.set_ylim(bottom=1, top=max(band_vals) * 2)

        # --- eSense bars ---
        for bar, key in zip(self._esense_bars, self.ESENSE_KEYS):
            bar.set_height(eeg_values.get(key, 0))

        # --- Rolling normalized band history ---
        for key in self.BAND_KEYS:
            val = eeg_values.get(key, 0)
            # Update running min/max for normalization (adaptive)
            if val < self._band_mins[key]:
                self._band_mins[key] = val
            if val > self._band_maxs[key]:
                self._band_maxs[key] = val
            span = self._band_maxs[key] - self._band_mins[key]
            norm = (val - self._band_mins[key]) / span if span > 0 else 0.0
            self._band_history[key].append(norm)
            self._band_lines[key].set_ydata(list(self._band_history[key]))

        # --- eSense rolling time series ---
        for key in self.ESENSE_KEYS:
            self._esense_history[key].append(eeg_values.get(key, 0))
            self._esense_lines[key].set_ydata(list(self._esense_history[key]))

        self.fig.canvas.draw_idle()
        plt.pause(0.001)  # non-blocking flush