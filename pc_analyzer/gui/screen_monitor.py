import time
import threading
import numpy as np
import customtkinter as ctk
import matplotlib.patches as mpatches
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from queue import Empty

from core.preprocessor import extract_amplitudes
from core.feature_extractor import FeatureExtractor
from core.classifier import Classifier, CLASSES

_BG   = "#1e1e2e"
_DARK = "#2b2b2b"
CLASS_COLORS = {"Порожньо": "#4caf50", "Стілець": "#ffc107", "Людина": "#f44336"}

class ScreenMonitor(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color="transparent")
        self.app = app
        self._running = False
        self._history: list[tuple[int, str]] = []
        self._extractor = FeatureExtractor()
        self._clf = Classifier()
        self._build()

    def _build(self):
        # ── Верхня панель ────────────────────────────────────────────────────
        bar = ctk.CTkFrame(self, height=54)
        bar.pack(fill="x", padx=20, pady=(12, 4))
        bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="Моніторинг",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=14)
        ctk.CTkLabel(bar, text="Блок (с):").pack(side="left", padx=(18, 4))
        self._block = ctk.CTkEntry(bar, width=58)
        self._block.pack(side="left")
        self._toggle_btn = ctk.CTkButton(bar, text="▶  Старт",
                                         width=120, command=self._toggle)
        self._toggle_btn.pack(side="left", padx=12)
        self._result_lbl = ctk.CTkLabel(bar, text="",
                                        font=ctk.CTkFont(size=16, weight="bold"), width=220)
        self._result_lbl.pack(side="left", padx=10)
        ctk.CTkButton(bar, text="← Меню", width=100,
                      fg_color="transparent", border_width=1,
                      command=self._back).pack(side="right", padx=12)

        # ── Matplotlib ───────────────────────────────────────────────────────
        self._fig = Figure(figsize=(8.6, 4.6), dpi=88, facecolor=_DARK)
        self._ax_amp  = self._fig.add_subplot(2, 1, 1)
        self._ax_time = self._fig.add_subplot(2, 1, 2)
        self._fig.tight_layout(pad=1.8)
        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=4)

        self._stats_lbl = ctk.CTkLabel(self, text="", text_color="gray",
                                       font=ctk.CTkFont(size=12))
        self._stats_lbl.pack(pady=4)

        self._draw_empty()

    def _draw_empty(self):
        for ax in (self._ax_amp, self._ax_time):
            ax.set_facecolor(_BG)
            ax.tick_params(colors="white")
            for spine in ax.spines.values():
                spine.set_edgecolor("#444")
        self._ax_amp.set_title("Амплітуди субнесучих", color="white", fontsize=9)
        self._ax_amp.set_xlabel("Субнесуча #", color="gray", fontsize=8)
        self._ax_amp.set_ylabel("Амплітуда", color="gray", fontsize=8)
        self._ax_time.set_title("Часова шкала класів", color="white", fontsize=9)
        self._ax_time.set_xlabel("Блок #", color="gray", fontsize=8)
        self._ax_time.set_yticks([])
        legend = [mpatches.Patch(color=c, label=cls)
                  for cls, c in CLASS_COLORS.items()]
        self._ax_time.legend(handles=legend, loc="upper right",
                             fontsize=7, facecolor="#333", labelcolor="white")
        self._canvas.draw()

    def on_show(self):
        self._block.delete(0, "end")
        self._block.insert(0, str(self.app.cfg.get("monitor_block_sec", 30)))

    def _toggle(self):
        if self._running:
            self._running = False
            self._toggle_btn.configure(text="▶  Старт")
            self._show_stats()
        else:
            self._start()

    def _start(self):
        try:
            block_sec = int(self._block.get())
        except ValueError:
            return
        self.app.cfg["monitor_block_sec"] = block_sec
        self.app.save_config()

        self._extractor.load()
        self._clf.load()
        self._running = True
        self._history.clear()
        self._stats_lbl.configure(text="")
        self._result_lbl.configure(text="")
        self._toggle_btn.configure(text="■  Стоп")

        def task():
            while self._running:
                packets: list[list[float]] = []
                deadline = time.time() + block_sec
                while time.time() < deadline and self._running:
                    try:
                        pkt  = self.app.serial.queue.get(timeout=0.2)
                        amps = extract_amplitudes(pkt)
                        if amps:
                            packets.append(amps)
                    except Empty:
                        pass

                if not packets or not self._running:
                    continue

                X_mean = np.array(packets, dtype=np.float32).mean(axis=0)
                X_feat = self._extractor.transform(X_mean.reshape(1, -1))
                cls, prob = self._clf.predict(X_feat)
                self._history.append((len(self._history), cls))
                self.after(0, self._update_ui, X_mean, cls, prob)

        threading.Thread(target=task, daemon=True).start()

    def _update_ui(self, amplitudes: np.ndarray, cls: str, prob: float):
        color = CLASS_COLORS.get(cls, "white")
        self._result_lbl.configure(text=f"{cls}  {prob:.0%}", text_color=color)

        # Амплітуди
        self._ax_amp.cla()
        self._ax_amp.set_facecolor(_BG)
        self._ax_amp.tick_params(colors="white")
        for spine in self._ax_amp.spines.values():
            spine.set_edgecolor("#444")
        self._ax_amp.plot(amplitudes, color="#4fc3f7", linewidth=0.9)
        self._ax_amp.set_title("Амплітуди субнесучих", color="white", fontsize=9)
        self._ax_amp.set_xlabel("Субнесуча #", color="gray", fontsize=8)
        self._ax_amp.set_ylabel("Амплітуда", color="gray", fontsize=8)

        # Часова шкала
        self._ax_time.cla()
        self._ax_time.set_facecolor(_BG)
        self._ax_time.tick_params(colors="white")
        for spine in self._ax_time.spines.values():
            spine.set_edgecolor("#444")
        for t, c in self._history:
            self._ax_time.axvspan(t, t + 1, color=CLASS_COLORS.get(c, "gray"), alpha=0.85)
        self._ax_time.set_xlim(0, max(len(self._history) + 1, 10))
        self._ax_time.set_ylim(0, 1)
        self._ax_time.set_yticks([])
        self._ax_time.set_title("Часова шкала класів", color="white", fontsize=9)
        self._ax_time.set_xlabel("Блок #", color="gray", fontsize=8)
        legend = [mpatches.Patch(color=c, label=cls)
                  for cls, c in CLASS_COLORS.items()]
        self._ax_time.legend(handles=legend, loc="upper right",
                             fontsize=7, facecolor="#333", labelcolor="white")

        self._fig.tight_layout(pad=1.8)
        self._canvas.draw()

    def _show_stats(self):
        if not self._history:
            return
        counts: dict[str, int] = {}
        for _, cls in self._history:
            counts[cls] = counts.get(cls, 0) + 1
        total = len(self._history)
        parts = [f"{cls}: {cnt/total:.0%}" for cls, cnt in counts.items()]
        self._stats_lbl.configure(text="Підсумок сесії:  " + "   |   ".join(parts))

    def _back(self):
        self._running = False
        self._toggle_btn.configure(text="▶  Старт")
        self.app.show("menu")
