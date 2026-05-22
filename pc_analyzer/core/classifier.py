import os
import numpy as np
import joblib
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from dataclasses import dataclass, field

CLASSES = ["Порожньо", "Стілець", "Людина"]
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(_BASE, "model.pkl")

@dataclass
class TrainingResult:
    knn_accuracy: float = 0.0
    svm_accuracy: float = 0.0
    knn_report: dict = field(default_factory=dict)
    svm_report: dict = field(default_factory=dict)
    knn_cm: np.ndarray | None = None
    svm_cm: np.ndarray | None = None
    explained_variance_pct: float = 0.0

class Classifier:
    def __init__(self):
        self.knn = KNeighborsClassifier(n_neighbors=5)
        self.svm = SVC(kernel="rbf", C=1.0, gamma="scale", probability=True)

    def train(self, X: np.ndarray, y: np.ndarray) -> TrainingResult:
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )
        self.knn.fit(X_tr, y_tr)
        self.svm.fit(X_tr, y_tr)

        result = TrainingResult()

        knn_pred = self.knn.predict(X_te)
        result.knn_accuracy = accuracy_score(y_te, knn_pred)
        result.knn_report   = classification_report(y_te, knn_pred, output_dict=True,
                                                     target_names=CLASSES, zero_division=0)
        result.knn_cm       = confusion_matrix(y_te, knn_pred)

        svm_pred = self.svm.predict(X_te)
        result.svm_accuracy = accuracy_score(y_te, svm_pred)
        result.svm_report   = classification_report(y_te, svm_pred, output_dict=True,
                                                     target_names=CLASSES, zero_division=0)
        result.svm_cm       = confusion_matrix(y_te, svm_pred)
        return result

    def predict(self, X: np.ndarray) -> tuple[str, float]:
        proba = self.svm.predict_proba(X)[0]
        idx   = int(np.argmax(proba))
        return CLASSES[idx], float(proba[idx])

    def save(self):
        joblib.dump({"knn": self.knn, "svm": self.svm}, MODEL_PATH)

    def load(self):
        data     = joblib.load(MODEL_PATH)
        self.knn = data["knn"]
        self.svm = data["svm"]

    @staticmethod
    def model_exists() -> bool:
        return os.path.exists(MODEL_PATH)
