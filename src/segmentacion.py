"""Primera etapa de procesamiento: envolvente, detección de inicio,
selección de un segmento comparable y normalización.

Criterio de segmentación (igual para todos los instrumentos):
    1. Se calcula la envolvente RMS con una ventana de 10 ms.
    2. El INICIO de la nota es el primer instante en que la envolvente supera
       el 10 % de su máximo.
    3. Se descarta el transitorio de ataque saltando ``desplazamiento_s``
       (0.10 s por defecto) y se toma una ventana de ``duracion_s``
       (0.20 s por defecto).
Así todos los segmentos tienen el mismo número de muestras y corresponden a
la misma fase de la nota, lo que permite comparar sus espectros.
"""
from __future__ import annotations

import numpy as np


def envolvente_rms(x: np.ndarray, fs: float, ventana_s: float = 0.010) -> np.ndarray:
    """Envolvente de amplitud: raíz de la media móvil de x[n]^2 (ventana rectangular)."""
    n = max(1, int(round(ventana_s * fs)))
    nucleo = np.ones(n) / n
    return np.sqrt(np.convolve(x**2, nucleo, mode="same"))


def detectar_inicio(x: np.ndarray, fs: float, umbral_rel: float = 0.10) -> int:
    """Índice de muestra en que la envolvente supera ``umbral_rel`` * máximo."""
    env = envolvente_rms(x, fs)
    return int(np.argmax(env >= umbral_rel * env.max()))


def seleccionar_segmento(
    x: np.ndarray,
    fs: float,
    duracion_s: float = 0.20,
    desplazamiento_s: float = 0.10,
    umbral_rel: float = 0.10,
) -> tuple[np.ndarray, int, int]:
    """Devuelve ``(segmento, i0, inicio)``: muestras, índice de arranque y inicio de la nota."""
    inicio = detectar_inicio(x, fs, umbral_rel)
    n_seg = int(round(duracion_s * fs))
    i0 = inicio + int(round(desplazamiento_s * fs))
    if i0 + n_seg > len(x):  # nota demasiado corta: se corre la ventana hacia atrás
        i0 = max(0, len(x) - n_seg)
    return x[i0 : i0 + n_seg], i0, inicio


def normalizar_pico(x: np.ndarray, objetivo: float = 1.0) -> np.ndarray:
    """Escala la señal para que su máximo absoluto sea ``objetivo``."""
    return objetivo * x / np.max(np.abs(x))


def normalizar_rms(x: np.ndarray, objetivo: float = 0.1) -> np.ndarray:
    """Escala la señal para que su valor RMS sea ``objetivo``."""
    return objetivo * x / np.sqrt(np.mean(x**2))
