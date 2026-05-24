import os
from collections import Counter
import numpy as np
import joblib
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from dataclasses import dataclass, field

CLASSES = [
    "Пряма видимість",
    "Меблі",
    "Міжкімнатні двері",
    "Одинарна стіна",
    "Подвійна стіна",
]
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(_BASE, "model.pkl")

BLOCK_SIZE = 1500

@dataclass
class TrainingResult:
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
    def __init__(self):
        self.knn = KNeighborsClassifier(n_neighbors=5, metric="euclidean")
        self.svm = SVC(kernel="rbf", C=1.0, gamma="scale", probability=True)

    @staticmethod
    def block_split_indices(y: np.ndarray) -> tuple[list, list]:
        """Returns (train_idx, test_idx) for block-based split."""
        train_idx, test_idx = [], []
        for label_idx in range(len(CLASSES)):
            idx = np.where(y == label_idx)[0]
            if len(idx) >= 2 * BLOCK_SIZE:
                test_idx.extend(idx[-BLOCK_SIZE:].tolist())
                train_idx.extend(idx[:-BLOCK_SIZE].tolist())
            else:
                n_test = max(1, int(len(idx) * 0.2))
                test_idx.extend(idx[-n_test:].tolist())
                train_idx.extend(idx[:-n_test].tolist())
        return train_idx, test_idx

    @staticmethod
    def block_split(X: np.ndarray, y: np.ndarray) -> tuple:
        """Last BLOCK_SIZE packets per class → test, rest → train."""
        train_idx, test_idx = Classifier.block_split_indices(y)
        return (X[train_idx], X[test_idx], y[train_idx], y[test_idx])

    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              X_test: np.ndarray,  y_test:  np.ndarray) -> TrainingResult:
        """Train both models on pre-scaled, pre-PCA data; evaluate on test set."""
        self.knn.fit(X_train, y_train)
        self.svm.fit(X_train, y_train)

        result = TrainingResult()
        result.train_size = int(len(X_train))
        result.test_size  = int(len(X_test))

        all_labels = list(range(len(CLASSES)))

        for attr, model in [("knn", self.knn), ("svm", self.svm)]:
            y_pred = model.predict(X_test)
            setattr(result, f"{attr}_accuracy", float(accuracy_score(y_test, y_pred)))
            setattr(result, f"{attr}_report",
                    classification_report(y_test, y_pred, output_dict=True,
                                          target_names=CLASSES, labels=all_labels,
                                          zero_division=0))
            setattr(result, f"{attr}_cm",
                    confusion_matrix(y_test, y_pred, labels=all_labels))

        return result

    def predict(self, X: np.ndarray) -> tuple[str, float]:
        """Majority vote over all rows in X (one block of packets).
        Returns (class_name, mean_confidence_of_winner)."""
        proba = self.svm.predict_proba(X)          # (N, n_classes)
        votes = self.svm.predict(X)                # (N,)
        final_idx = int(Counter(votes).most_common(1)[0][0])
        mean_conf = float(proba[:, final_idx].mean())
        return CLASSES[final_idx], mean_conf

    def save(self):
        joblib.dump({"knn": self.knn, "svm": self.svm}, MODEL_PATH)

    def load(self):
        data     = joblib.load(MODEL_PATH)
        self.knn = data["knn"]
        self.svm = data["svm"]

    @staticmethod
    def model_exists() -> bool:
        return os.path.exists(MODEL_PATH)
