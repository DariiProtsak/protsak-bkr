import os
import numpy as np
import joblib
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

N_COMPONENTS = 10
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCA_PATH    = os.path.join(_BASE, "pca.pkl")
SCALER_PATH = os.path.join(_BASE, "scaler.pkl")

class FeatureExtractor:
    def __init__(self):
        self.scaler: StandardScaler | None = None
        self.pca: PCA | None = None
        self.explained_variance_ratio_: np.ndarray | None = None

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """Fit scaler and PCA on training data only, then transform."""
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        n = min(N_COMPONENTS, X.shape[0], X.shape[1])
        self.pca = PCA(n_components=n)
        X_pca = self.pca.fit_transform(X_scaled)
        self.explained_variance_ratio_ = self.pca.explained_variance_ratio_.copy()
        return X_pca

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Transform only — never call fit here."""
        return self.pca.transform(self.scaler.transform(X))

    def save(self):
        joblib.dump(self.pca,    PCA_PATH)
        joblib.dump(self.scaler, SCALER_PATH)

    def load(self):
        self.pca    = joblib.load(PCA_PATH)
        self.scaler = joblib.load(SCALER_PATH)

    @property
    def explained_variance_pct(self) -> float:
        if self.explained_variance_ratio_ is None:
            return 0.0
        return float(self.explained_variance_ratio_.sum() * 100)

    @staticmethod
    def artifacts_exist() -> bool:
        return os.path.exists(PCA_PATH) and os.path.exists(SCALER_PATH)
