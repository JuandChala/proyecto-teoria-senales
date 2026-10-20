"""Degradación controlada: ruido blanco gaussiano aditivo (AWGN).

Modelo:  y[n] = x[n] + w[n],   w[n] ~ N(0, sigma^2)

La varianza se calcula para lograr una relación señal-ruido objetivo:

    SNR_dB = 10*log10(P_x / P_w)   =>   sigma^2 = P_x / 10^(SNR_dB/10)

donde P_x = mean(x^2) es la potencia de la señal.
"""
from __future__ import annotations

import numpy as np


def agregar_ruido_awgn(x: np.ndarray, snr_db: float, rng: np.random.Generator | None = None) -> np.ndarray:
    """Suma ruido blanco gaussiano para obtener (en promedio) la SNR indicada."""
    rng = rng or np.random.default_rng()
    potencia_senal = np.mean(x**2)
    sigma = np.sqrt(potencia_senal / 10.0 ** (snr_db / 10.0))
    return x + sigma * rng.standard_normal(len(x))


def medir_snr_db(limpia: np.ndarray, ruidosa: np.ndarray) -> float:
    """SNR realmente obtenida entre una señal limpia y su versión ruidosa."""
    ruido = ruidosa - limpia
    return float(10.0 * np.log10(np.sum(limpia**2) / np.sum(ruido**2)))
