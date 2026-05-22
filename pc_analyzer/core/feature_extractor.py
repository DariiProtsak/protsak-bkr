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

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        self.pca = PCA(n_components=N_COMPONENTS)
        return self.pca.fit_transform(X_scaled)

    def transform(self, X: np.ndarray) -> np.ndarray:
        return self.pca.transform(self.scaler.transform(X))

    def save(self):
        joblib.dump(self.pca, PCA_PATH)
        joblib.dump(self.scaler, SCALER_PATH)

    def load(self):
        self.pca    = joblib.load(PCA_PATH)
        self.scaler = joblib.load(SCALER_PATH)

    @property
    def explained_variance_pct(self) -> float:
        if self.pca is None:
            return 0.0
        return float(self.pca.explained_variance_ratio_.sum()) * 100
