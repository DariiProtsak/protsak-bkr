"""
Statistical analysis module — reproduces the metrics from the article:
  Table 1: per-class signal statistics (μ_CSI, σ_CSI, μ_RSSI, σ_RSSI, μ||ΔCSI||)
  Table 2: separability metrics (Fisher Ratio, WCV, BCV, Silhouette, PCA-2/10 %)
  Table 3: 4-model classification comparison (RSSI single, RSSI windowed, kNN CSI, SVM CSI)
"""

import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (accuracy_score, classification_report,
                              confusion_matrix, silhouette_score)
from sklearn.decomposition import PCA

W_RSSI = 50  # window size for windowed RSSI baseline (formula from article)


# ── μ||ΔCSI|| ─────────────────────────────────────────────────────────────────

def compute_los_reference(X: np.ndarray, y: np.ndarray,
                           los_label: int = 0, n: int = 1500) -> np.ndarray:
    """Mean amplitude profile over first n packets of the LOS/reference class.
    Corresponds to A_k^LOS in formula (5)."""
    idx = np.where(y == los_label)[0]
    n = min(n, len(idx))
    return X[idx[:n]].mean(axis=0)  # shape: (K,)


def compute_delta_csi(X: np.ndarray, los_ref: np.ndarray) -> np.ndarray:
    """L2-norm of amplitude deviation from LOS reference per packet.
    Inner sqrt in formula (5). Returns shape (N,)."""
    return np.sqrt(((X - los_ref) ** 2).sum(axis=1))


# ── Per-class signal statistics (Table 1) ────────────────────────────────────

def compute_class_stats(X: np.ndarray, rssi: np.ndarray, y: np.ndarray,
                         classes: list, los_ref: np.ndarray) -> list[dict]:
    """Compute μ_CSI, σ_CSI, μ_RSSI, σ_RSSI, μ||ΔCSI|| for each class."""
    deltas = compute_delta_csi(X, los_ref)
    stats = []
    for i, cls in enumerate(classes):
        mask = y == i
        if not mask.any():
            stats.append({"cls": cls, "n": 0, "mu_csi": 0, "sigma_csi": 0,
                          "mu_rssi": 0, "sigma_rssi": 0, "mu_delta_csi": 0})
            continue
        avg_amps = X[mask].mean(axis=1)   # μ_avg per packet
        stats.append({
            "cls":          cls,
            "n":            int(mask.sum()),
            "mu_csi":       float(avg_amps.mean()),
            "sigma_csi":    float(avg_amps.std()),
            "mu_rssi":      float(rssi[mask].mean()),
            "sigma_rssi":   float(rssi[mask].std()),
            "mu_delta_csi": float(deltas[mask].mean()),
        })
    return stats


# ── Separability metrics (Table 2) ───────────────────────────────────────────

def compute_separability(X: np.ndarray, y: np.ndarray,
                          pca_evr: np.ndarray | None = None) -> dict:
    """Fisher Ratio B/W, WCV, BCV, Silhouette (PCA-2), PCA-2 variance %."""
    scalar = X.mean(axis=1)          # scalar feature μ_CSI per packet
    global_mean = scalar.mean()
    classes = np.unique(y)
    N = len(y)

    bcv = float(sum(np.sum(y == c) * (scalar[y == c].mean() - global_mean) ** 2
                    for c in classes) / N)
    wcv = float(sum(np.sum(y == c) * scalar[y == c].var()
                    for c in classes) / N)
    fisher = float(bcv / wcv) if wcv > 0 else 0.0

    # Silhouette in PCA-2 space on a subsample
    n_sub = min(600, N // max(len(classes), 1))
    sub_idx = []
    for c in classes:
        ci = np.where(y == c)[0]
        sub_idx.extend(ci[:n_sub].tolist())
    sub_idx = np.array(sub_idx)

    pca2 = PCA(n_components=min(2, X.shape[1], N - 1))
    X_pca2 = pca2.fit_transform(X)
    try:
        sil = float(silhouette_score(X_pca2[sub_idx], y[sub_idx]))
    except Exception:
        sil = 0.0

    pca2_var = float(pca2.explained_variance_ratio_.sum() * 100)

    return {
        "fisher_ratio":    fisher,
        "bcv":             bcv,
        "wcv":             wcv,
        "silhouette":      sil,
        "pca2_variance_pct": pca2_var,
    }


# ── RSSI baseline models (models 1 & 2 from Table 3) ─────────────────────────

def _make_rssi_windows(rssi: np.ndarray, y: np.ndarray,
                        n_classes: int, W: int) -> tuple[np.ndarray, np.ndarray]:
    Xw, yw = [], []
    for i in range(n_classes):
        r = rssi[y == i]
        for start in range(0, len(r) - W + 1, W):
            w = r[start:start + W]
            Xw.append([float(w.mean()), float(w.std())])
            yw.append(i)
    if not Xw:
        return np.empty((0, 2), dtype=np.float32), np.empty(0, dtype=np.int32)
    return np.array(Xw, dtype=np.float32), np.array(yw, dtype=np.int32)


def train_rssi_baselines(rssi_train: np.ndarray, y_train: np.ndarray,
                          rssi_test: np.ndarray,  y_test:  np.ndarray,
                          classes: list) -> dict:
    """Train kNN on single RSSI and on windowed [μ_RSSI, σ_RSSI] W=50."""
    all_labels = list(range(len(classes)))
    results = {}

    # Model 1: single RSSI value per packet
    knn1 = KNeighborsClassifier(n_neighbors=5, metric="euclidean")
    knn1.fit(rssi_train.reshape(-1, 1), y_train)
    yp1 = knn1.predict(rssi_test.reshape(-1, 1))
    results["single"] = {
        "accuracy": float(accuracy_score(y_test, yp1)),
        "report":   classification_report(y_test, yp1, output_dict=True,
                                           target_names=classes,
                                           labels=all_labels, zero_division=0),
    }

    # Model 2: windowed [μ_RSSI, σ_RSSI] with W=50
    Xtr_w, ytr_w = _make_rssi_windows(rssi_train, y_train, len(classes), W_RSSI)
    Xte_w, yte_w = _make_rssi_windows(rssi_test,  y_test,  len(classes), W_RSSI)
    if len(Xtr_w) > len(classes) and len(Xte_w) > 0:
        knnw = KNeighborsClassifier(n_neighbors=5, metric="euclidean")
        knnw.fit(Xtr_w, ytr_w)
        ypw = knnw.predict(Xte_w)
        results["windowed"] = {
            "accuracy":       float(accuracy_score(yte_w, ypw)),
            "n_windows_test": len(Xte_w),
            "report":         classification_report(yte_w, ypw, output_dict=True,
                                                    target_names=classes,
                                                    labels=all_labels,
                                                    zero_division=0),
        }

    return results
