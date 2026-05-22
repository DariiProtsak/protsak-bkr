import os
import json
import time
import threading
import numpy as np
import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core.preprocessor import extract_amplitudes
from core.feature_extractor import FeatureExtractor
from core.classifier import Classifier, CLASSES

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(_BASE, "data", "dataset.jsonl")

class ScreenCollect(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color="transparent")
        self.app = app
        self._collecting = False
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Навчання моделі",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(16, 4))

        # ── Крок 1 ──────────────────────────────────────────────────────────
        step1 = ctk.CTkFrame(self)
        step1.pack(fill="x", padx=28, pady=4)
        ctk.CTkLabel(step1, text="Крок 1: Збір навчальних даних",
                     font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=5, sticky="w", padx=10, pady=(8, 2))

        ctk.CTkLabel(step1, text="Клас:").grid(row=1, column=0, padx=10, pady=6, sticky="w")
        self._class_var = ctk.StringVar(value=CLASSES[0])
        ctk.CTkSegmentedButton(step1, values=CLASSES, variable=self._class_var,
                               width=320).grid(row=1, column=1, padx=10, pady=6, sticky="w")

        ctk.CTkLabel(step1, text="Тривалість (с):").grid(row=1, column=2, padx=(20, 4))
        self._dur = ctk.CTkEntry(step1, width=64)
        self._dur.insert(0, str(self.app.cfg.get("collect_duration_sec", 60)))
        self._dur.grid(row=1, column=3, padx=4, pady=6)

        self._progress = ctk.CTkProgressBar(step1, width=380)
        self._progress.set(0)
        self._progress.grid(row=2, column=0, columnspan=4, padx=10, pady=4, sticky="ew")
        self._counter = ctk.CTkLabel(step1, text="0 пакетів", width=80)
        self._counter.grid(row=2, column=4, padx=8)

        self._collect_btn = ctk.CTkButton(step1, text="▶  Старт збору",
                                          width=160, command=self._toggle_collect)
        self._collect_btn.grid(row=3, column=0, padx=10, pady=8, sticky="w")

        # ── Статус датасету ──────────────────────────────────────────────────
        ds = ctk.CTkFrame(self)
        ds.pack(fill="x", padx=28, pady=2)
        ctk.CTkLabel(ds, text="Датасет:", font=ctk.CTkFont(weight="bold")).pack(
            side="left", padx=10, pady=6)
        self._ds_labels: dict[str, ctk.CTkLabel] = {}
        for cls in CLASSES:
            lbl = ctk.CTkLabel(ds, text=f"{cls}: 0")
            lbl.pack(side="left", padx=16)
            self._ds_labels[cls] = lbl
        ctk.CTkButton(ds, text="Очистити", width=110, fg_color="gray30",
                      command=self._clear_dataset).pack(side="right", padx=10)

        # ── Крок 2 ──────────────────────────────────────────────────────────
        step2 = ctk.CTkFrame(self)
        step2.pack(fill="x", padx=28, pady=4)
        ctk.CTkLabel(step2, text="Крок 2: Тренування моделі",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 2))
        self._train_btn = ctk.CTkButton(step2, text="Тренувати модель",
                                        width=200, height=40, command=self._train)
        self._train_btn.pack(anchor="w", padx=10, pady=4)
        self._train_status = ctk.CTkLabel(step2, text="", text_color="gray")
        self._train_status.pack(anchor="w", padx=10, pady=(0, 6))

        # ── Результати ──────────────────────────────────────────────────────
        self._results = ctk.CTkScrollableFrame(self, height=180)
        self._results.pack(fill="x", padx=28, pady=4)

        ctk.CTkButton(self, text="← Меню", width=120,
                      fg_color="transparent", border_width=1,
                      command=lambda: self.app.show("menu")).pack(pady=6)

    def on_show(self):
        self._refresh_ds_ui()
        self._refresh_train_btn()

    # ── Збір даних ────────────────────────────────────────────────────────────
    def _toggle_collect(self):
        if self._collecting:
            self._collecting = False
            self._collect_btn.configure(text="▶  Старт збору")
        else:
            self._start_collect()

    def _start_collect(self):
        try:
            duration = int(self._dur.get())
        except ValueError:
            return
        label = self._class_var.get()
        self.app.cfg["collect_duration_sec"] = duration
        self.app.save_config()

        self._collecting = True
        self._collect_btn.configure(text="■  Стоп")
        self._progress.set(0)
        self._counter.configure(text="0 пакетів")

        def task():
            os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
            count = 0
            start = time.time()
            with open(DATASET_PATH, "a", encoding="utf-8") as f:
                while self._collecting:
                    elapsed = time.time() - start
                    if elapsed >= duration:
                        break
                    try:
                        pkt = self.app.serial.queue.get(timeout=0.5)
                    except Exception:
                        continue
                    pkt["label"] = label
                    f.write(json.dumps(pkt, ensure_ascii=False) + "\n")
                    count += 1
                    self.after(0, self._update_progress, min(elapsed / duration, 1.0), count)
            self.after(0, self._on_collect_done)

        threading.Thread(target=task, daemon=True).start()

    def _update_progress(self, pct: float, count: int):
        self._progress.set(pct)
        self._counter.configure(text=f"{count} пакетів")

    def _on_collect_done(self):
        self._collecting = False
        self._collect_btn.configure(text="▶  Старт збору")
        self._progress.set(1.0)
        self._refresh_ds_ui()
        self._refresh_train_btn()

    # ── Датасет ───────────────────────────────────────────────────────────────
    def _count_dataset(self) -> dict[str, int]:
        counts = {cls: 0 for cls in CLASSES}
        if not os.path.exists(DATASET_PATH):
            return counts
        try:
            with open(DATASET_PATH, encoding="utf-8") as f:
                for line in f:
                    try:
                        lbl = json.loads(line).get("label")
                        if lbl in counts:
                            counts[lbl] += 1
                    except Exception:
                        pass
        except Exception:
            pass
        return counts

    def _refresh_ds_ui(self):
        counts = self._count_dataset()
        for cls, count in counts.items():
            color = "green" if count >= 1500 else ("orange" if count > 0 else "gray")
            self._ds_labels[cls].configure(text=f"{cls}: {count}", text_color=color)

    def _refresh_train_btn(self):
        counts = self._count_dataset()
        ready = all(counts[cls] > 0 for cls in CLASSES)
        self._train_btn.configure(state="normal" if ready else "disabled")

    def _clear_dataset(self):
        if os.path.exists(DATASET_PATH):
            os.remove(DATASET_PATH)
        self._refresh_ds_ui()
        self._refresh_train_btn()

    # ── Тренування ───────────────────────────────────────────────────────────
    def _train(self):
        self._train_btn.configure(state="disabled")
        self._train_status.configure(text="Тренування…", text_color="gray")
        self.update()

        def task():
            try:
                packets, labels = [], []
                with open(DATASET_PATH, encoding="utf-8") as f:
                    for line in f:
                        try:
                            pkt = json.loads(line)
                            amps = extract_amplitudes(pkt)
                            if amps and pkt.get("label") in CLASSES:
                                packets.append(amps)
                                labels.append(CLASSES.index(pkt["label"]))
                        except Exception:
                            pass

                X = np.array(packets, dtype=np.float32)
                y = np.array(labels)

                extractor = FeatureExtractor()
                X_t = extractor.fit_transform(X)
                extractor.save()

                clf = Classifier()
                result = clf.train(X_t, y)
                clf.save()
                result.explained_variance_pct = extractor.explained_variance_pct

                self.after(0, self._show_results, result)
            except Exception as e:
                self.after(0, lambda: (
                    self._train_status.configure(text=f"Помилка: {e}", text_color="red"),
                    self._train_btn.configure(state="normal"),
                ))

        threading.Thread(target=task, daemon=True).start()

    def _show_results(self, result):
        self._train_status.configure(text="Модель збережена!", text_color="green")
        self._train_btn.configure(state="normal")

        for w in self._results.winfo_children():
            w.destroy()

        # Таблиця метрик
        tbl = ctk.CTkFrame(self._results)
        tbl.pack(fill="x", pady=4)
        for col, h in enumerate(["Модель", "Accuracy", "Precision", "Recall", "F1-macro"]):
            ctk.CTkLabel(tbl, text=h, font=ctk.CTkFont(weight="bold"),
                         width=110).grid(row=0, column=col, padx=4, pady=3)

        rows = [
            ("kNN (k=5)", result.knn_accuracy, result.knn_report, False),
            ("SVM (RBF)", result.svm_accuracy, result.svm_report, True),
        ]
        for r, (name, acc, rep, is_svm) in enumerate(rows, 1):
            macro = rep.get("macro avg", {})
            f1    = macro.get("f1-score", 0.0)
            vals  = [
                (name, "white"),
                (f"{acc:.1%}", "green" if (is_svm and acc >= 0.769) else "white"),
                (f"{macro.get('precision', 0):.3f}", "white"),
                (f"{macro.get('recall', 0):.3f}", "white"),
                (f"{f1:.3f}", "green" if (is_svm and f1 >= 0.75) else "white"),
            ]
            for col, (val, color) in enumerate(vals):
                ctk.CTkLabel(tbl, text=val, text_color=color, width=110).grid(
                    row=r, column=col, padx=4, pady=2)

        ev_color = "green" if result.explained_variance_pct >= 93.2 else "white"
        ctk.CTkLabel(self._results,
                     text=f"PCA-10 пояснена дисперсія: {result.explained_variance_pct:.1f}%",
                     text_color=ev_color).pack(pady=4)

        # Confusion matrix SVM
        fig = Figure(figsize=(4.2, 2.8), dpi=80, facecolor="#2b2b2b")
        ax  = fig.add_subplot(111)
        ax.set_facecolor("#2b2b2b")
        ax.imshow(result.svm_cm, interpolation="nearest", cmap="Blues")
        ax.set_title("SVM Confusion Matrix", color="white", fontsize=9)
        ax.set_xticks(range(len(CLASSES)))
        ax.set_yticks(range(len(CLASSES)))
        ax.set_xticklabels(CLASSES, rotation=12, color="white", fontsize=8)
        ax.set_yticklabels(CLASSES, color="white", fontsize=8)
        for i in range(len(CLASSES)):
            for j in range(len(CLASSES)):
                ax.text(j, i, str(result.svm_cm[i, j]),
                        ha="center", va="center", color="white", fontsize=9)
        fig.tight_layout()
        FigureCanvasTkAgg(fig, master=self._results).get_tk_widget().pack(pady=4)
