"""Síntesis aditiva de notas de cuatro instrumentos (señales SIMULADAS).

Cada nota se modela como una suma de sinusoides (parciales):

    x(t) = sum_k  A_k * exp(-t / tau_k) * sin(2*pi*f_k*t + phi_k)

con amplitudes ``A_k``, constantes de decaimiento ``tau_k`` y frecuencias
``f_k`` distintas según el instrumento (ver ``docs/modelo_sintesis.md``).
Los parámetros son SUPUESTOS DE MODELADO inspirados en la acústica musical
(Fletcher & Rossing, 1998); no provienen de mediciones de instrumentos reales.

Uso:
    python -m src.sintesis                       # regenera data/audio_sintetico/
    python -m src.sintesis --salida otra_carpeta
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from .audio_io import escribir_wav, nota_a_frecuencia

FS_DEFECTO = 44100  # Hz (estándar de audio; Nyquist = 22050 Hz)
DURACION_DEFECTO = 2.0  # s
PICO_FINAL = 0.8  # la señal se escala para que su valor pico sea 0.8 (sin recorte)
RUIDO_FONDO = 1e-3  # desviación estándar del ruido de fondo (antes de escalar)

# --- Parámetros de cada modelo (se documentan en docs/modelo_sintesis.md) ---
GUITARRA_POSICION_PULSADO = 0.18  # fracción de la longitud de la cuerda
GUITARRA_N_ARMONICOS = 12
PIANO_INARMONICIDAD_B = 4e-4  # f_n = n*f0*sqrt(1 + B*n^2)
PIANO_N_PARCIALES = 14
FLAUTA_AMPLITUDES = (1.0, 0.45, 0.15, 0.06, 0.03)
XILOFONO_PARCIALES = ((1.0, 1.0, 0.45), (3.0, 0.5, 0.15), (6.0, 0.2, 0.06))  # (razón f/f0, amplitud, tau en s)


def _guitarra(f0, t, fs, rng):
    x = np.zeros_like(t)
    for n in range(1, GUITARRA_N_ARMONICOS + 1):
        if n * f0 >= fs / 2:
            break
        amp = abs(np.sin(n * np.pi * GUITARRA_POSICION_PULSADO)) / n**1.1
        tau = 1.6 / n**0.7  # los armónicos agudos se apagan antes
        x += amp * np.exp(-t / tau) * np.sin(2 * np.pi * n * f0 * t + rng.uniform(0, 2 * np.pi))
    return x * (1.0 - np.exp(-t / 0.004))  # ataque de ~4 ms


def _piano(f0, t, fs, rng):
    x = np.zeros_like(t)
    for n in range(1, PIANO_N_PARCIALES + 1):
        fn = n * f0 * np.sqrt(1.0 + PIANO_INARMONICIDAD_B * n**2)  # cuerda rígida: parciales "estirados"
        if fn >= fs / 2:
            break
        amp = 1.0 / n**1.1
        tau = 3.0 / (1.0 + 0.35 * (n - 1))
        x += amp * np.exp(-t / tau) * np.sin(2 * np.pi * fn * t + rng.uniform(0, 2 * np.pi))
    return x * (1.0 - np.exp(-t / 0.003))  # ataque de ~3 ms


def _flauta(f0, t, fs, rng):
    dur = t[-1] + 1.0 / fs
    ataque = np.clip(t / 0.06, 0.0, 1.0)  # rampa de 60 ms
    liberacion = np.clip((dur - t) / 0.20, 0.0, 1.0)  # rampa final de 200 ms
    env = np.minimum(ataque, liberacion)
    x = np.zeros_like(t)
    for n, amp in enumerate(FLAUTA_AMPLITUDES, start=1):
        x += amp * np.sin(2 * np.pi * n * f0 * t + rng.uniform(0, 2 * np.pi))
    x = x * env + 0.01 * rng.standard_normal(len(t)) * env  # + "soplido"
    return x


def _xilofono(f0, t, fs, rng):
    x = np.zeros_like(t)
    for razon, amp, tau in XILOFONO_PARCIALES:  # barra afinada: parciales en 1 : 3 : 6
        x += amp * np.exp(-t / tau) * np.sin(2 * np.pi * razon * f0 * t + rng.uniform(0, 2 * np.pi))
    x *= 1.0 - np.exp(-t / 0.001)  # ataque de ~1 ms
    x += 0.15 * rng.standard_normal(len(t)) * np.exp(-t / 0.002)  # "clic" de la baqueta
    return x


MODELOS = {
    "guitarra": _guitarra,
    "flauta": _flauta,
    "piano": _piano,
    "xilofono": _xilofono,
}


def sintetizar(instrumento: str, nota: str, fs: int = FS_DEFECTO, duracion: float = DURACION_DEFECTO, semilla: int = 0) -> np.ndarray:
    """Genera una nota sintética (escala ±1, valor pico = ``PICO_FINAL``)."""
    rng = np.random.default_rng(semilla)
    n = int(round(fs * duracion))
    t = np.arange(n) / fs
    x = MODELOS[instrumento](nota_a_frecuencia(nota), t, fs, rng)
    x = x / np.max(np.abs(x))
    x = x + RUIDO_FONDO * rng.standard_normal(n)  # ruido de fondo de "la sala"
    return PICO_FINAL * x / np.max(np.abs(x))


def generar_banco(directorio: str | Path, notas=("A4", "C5"), semilla: int = 2026) -> list[Path]:
    """Escribe un WAV por instrumento y nota: ``instrumento_nota_01.wav``."""
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)
    rutas = []
    for i, instrumento in enumerate(MODELOS):
        for j, nota in enumerate(notas):
            x = sintetizar(instrumento, nota, semilla=semilla + 100 * i + j)
            ruta = directorio / f"{instrumento}_{nota}_01.wav"
            escribir_wav(ruta, x, FS_DEFECTO)
            rutas.append(ruta)
    return rutas


def _cli() -> None:
    raiz = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Genera el banco de señales sintéticas de ejemplo.")
    p.add_argument("--salida", default=str(raiz / "data" / "audio_sintetico"))
    p.add_argument("--notas", nargs="+", default=["A4", "C5"])
    p.add_argument("--semilla", type=int, default=2026)
    args = p.parse_args()
    for ruta in generar_banco(args.salida, args.notas, args.semilla):
        print("generado:", ruta)


if __name__ == "__main__":
    _cli()
