import os
import json
import time
import threading
import subprocess
import numpy as np
import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core.preprocessor import extract_amplitudes
from core.feature_extractor import FeatureExtractor
from core.classifier import Classifier, class_color
from core.udp_pinger import UdpPinger
from core.analytics import (compute_los_reference, compute_class_stats,
                              compute_separability, train_rssi_baselines, W_RSSI)

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(_BASE, "data", "dataset.jsonl")


class ScreenCollect(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app, fg_color="transparent")
        self.app = app
        self._collecting = False
        self._pinger: UdpPinger | None = None
        self._class_entries: list[ctk.CTkEntry] = []
        self._ds_labels: dict[str, ctk.CTkLabel] = {}
        self._build()

    @property
    def _classes(self) -> list[str]:
        return self.app.cfg.get("classes", ["Клас 1", "Клас 2"])

    def _build(self):
        ctk.CTkLabel(self, text="Навчання моделі",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(16, 4))

        # ── Редактор класів ──────────────────────────────────────────────────
        ce = ctk.CTkFrame(self)
        ce.pack(fill="x", padx=28, pady=4)
        ctk.CTkLabel(ce, text="Класи (сценарії):",
                     font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=10, sticky="w", padx=10, pady=(8, 2))

        self._entry_grid = ctk.CTkFrame(ce, fg_color="transparent")
        self._entry_grid.grid(row=1, column=0, columnspan=10, sticky="w", padx=6)
        self._rebuild_class_entries()

        btn_row = ctk.CTkFrame(ce, fg_color="transparent")
        btn_row.grid(row=2, column=0, columnspan=10, sticky="w", padx=10, pady=(2, 8))
        ctk.CTkButton(btn_row, text="+ Клас", width=84,
                      command=self._add_class).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="− Клас", width=84, fg_color="gray30",
                      command=self._remove_class).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="Застосувати", width=130,
                      command=self._apply_classes).pack(side="left", padx=16)
        self._apply_lbl = ctk.CTkLabel(btn_row, text="", text_color="green",
                                       font=ctk.CTkFont(size=11))
        self._apply_lbl.pack(side="left", padx=8)

        # ── Крок 1 ──────────────────────────────────────────────────────────
        step1 = ctk.CTkFrame(self)
        step1.pack(fill="x", padx=28, pady=4)
        ctk.CTkLabel(step1, text="Крок 1: Збір навчальних даних",
                     font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=5, sticky="w", padx=10, pady=(8, 2))

        ctk.CTkLabel(step1, text="Клас:").grid(row=1, column=0, padx=10, pady=6, sticky="w")
        self._class_var = ctk.StringVar(value=self._classes[0])
        self._class_selector = ctk.CTkOptionMenu(
            step1, values=self._classes, variable=self._class_var, width=240)
        self._class_selector.grid(row=1, column=1, padx=10, pady=6, sticky="w")

        ctk.CTkLabel(step1, text="Тривалість (с):").grid(row=1, column=2, padx=(20, 4))
        self._dur = ctk.CTkEntry(step1, width=64)
        self._dur.insert(0, str(self.app.cfg.get("collect_duration_sec", 60)))
        self._dur.grid(row=1, column=3, padx=4, pady=6)

        self._progress = ctk.CTkProgressBar(step1, width=380)
        self._progress.set(0)
        self._progress.grid(row=2, column=0, columnspan=3, padx=10, pady=4, sticky="ew")
        self._timer = ctk.CTkLabel(step1, text="0 / 60 сек", width=90, text_color="gray")
        self._timer.grid(row=2, column=3, padx=4)
        self._counter = ctk.CTkLabel(step1, text="0 пакетів", width=80)
        self._counter.grid(row=2, column=4, padx=8)

        self._collect_btn = ctk.CTkButton(step1, text="▶  Старт збору",
                                          width=160, command=self._toggle_collect)
        self._collect_btn.grid(row=3, column=0, padx=10, pady=8, sticky="w")

        # ── Статус датасету ──────────────────────────────────────────────────
        self._ds_frame = ctk.CTkFrame(self)
        self._ds_frame.pack(fill="x", padx=28, pady=2)
        self._rebuild_ds_labels()

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

        ctk.CTkButton(self, text="← Меню", width=120,
                      fg_color="transparent", border_width=1,
                      command=lambda: self.app.show("menu")).pack(side="bottom", pady=6)

        # ── Результати ──────────────────────────────────────────────────────
        self._results = ctk.CTkScrollableFrame(self)
        self._results.pack(fill="both", expand=True, padx=28, pady=4)

    def on_show(self):
        self._refresh_ds_ui()
        self._refresh_train_btn()

    # ── Редактор класів ───────────────────────────────────────────────────────
    def _rebuild_class_entries(self):
        for w in self._entry_grid.winfo_children():
            w.destroy()
        self._class_entries.clear()
        COLS = 4
        for i, cls in enumerate(self._classes):
            row, col = divmod(i, COLS)
            ctk.CTkLabel(self._entry_grid, text=f"{i + 1}.", width=22,
                         font=ctk.CTkFont(size=11)).grid(
                row=row, column=col * 2, padx=(8, 2), pady=3, sticky="e")
            e = ctk.CTkEntry(self._entry_grid, width=155, font=ctk.CTkFont(size=11))
            e.insert(0, cls)
            e.grid(row=row, column=col * 2 + 1, padx=(0, 10), pady=3, sticky="w")
            self._class_entries.append(e)

    def _get_entry_classes(self) -> list[str]:
        result = []
        for i, e in enumerate(self._class_entries):
            name = e.get().strip()
            result.append(name if name else f"Клас {i + 1}")
        return result

    def _add_class(self):
        if len(self._class_entries) >= 10:
            return
        classes = self._get_entry_classes()
        classes.append(f"Клас {len(classes) + 1}")
        self.app.cfg["classes"] = classes
        self._rebuild_class_entries()

    def _remove_class(self):
        if len(self._class_entries) <= 2:
            return
        classes = self._get_entry_classes()[:-1]
        self.app.cfg["classes"] = classes
        self._rebuild_class_entries()

    def _apply_classes(self):
        classes = self._get_entry_classes()
        self.app.cfg["classes"] = classes
        self.app.save_config()
        self._class_selector.configure(values=classes)
        self._class_var.set(classes[0])
        self._rebuild_ds_labels()
        self._refresh_ds_ui()
        self._refresh_train_btn()
        self._apply_lbl.configure(text="✓ Збережено")
        self.after(2000, lambda: self._apply_lbl.configure(text=""))

    # ── Датасет (динамічний) ──────────────────────────────────────────────────
    def _rebuild_ds_labels(self):
        for w in self._ds_frame.winfo_children():
            w.destroy()
        self._ds_labels = {}
        ctk.CTkLabel(self._ds_frame, text="Датасет:",
                     font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10, pady=6)
        for i, cls in enumerate(self._classes):
            color = class_color(i)
            lbl = ctk.CTkLabel(self._ds_frame, text=f"{cls}: 0", text_color=color)
            lbl.pack(side="left", padx=10)
            self._ds_labels[cls] = lbl
        ctk.CTkButton(self._ds_frame, text="Очистити", width=110, fg_color="gray30",
                      command=self._clear_dataset).pack(side="right", padx=10)
        ctk.CTkButton(self._ds_frame, text="📂 Дані", width=90, fg_color="gray30",
                      command=self._open_data_dir).pack(side="right", padx=4)

    # ── Збір даних ────────────────────────────────────────────────────────────
    def _toggle_collect(self):
        if self._collecting:
            self._collecting = False
            self._collect_btn.configure(text="▶  Старт збору")
            self._stop_pinger()
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
        self._timer.configure(text=f"0 / {duration} сек")
        self._counter.configure(text="0 пакетів")

        self._pinger = UdpPinger(rate=500.0, target_ip=self.app.serial.esp32_ip)
        self._pinger.start()

        def task():
            q = self.app.serial.queue
            while True:
                try:
                    q.get_nowait()
                except Exception:
                    break

            os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
            count = 0
            last_ui = time.time()
            start = time.time()
            with open(DATASET_PATH, "a", encoding="utf-8") as f:
                while self._collecting:
                    elapsed = time.time() - start
                    if elapsed >= duration:
                        break
                    try:
                        pkt = self.app.serial.queue.get(timeout=0.5)
                    except Exception:
                        elapsed = time.time() - start
                        self.after(0, self._update_progress,
                                   min(elapsed / duration, 1.0), int(elapsed), duration, count)
                        continue
                    pkt["label"] = label
                    f.write(json.dumps(pkt, ensure_ascii=False) + "\n")
                    count += 1
                    now = time.time()
                    if now - last_ui >= 0.3:
                        last_ui = now
                        elapsed = time.time() - start
                        self.after(0, self._update_progress,
                                   min(elapsed / duration, 1.0), int(elapsed), duration, count)
            self.after(0, self._on_collect_done)

        threading.Thread(target=task, daemon=True).start()

    def _update_progress(self, pct: float, elapsed_sec: int, duration: int, count: int):
        self._progress.set(pct)
        self._timer.configure(text=f"{elapsed_sec} / {duration} сек")
        self._counter.configure(text=f"{count} пакетів")

    def _stop_pinger(self):
        if self._pinger:
            self._pinger.stop()
            self._pinger = None

    def _on_collect_done(self):
        self._collecting = False
        self._stop_pinger()
        self._collect_btn.configure(text="▶  Старт збору")
        self._progress.set(1.0)
        self._refresh_ds_ui()
        self._refresh_train_btn()

    # ── Датасет ───────────────────────────────────────────────────────────────
    def _count_dataset(self) -> dict[str, int]:
        classes = self._classes
        counts = {cls: 0 for cls in classes}
        if not os.path.exists(DATASET_PATH):
            return counts
        try:
            with open(DATASET_PATH, encoding="utf-8") as f:
                for line in f:
                    try:
                        pkt = json.loads(line)
                        lbl = pkt.get("label")
                        if lbl in counts and extract_amplitudes(pkt):
                            counts[lbl] += 1
                    except Exception:
                        pass
        except Exception:
            pass
        return counts

    def _refresh_ds_ui(self):
        counts = self._count_dataset()
        for cls, lbl in self._ds_labels.items():
            count = counts.get(cls, 0)
            suffix = " ✓" if count >= 1500 else ""
            lbl.configure(text=f"{cls}: {count}{suffix}")

    def _refresh_train_btn(self):
        counts = self._count_dataset()
        ready = all(counts.get(cls, 0) > 0 for cls in self._classes)
        self._train_btn.configure(state="normal" if ready else "disabled")

    def _open_data_dir(self):
        data_dir = os.path.dirname(DATASET_PATH)
        os.makedirs(data_dir, exist_ok=True)
        subprocess.Popen(["explorer", data_dir])

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
                classes = self._classes

                packets_by_class: dict[str, list] = {cls: [] for cls in classes}
                rssi_by_class: dict[str, list]    = {cls: [] for cls in classes}
                with open(DATASET_PATH, encoding="utf-8") as f:
                    for line in f:
                        try:
                            pkt = json.loads(line)
                            amps = extract_amplitudes(pkt)
                            label = pkt.get("label")
                            if amps and label in classes:
                                packets_by_class[label].append(amps)
                                rssi_val = pkt.get("rssi")
                                rssi_by_class[label].append(
                                    float(rssi_val) if rssi_val is not None else 0.0)
                        except Exception:
                            pass

                warnings = []

                all_lens = [len(a) for cls_amps in packets_by_class.values()
                            for a in cls_amps]
                if all_lens:
                    from collections import Counter as _Counter
                    actual_n = _Counter(all_lens).most_common(1)[0][0]
                    if actual_n != 114:
                        warnings.append(
                            f"Виявлено {actual_n} субнесучих замість 114 "
                            f"(HT20 канал 20 МГц — це нормально)")
                    for cls in classes:
                        filtered = [(a, r) for a, r in
                                    zip(packets_by_class[cls], rssi_by_class[cls])
                                    if len(a) == actual_n]
                        packets_by_class[cls] = [a for a, _ in filtered]
                        rssi_by_class[cls]    = [r for _, r in filtered]

                for cls in classes:
                    n = len(packets_by_class[cls])
                    if n == 0:
                        raise ValueError(f"Клас «{cls}» — немає даних")
                    if n < 1500:
                        warnings.append(f"«{cls}»: {n} пакетів (рекомендовано ≥ 1500)")

                all_amps, all_labels, all_rssi = [], [], []
                for i, cls in enumerate(classes):
                    all_amps.extend(packets_by_class[cls])
                    all_labels.extend([i] * len(packets_by_class[cls]))
                    all_rssi.extend(rssi_by_class[cls])

                X    = np.array(all_amps,   dtype=np.float32)
                y    = np.array(all_labels, dtype=np.int32)
                rssi = np.array(all_rssi,   dtype=np.float32)

                train_idx, test_idx = Classifier.block_split_indices(y, len(classes))
                X_train, X_test = X[train_idx], X[test_idx]
                y_train, y_test = y[train_idx], y[test_idx]
                rssi_train, rssi_test = rssi[train_idx], rssi[test_idx]

                extractor = FeatureExtractor()
                X_train_pca = extractor.fit_transform(X_train)
                X_test_pca  = extractor.transform(X_test)
                extractor.save()

                clf = Classifier(classes=classes)
                result = clf.train(X_train_pca, y_train, X_test_pca, y_test)
                clf.save()

                result.explained_variance_pct    = extractor.explained_variance_pct
                result.explained_variance_ratio_ = extractor.explained_variance_ratio_
                result.warnings = warnings

                los_ref = compute_los_reference(X_train, y_train, los_label=0)
                result.class_stats    = compute_class_stats(X, rssi, y, classes, los_ref)
                sep = compute_separability(X, y)
                result.fisher_ratio      = sep["fisher_ratio"]
                result.bcv               = sep["bcv"]
                result.wcv               = sep["wcv"]
                result.silhouette        = sep["silhouette"]
                result.pca2_variance_pct = sep["pca2_variance_pct"]
                result.rssi_baselines    = train_rssi_baselines(
                    rssi_train, y_train, rssi_test, y_test, classes)

                self.after(0, self._show_results, result)
            except Exception as e:
                self.after(0, lambda err=e: (
                    self._train_status.configure(text=f"Помилка: {err}", text_color="red"),
                    self._train_btn.configure(state="normal"),
                ))

        threading.Thread(target=task, daemon=True).start()

    def _show_results(self, result):
        self._train_status.configure(text="Модель збережена!", text_color="green")
        self._train_btn.configure(state="normal")
        classes = result.classes

        for w in self._results.winfo_children():
            w.destroy()

        for warn in result.warnings:
            ctk.CTkLabel(self._results, text=f"⚠ {warn}",
                         text_color="orange", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=8)

        ctk.CTkLabel(self._results,
                     text=(f"Train: {result.train_size}  |  Test: {result.test_size}"
                           f"  |  PCA-10: {result.explained_variance_pct:.1f}%"),
                     text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=8, pady=(2, 4))

        CW  = 88
        CWL = 150

        # ── Таблиця 1: статистика сигналу по класах ──────────────────────────
        if result.class_stats:
            ctk.CTkLabel(self._results, text="Таблиця 1: Статистика сигналу по класах",
                         font=ctk.CTkFont(weight="bold", size=11)).pack(anchor="w", padx=8, pady=(6, 1))
            t1 = ctk.CTkFrame(self._results)
            t1.pack(fill="x", padx=4, pady=2)
            for c, (h, w) in enumerate(zip(
                    ["Клас", "n", "μ_CSI", "σ_CSI", "μ_RSSI", "σ_RSSI", "μ||ΔCSI||"],
                    [CWL,   60,   CW,      CW,       CW,        CW,        CW])):
                ctk.CTkLabel(t1, text=h, font=ctk.CTkFont(weight="bold", size=10),
                             width=w).grid(row=0, column=c, padx=2, pady=2)
            for r, st in enumerate(result.class_stats, 1):
                for c, (val, w) in enumerate(zip(
                        [st["cls"], str(st["n"]),
                         f"{st['mu_csi']:.2f}", f"{st['sigma_csi']:.2f}",
                         f"{st['mu_rssi']:.1f}", f"{st['sigma_rssi']:.2f}",
                         f"{st['mu_delta_csi']:.2f}"],
                        [CWL, 60, CW, CW, CW, CW, CW])):
                    ctk.CTkLabel(t1, text=val, font=ctk.CTkFont(size=10),
                                 width=w).grid(row=r, column=c, padx=2, pady=1)

        # ── Таблиця 2: метрики роздільності ──────────────────────────────────
        ctk.CTkLabel(self._results, text="Таблиця 2: Метрики роздільності",
                     font=ctk.CTkFont(weight="bold", size=11)).pack(anchor="w", padx=8, pady=(6, 1))
        t2 = ctk.CTkFrame(self._results)
        t2.pack(fill="x", padx=4, pady=2)
        sep_hdrs = ["Fisher B/W", "WCV", "BCV", "Silhouette", "PCA-2%"]
        sep_vals = [f"{result.fisher_ratio:.3f}", f"{result.wcv:.4f}", f"{result.bcv:.4f}",
                    f"{result.silhouette:.4f}", f"{result.pca2_variance_pct:.1f}%"]
        sep_ref  = ["(2.65)", "(0.075)", "(0.199)", "(-0.003)", "(84.6%)"]
        for c, h in enumerate(sep_hdrs):
            ctk.CTkLabel(t2, text=h, font=ctk.CTkFont(weight="bold", size=10),
                         width=100).grid(row=0, column=c, padx=3, pady=2)
        for c, v in enumerate(sep_vals):
            ctk.CTkLabel(t2, text=v, font=ctk.CTkFont(size=10),
                         width=100).grid(row=1, column=c, padx=3, pady=1)
        for c, ref in enumerate(sep_ref):
            ctk.CTkLabel(t2, text=ref, font=ctk.CTkFont(size=9), text_color="gray",
                         width=100).grid(row=2, column=c, padx=3, pady=0)

        # ── Таблиця 3: порівняння класифікаторів ─────────────────────────────
        ctk.CTkLabel(self._results, text="Таблиця 3: Порівняння класифікаторів",
                     font=ctk.CTkFont(weight="bold", size=11)).pack(anchor="w", padx=8, pady=(6, 1))
        t3 = ctk.CTkFrame(self._results)
        t3.pack(fill="x", padx=4, pady=2)
        for c, h in enumerate(["Модель", "Accuracy", "Precision", "Recall", "F1-macro"]):
            ctk.CTkLabel(t3, text=h, font=ctk.CTkFont(weight="bold", size=10),
                         width=135).grid(row=0, column=c, padx=3, pady=2)

        t3_rows: list[tuple] = []
        rb = result.rssi_baselines
        if "single" in rb:
            m = rb["single"]["report"].get("macro avg", {})
            t3_rows.append(("RSSI single (kNN)", rb["single"]["accuracy"],
                             m.get("precision", 0), m.get("recall", 0), m.get("f1-score", 0), False))
        if "windowed" in rb:
            m = rb["windowed"]["report"].get("macro avg", {})
            t3_rows.append((f"RSSI W={W_RSSI} (kNN)", rb["windowed"]["accuracy"],
                             m.get("precision", 0), m.get("recall", 0), m.get("f1-score", 0), False))
        for mname, acc, rep, is_main in [
            ("CSI kNN PCA-10",  result.knn_accuracy, result.knn_report, False),
            ("CSI SVM RBF",     result.svm_accuracy, result.svm_report, True),
        ]:
            m = rep.get("macro avg", {})
            t3_rows.append((mname, acc, m.get("precision", 0), m.get("recall", 0),
                             m.get("f1-score", 0), is_main))

        for r, (mname, acc, prec, rec, f1, is_main) in enumerate(t3_rows, 1):
            color = "green" if is_main else "white"
            wt    = "bold"  if is_main else "normal"
            for c, val in enumerate([mname, f"{acc:.1%}", f"{prec:.3f}", f"{rec:.3f}", f"{f1:.3f}"]):
                ctk.CTkLabel(t3, text=val, text_color=color,
                             font=ctk.CTkFont(size=10, weight=wt),
                             width=135).grid(row=r, column=c, padx=3, pady=1)

        # ── Таблиця 4: F1 по класах ───────────────────────────────────────────
        short = [c[:9] for c in classes]
        ctk.CTkLabel(self._results, text="Таблиця 4: F1-score по класах",
                     font=ctk.CTkFont(weight="bold", size=11)).pack(anchor="w", padx=8, pady=(6, 1))
        t4 = ctk.CTkFrame(self._results)
        t4.pack(fill="x", padx=4, pady=2)
        for c, h in enumerate(["Модель"] + short):
            ctk.CTkLabel(t4, text=h, font=ctk.CTkFont(weight="bold", size=10),
                         width=90).grid(row=0, column=c, padx=3, pady=2)
        for r, (mname, rep) in enumerate([("kNN", result.knn_report), ("SVM", result.svm_report)], 1):
            ctk.CTkLabel(t4, text=mname, font=ctk.CTkFont(size=10),
                         width=90).grid(row=r, column=0, padx=3, pady=1)
            for c, cls in enumerate(classes, 1):
                f1 = rep.get(cls, {}).get("f1-score", 0.0)
                color = "green" if f1 >= 0.75 else ("orange" if f1 >= 0.5 else "red")
                ctk.CTkLabel(t4, text=f"{f1:.3f}", text_color=color,
                             font=ctk.CTkFont(size=10),
                             width=90).grid(row=r, column=c, padx=3, pady=1)

        # ── Графіки: kNN + SVM confusion matrices + PCA variance ─────────────
        short_cm = [c[:7] for c in classes]
        has_pca = result.explained_variance_ratio_ is not None
        ncols = 3 if has_pca else 2
        fig = Figure(figsize=(4.2 * ncols, 3.2), dpi=80, facecolor="#2b2b2b")

        for col, (title, cm) in enumerate([
            ("kNN Confusion Matrix", result.knn_cm),
            ("SVM Confusion Matrix", result.svm_cm),
        ]):
            ax = fig.add_subplot(1, ncols, col + 1)
            ax.set_facecolor("#2b2b2b")
            ax.imshow(cm, interpolation="nearest", cmap="Blues")
            ax.set_title(title, color="white", fontsize=9)
            ax.set_xticks(range(len(classes)))
            ax.set_yticks(range(len(classes)))
            ax.set_xticklabels(short_cm, rotation=30, ha="right", color="white", fontsize=7)
            ax.set_yticklabels(short_cm, color="white", fontsize=7)
            for i in range(len(classes)):
                for j in range(len(classes)):
                    ax.text(j, i, str(int(cm[i, j])),
                            ha="center", va="center", color="white", fontsize=8)

        if has_pca:
            ax_pca = fig.add_subplot(1, ncols, ncols)
            ax_pca.set_facecolor("#2b2b2b")
            ratios = result.explained_variance_ratio_ * 100
            ax_pca.bar(range(1, len(ratios) + 1), ratios, color="#4fc3f7")
            ax_pca.set_title("PCA: дисперсія по компонентах", color="white", fontsize=9)
            ax_pca.set_xlabel("Компонента", color="gray", fontsize=8)
            ax_pca.set_ylabel("%", color="gray", fontsize=8)
            ax_pca.tick_params(colors="white")
            for spine in ax_pca.spines.values():
                spine.set_edgecolor("#444")

        fig.tight_layout()
        FigureCanvasTkAgg(fig, master=self._results).get_tk_widget().pack(pady=4)
