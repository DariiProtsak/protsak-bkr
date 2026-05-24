import time
import threading
import numpy as np
import customtkinter as ctk
import matplotlib.patches as mpatches
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from queue import Empty

from core.preprocessor import extract_amplitudes
from core.feature_extractor import FeatureExtractor, SCALER_PATH, PCA_PATH
from core.classifier import Classifier, class_color
from core.udp_pinger import UdpPinger

_BG   = "#1e1e2e"
_DARK = "#2b2b2b"

class ScreenMonitor(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color="transparent")
        self.app = app
        self._running = False
        self._history: list[tuple[int, str]] = []
        self._extractor = FeatureExtractor()
        self._clf = Classifier()
        self._pinger: UdpPinger | None = None
        self._build()

    @property
    def _class_colors(self) -> dict[str, str]:
        return {cls: class_color(i) for i, cls in enumerate(self._clf.classes)}

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
        self._mpl_canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._mpl_canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=4)

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
                  for cls, c in self._class_colors.items()]
        self._ax_time.legend(handles=legend, loc="upper right",
                             fontsize=7, facecolor="#333", labelcolor="white")
        self._mpl_canvas.draw()

    def on_show(self):
        self._block.delete(0, "end")
        self._block.insert(0, str(self.app.cfg.get("monitor_block_sec", 30)))

    def _stop_pinger(self):
        if self._pinger:
            self._pinger.stop()
            self._pinger = None

    def _toggle(self):
        if self._running:
            self._running = False
            self._stop_pinger()
            self._toggle_btn.configure(text="▶  Старт")
            self._show_stats()
        else:
            self._start()

    def _start(self):
        try:
            block_sec = int(self._block.get())
        except ValueError:
            return

        if not Classifier.model_exists() or not FeatureExtractor.artifacts_exist():
            self._stats_lbl.configure(
                text="Немає моделі. Спочатку зберіть дані і натренуйте модель.",
                text_color="orange")
            return

        try:
            self._extractor.load()
            self._clf.load()
        except Exception as e:
            self._stats_lbl.configure(text=f"Помилка завантаження моделі: {e}",
                                       text_color="red")
            return

        expected_n = int(self._extractor.scaler.n_features_in_)

        self.app.cfg["monitor_block_sec"] = block_sec
        self.app.save_config()

        self._running = True
        self._history.clear()
        self._stats_lbl.configure(text="Очікую CSI пакети…", text_color="gray")
        self._result_lbl.configure(text="")
        self._toggle_btn.configure(text="■  Стоп")

        # Flush stale packets before starting
        _q = self.app.serial.queue
        while not _q.empty():
            try: _q.get_nowait()
            except Exception: break

        self._pinger = UdpPinger(rate=500.0, target_ip=self.app.serial.esp32_ip)
        self._pinger.start()

        def task():
            while self._running:
                try:
                    # Check serial port is alive
                    if not self.app.serial.is_connected:
                        self.after(0, lambda: self._stats_lbl.configure(
                            text="COM порт відключено — підключи ESP32",
                            text_color="red"))
                        time.sleep(2)
                        continue

                    packets: list[list[float]] = []
                    raw_count = 0
                    skipped   = 0
                    deadline = time.time() + block_sec
                    last_ui  = time.time()
                    while time.time() < deadline and self._running:
                        remaining = max(0, int(deadline - time.time()))
                        now = time.time()
                        if now - last_ui >= 1.0:
                            last_ui = now
                            _r, _p, _j, _s = remaining, len(packets), raw_count, skipped
                            self.after(0, lambda r=_r, p=_p, j=_j, s=_s: self._stats_lbl.configure(
                                text=f"Збираю… {r}с  CSI:{p}  JSON:{j}" + (f"  skip:{s}" if s else ""),
                                text_color="gray"))
                        try:
                            pkt  = self.app.serial.queue.get(timeout=0.2)
                            raw_count += 1
                            amps = extract_amplitudes(pkt)
                            if amps:
                                if len(amps) == expected_n:
                                    packets.append(amps)
                                else:
                                    skipped += 1
                        except Exception:
                            pass
                    if packets:
                        msg   = f"CSI: {len(packets)}  JSON: {raw_count}" + (f"  skip:{skipped}" if skipped else "")
                        color = "gray"
                    elif skipped > 0:
                        msg   = f"JSON: {raw_count}, CSI wrong size ({skipped} пакетів з ≠{expected_n} субнесучих) — перетренуй модель"
                        color = "orange"
                    elif raw_count > 0:
                        msg   = f"JSON: {raw_count}, CSI: 0 — перевір формат даних"
                        color = "orange"
                    else:
                        msg   = "0 пакетів — ESP32 в мережі? (перевір LCD)"
                        color = "red"
                    _msg, _color = msg, color
                    self.after(0, lambda m=_msg, c=_color: self._stats_lbl.configure(
                        text=m, text_color=c))

                    if not packets or not self._running:
                        continue

                    X      = np.array(packets, dtype=np.float32)
                    X_feat = self._extractor.transform(X)
                    cls, prob = self._clf.predict(X_feat)
                    X_mean = X.mean(axis=0)
                    self._history.append((len(self._history), cls))
                    self.after(0, self._update_ui, X_mean, cls, prob)
                except Exception as e:
                    _e = str(e)
                    self.after(0, lambda err=_e: self._stats_lbl.configure(
                        text=f"Помилка блоку: {err}", text_color="red"))

        threading.Thread(target=task, daemon=True).start()

    def _update_ui(self, amplitudes: np.ndarray, cls: str, prob: float):
        color = self._class_colors.get(cls, "white")
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
            self._ax_time.axvspan(t, t + 1, color=self._class_colors.get(c, "gray"), alpha=0.85)
        self._ax_time.set_xlim(0, max(len(self._history) + 1, 10))
        self._ax_time.set_ylim(0, 1)
        self._ax_time.set_yticks([])
        self._ax_time.set_title("Часова шкала класів", color="white", fontsize=9)
        self._ax_time.set_xlabel("Блок #", color="gray", fontsize=8)
        legend = [mpatches.Patch(color=c, label=cls)
                  for cls, c in self._class_colors.items()]
        self._ax_time.legend(handles=legend, loc="upper right",
                             fontsize=7, facecolor="#333", labelcolor="white")

        self._fig.tight_layout(pad=1.8)
        self._mpl_canvas.draw()

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
        self._stop_pinger()
        self._toggle_btn.configure(text="▶  Старт")
        self.app.show("menu")
