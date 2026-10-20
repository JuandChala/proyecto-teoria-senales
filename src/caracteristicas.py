"""Caracterización temporal y frecuencial de una señal de audio.

Dominio del tiempo : estadísticos, energía/potencia, cruces por cero, envolvente.
Dominio de la frecuencia : DFT/FFT con ventana de Hann, f0, parciales, centroide.
"""
from __future__ import annotations

import numpy as np

from .segmentacion import envolvente_rms

# ----------------------------------------------------------------------
# Dominio del tiempo
# ----------------------------------------------------------------------


def caracteristicas_temporales(x: np.ndarray, fs: float) -> dict:
    """Medidas básicas de x[n] (escala completa = ±1, es decir, sin unidades físicas)."""
    n = len(x)
    rms = float(np.sqrt(np.mean(x**2)))
    pico = float(np.max(np.abs(x)))
    cruces = int(np.sum(np.signbit(x[:-1]) != np.signbit(x[1:])))
    return {
        "n_muestras": n,
        "duracion_s": n / fs,
        "minimo": float(x.min()),
        "maximo": float(x.max()),
        "media": float(x.mean()),
        "amplitud_pico": pico,
        "rms": rms,
        "potencia": rms**2,  # P = (1/N) * sum x[n]^2
        "energia": float(np.sum(x**2)),  # E = sum x[n]^2
        "factor_cresta": pico / rms if rms > 0 else float("nan"),
        "cruces_por_cero_s": cruces / (n / fs),  # para un seno de frecuencia f vale ~2f
    }


def parametros_envolvente(x: np.ndarray, fs: float) -> dict:
    """Parámetros de la envolvente RMS.

    * ``tiempo_ataque_ms``: tiempo que tarda en pasar del 10 % al 90 % del máximo.
    * ``tiempo_a_mitad_s``: tiempo, medido desde que alcanza el 90 %, hasta que
      cae por debajo del 50 % del máximo (mide qué tan sostenido es el sonido:
      grande = sostenido, pequeño = se apaga rápido).
    """
    env = envolvente_rms(x, fs)
    pico = env.max()
    i10 = int(np.argmax(env >= 0.10 * pico))
    i90 = int(np.argmax(env >= 0.90 * pico))
    despues = env[i90:] < 0.5 * pico
    t_mitad = float(np.argmax(despues) / fs) if despues.any() else float("nan")
    return {
        "tiempo_ataque_ms": 1000.0 * (i90 - i10) / fs,
        "tiempo_a_mitad_s": t_mitad,
    }


# ----------------------------------------------------------------------
# Dominio de la frecuencia
# ----------------------------------------------------------------------


def espectro_magnitud(x: np.ndarray, fs: float, zero_pad: int = 8) -> tuple[np.ndarray, np.ndarray]:
    """Espectro de magnitud de un segmento mediante FFT con ventana de Hann.

    Devuelve ``(f, mag)``:
      * ``f``  : eje de frecuencias en Hz, f[k] = k * fs / N_fft  (0 ... fs/2).
      * ``mag``: amplitud pico estimada de cada componente senoidal. Se divide
        por sum(w)/2 para compensar la ganancia de la ventana, de modo que un
        seno de amplitud A produce un pico de altura ~A.

    ``zero_pad`` (relleno con ceros) solo interpola el espectro para ubicar
    mejor los picos; la resolución real sigue siendo ~ fs / N (N = largo del
    segmento), aumentada por el ancho del lóbulo principal de la ventana.
    """
    n = len(x)
    w = np.hanning(n)
    n_fft = 1 << int(np.ceil(np.log2(n * zero_pad)))
    X = np.fft.rfft(x * w, n=n_fft)
    mag = 2.0 * np.abs(X) / np.sum(w)
    f = np.fft.rfftfreq(n_fft, d=1.0 / fs)
    return f, mag


def mag_a_db(mag: np.ndarray, ref: float | None = None) -> np.ndarray:
    """Magnitud en dB: 20*log10(mag/ref). Por defecto ref = máximo del espectro."""
    ref = float(np.max(mag)) if ref is None else ref
    return 20.0 * np.log10(np.maximum(mag, 1e-12) / ref)


def _pico_parabolico(y_db: np.ndarray, k: int) -> tuple[float, float]:
    """Interpolación parabólica de un máximo local: (índice fraccionario, valor)."""
    a, b, c = y_db[k - 1], y_db[k], y_db[k + 1]
    den = a - 2.0 * b + c
    delta = 0.5 * (a - c) / den if den != 0 else 0.0
    return k + delta, b - 0.25 * (a - c) * delta


def autocorrelacion_normalizada(x: np.ndarray) -> np.ndarray:
    """r[l] = sum x[n]x[n+l] / sum x[n]^2 (insesgada), calculada vía FFT."""
    x = x - np.mean(x)
    n = len(x)
    n_fft = 1 << int(np.ceil(np.log2(2 * n)))
    X = np.fft.rfft(x, n=n_fft)
    r = np.fft.irfft(np.abs(X) ** 2, n=n_fft)[:n]
    r = r / r[0]
    return r * n / (n - np.arange(n))  # corrección del sesgo por solapamiento


def estimar_f0_autocorrelacion(x: np.ndarray, fs: float, f_min: float = 50.0, f_max: float = 2000.0, umbral: float = 0.85) -> float | None:
    """f0 = fs / (periodo en muestras), con el periodo tomado del primer máximo
    de la autocorrelación que alcanza ``umbral`` veces el mayor máximo local.
    Tomar el primer máximo "alto" (y no el máximo global) evita errores de octava.
    """
    r = autocorrelacion_normalizada(x)
    lag_min = max(2, int(fs / f_max))
    lag_max = min(int(fs / f_min), len(r) - 2)
    if lag_max <= lag_min + 2:
        return None
    idx = np.arange(lag_min + 1, lag_max)
    es_max = (r[idx] > r[idx - 1]) & (r[idx] >= r[idx + 1])
    candidatos = idx[es_max]
    if len(candidatos) == 0:
        return None
    ref = r[candidatos].max()
    lag = int(candidatos[np.argmax(r[candidatos] >= umbral * ref)])
    lag_frac, _ = _pico_parabolico(r, lag)
    return float(fs / lag_frac)


def estimar_f0(x: np.ndarray, fs: float, **kwargs) -> float | None:
    """f0 en dos pasos: (1) autocorrelación (estimación gruesa, sin errores de
    octava) y (2) refinamiento con el pico de la FFT más cercano (±4 %)."""
    f0_grueso = estimar_f0_autocorrelacion(x, fs, **kwargs)
    if f0_grueso is None:
        return None
    f, mag = espectro_magnitud(x, fs)
    zona = np.where(np.abs(f - f0_grueso) <= 0.04 * f0_grueso)[0]
    if len(zona) < 3:
        return f0_grueso
    k = int(zona[np.argmax(mag[zona])])
    if k < 1 or k >= len(f) - 1:
        return f0_grueso
    k_frac, _ = _pico_parabolico(mag_a_db(mag), k)
    return float(k_frac * (f[1] - f[0]))


def encontrar_parciales(
    f: np.ndarray,
    mag: np.ndarray,
    f0: float,
    umbral_db: float = -50.0,
    max_parciales: int = 10,
    f_max: float = 10000.0,
    separacion: float = 0.4,
) -> list[dict]:
    """Picos espectrales (parciales) más intensos, ordenados por frecuencia.

    Un pico es un máximo local por encima de ``umbral_db`` (dB respecto al pico
    mayor). Se aceptan de mayor a menor intensidad y se descartan los que quedan
    a menos de ``separacion * f0`` de uno ya aceptado (lóbulos laterales).
    Para cada uno se reporta la frecuencia, su razón f/f0 y su nivel en dB
    respecto al pico más cercano a f0 (la fundamental).
    """
    mag_db = mag_a_db(mag)
    medio = np.arange(1, len(f) - 1)
    es_pico = (mag_db[medio] > mag_db[medio - 1]) & (mag_db[medio] >= mag_db[medio + 1])
    es_pico &= (mag_db[medio] >= umbral_db) & (f[medio] <= f_max)
    candidatos = medio[es_pico]
    candidatos = candidatos[np.argsort(-mag_db[candidatos])]

    aceptados: list[int] = []
    for k in candidatos:
        if all(abs(f[k] - f[j]) >= separacion * f0 for j in aceptados):
            aceptados.append(int(k))

    df = f[1] - f[0]
    parciales = []
    for k in aceptados:
        k_frac, nivel_db = _pico_parabolico(mag_db, k)
        parciales.append({"frecuencia_hz": k_frac * df, "nivel_db_re_max": nivel_db})
    parciales.sort(key=lambda p: p["frecuencia_hz"])
    parciales = parciales[:max_parciales]

    if parciales:  # nivel relativo a la fundamental (parcial más cercano a f0)
        ref = min(parciales, key=lambda p: abs(p["frecuencia_hz"] - f0))["nivel_db_re_max"]
        for p in parciales:
            p["razon_f0"] = p["frecuencia_hz"] / f0
            p["nivel_db_re_f0"] = p["nivel_db_re_max"] - ref
    return parciales


def centroide_espectral(f: np.ndarray, mag: np.ndarray, f_max: float = 10000.0) -> float:
    """Centroide espectral (Hz): promedio de las frecuencias ponderado por la magnitud.
    Indica el "brillo" del sonido: mayor centroide = más energía en agudos."""
    m = f <= f_max
    return float(np.sum(f[m] * mag[m]) / np.sum(mag[m]))


def error_en_cents(f_medida: float, f_referencia: float) -> float:
    """Diferencia entre dos frecuencias en cents (100 cents = 1 semitono)."""
    return 1200.0 * float(np.log2(f_medida / f_referencia))
