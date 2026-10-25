"""Ajuste, predicción y métricas de los modelos de probabilidad (regresión logística antisimétrica)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

#: Semilla de todo lo aleatorio del modelo (bootstrap).
SEMILLA = 726017
#: Rejilla de regularización (C = 1 / lambda) para la validación temporal.
REJILLA_C: tuple[float, ...] = (0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 10.0)
#: Réplicas bootstrap de los intervalos. D-29.
B_ESCENARIOS = 300
B_METRICAS = 1000
#: Bins de calibración (probabilidad del favorito según cada modelo).
BINS_CALIBRACION: tuple[float, ...] = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)


@dataclass
class Modelo:
    """Regresión logística sin intercepto sobre variables antisimétricas: p(A gana B) = 1 - p(B gana A)."""

    columnas: list[str]
    C: float
    pipeline: object | None = None

    def ajustar(self, X: pd.DataFrame, y: pd.Series) -> "Modelo":
        """Ajusta el escalado (sin centrar, para no romper la antisimetría) y la logística."""
        self.pipeline = make_pipeline(
            StandardScaler(with_mean=False),
            LogisticRegression(C=self.C, fit_intercept=False, max_iter=5000),
        )
        self.pipeline.fit(X[self.columnas].to_numpy(), y.to_numpy())
        return self

    def predecir(self, X: pd.DataFrame) -> np.ndarray:
        """Probabilidad de victoria del peleador de cada fila."""
        return self.pipeline.predict_proba(X[self.columnas].to_numpy())[:, 1]

    def coeficientes(self) -> pd.DataFrame:
        """Coeficientes en la escala estandarizada y en la original."""
        escala = self.pipeline.named_steps["standardscaler"].scale_
        coef = self.pipeline.named_steps["logisticregression"].coef_[0]
        return pd.DataFrame({"variable": self.columnas, "coef_estandarizado": coef, "coef_original": coef / escala})


def log_loss(y: np.ndarray, p: np.ndarray) -> float:
    """Log-loss medio (probabilidades recortadas a [1e-6, 1 - 1e-6])."""
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def brier(y: np.ndarray, p: np.ndarray) -> float:
    """Error cuadrático medio de la probabilidad."""
    return float(np.mean((p - y) ** 2))


def accuracy(y: np.ndarray, p: np.ndarray) -> float:
    """Acierto del lado con p > 0,5 (p = 0,5 cuenta como fallo)."""
    return float(np.mean((p > 0.5) == (y == 1)))


def favorito(y: np.ndarray, p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Reexpresa cada pelea desde el favorito del modelo: (p_favorito >= 0,5, gana_favorito)."""
    es = p >= 0.5
    return np.where(es, p, 1 - p), np.where(es, y, 1 - y)


def ece(y: np.ndarray, p: np.ndarray) -> float:
    """Error de calibración esperado con los bins de BINS_CALIBRACION (desde el favorito)."""
    pf, yf = favorito(y, p)
    idx = np.clip(np.digitize(pf, BINS_CALIBRACION[1:-1]), 0, len(BINS_CALIBRACION) - 2)
    total = 0.0
    for b in range(len(BINS_CALIBRACION) - 1):
        m = idx == b
        if m.any():
            total += m.mean() * abs(pf[m].mean() - yf[m].mean())
    return float(total)


def tabla_calibracion(y: np.ndarray, p: np.ndarray) -> pd.DataFrame:
    """Peleas, probabilidad media y frecuencia observada del favorito por bin."""
    pf, yf = favorito(y, p)
    idx = np.clip(np.digitize(pf, BINS_CALIBRACION[1:-1]), 0, len(BINS_CALIBRACION) - 2)
    filas = []
    for b in range(len(BINS_CALIBRACION) - 1):
        m = idx == b
        filas.append(
            {
                "bin": f"[{BINS_CALIBRACION[b]:.1f}, {BINS_CALIBRACION[b + 1]:.1f}{']' if b == len(BINS_CALIBRACION) - 2 else ')'}",
                "peleas": int(m.sum()),
                "p_media_favorito": float(pf[m].mean()) if m.any() else np.nan,
                "frecuencia_victoria_favorito": float(yf[m].mean()) if m.any() else np.nan,
            }
        )
    return pd.DataFrame(filas)


def elegir_C(columnas: list[str], X_tr: pd.DataFrame, y_tr: pd.Series, X_va: pd.DataFrame, y_va: pd.Series) -> tuple[float, pd.DataFrame]:
    """Elige C por log-loss en el periodo de validación (temporal, posterior al de ajuste)."""
    filas = []
    for C in REJILLA_C:
        m = Modelo(columnas, C).ajustar(X_tr, y_tr)
        filas.append({"C": C, "log_loss_validacion": log_loss(y_va.to_numpy(), m.predecir(X_va))})
    tabla = pd.DataFrame(filas)
    mejor = float(tabla.sort_values(["log_loss_validacion", "C"], kind="mergesort").iloc[0]["C"])
    return mejor, tabla


def indices_bootstrap(n: int, b: int, semilla: int) -> np.ndarray:
    """Matriz b x n de índices remuestreados con reposición (semilla fija)."""
    rng = np.random.default_rng(semilla)
    return rng.integers(0, n, size=(b, n))
