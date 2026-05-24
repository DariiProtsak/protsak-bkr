import os
from collections import Counter
import numpy as np
import joblib
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from dataclasses import dataclass, field

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(_BASE, "model.pkl")

BLOCK_SIZE = 1500

_PALETTE = [
    "#4caf50", "#ffc107", "#29b6f6", "#f44336", "#ab47bc",
    "#ff7043", "#26c6da", "#d4e157", "#ec407a", "#66bb6a",
]


def class_color(idx: int) -> str:
    return _PALETTE[idx % len(_PALETTE)]


@dataclass
class TrainingResult:
    classes: list = field(default_factory=list)
    knn_accuracy: float = 0.0
    svm_accuracy: float = 0.0
    knn_report: dict = field(default_factory=dict)
    svm_report: dict = field(default_factory=dict)
    knn_cm: np.ndarray | None = None
    svm_cm: np.ndarray | None = None
    explained_variance_pct: float = 0.0
    explained_variance_ratio_: np.ndarray | None = None
    train_size: int = 0
    test_size: int = 0
    warnings: list[str] = field(default_factory=list)
    fisher_ratio: float = 0.0
    bcv: float = 0.0
    wcv: float = 0.0
    silhouette: float = 0.0
    pca2_variance_pct: float = 0.0
    class_stats: list = field(default_factory=list)
    rssi_baselines: dict = field(default_factory=dict)


class Classifier:
    def __init__(self, classes: list[str] | None = None):
        self.classes: list[str] = list(classes) if classes else []
        self.knn = KNeighborsClassifier(n_neighbors=5, metric="euclidean")
        self.svm = SVC(kernel="rbf", C=1.0, gamma="scale", probability=True)

    @staticmethod
    def block_split_indices(y: np.ndarray, n_classes: int) -> tuple[list, list]:
        train_idx, test_idx = [], []
        for label_idx in range(n_classes):
            idx = np.where(y == label_idx)[0]
            if len(idx) >= 2 * BLOCK_SIZE:
                test_idx.extend(idx[-BLOCK_SIZE:].tolist())
                train_idx.extend(idx[:-BLOCK_SIZE].tolist())
            else:
                n_test = max(1, int(len(idx) * 0.2))
                test_idx.extend(idx[-n_test:].tolist())
                train_idx.extend(idx[:-n_test].tolist())
        return train_idx, test_idx

    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              X_test: np.ndarray,  y_test:  np.ndarray) -> TrainingResult:
        self.knn.fit(X_train, y_train)
        self.svm.fit(X_train, y_train)

        result = TrainingResult(classes=list(self.classes))
        result.train_size = int(len(X_train))
        result.test_size  = int(len(X_test))

        all_labels = list(range(len(self.classes)))

        for attr, model in [("knn", self.knn), ("svm", self.svm)]:
            y_pred = model.predict(X_test)
            setattr(result, f"{attr}_accuracy", float(accuracy_score(y_test, y_pred)))
            setattr(result, f"{attr}_report",
                    classification_report(y_test, y_pred, output_dict=True,
                                          target_names=self.classes, labels=all_labels,
                                          zero_division=0))
            setattr(result, f"{attr}_cm",
                    confusion_matrix(y_test, y_pred, labels=all_labels))

        return result

    def predict(self, X: np.ndarray) -> tuple[str, float]:
        proba = self.svm.predict_proba(X)
        votes = self.svm.predict(X)
        final_idx = int(Counter(votes).most_common(1)[0][0])
        mean_conf = float(proba[:, final_idx].mean())
        return self.classes[final_idx], mean_conf

    def save(self):
        joblib.dump({"knn": self.knn, "svm": self.svm, "classes": self.classes}, MODEL_PATH)

    def load(self):
        data = joblib.load(MODEL_PATH)
        self.knn    = data["knn"]
        self.svm    = data["svm"]
        self.classes = data.get("classes", [])

    @staticmethod
    def model_exists() -> bool:
        return os.path.exists(MODEL_PATH)
