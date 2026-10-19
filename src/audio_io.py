"""Entrada/salida de audio.

Lectura y escritura de archivos WAV (PCM) usando solo el módulo estándar
``wave`` + NumPy, y utilidades para interpretar el nombre de cada archivo
(``instrumento_nota_toma.wav``, por ejemplo ``guitarra_A4_01.wav``).
"""
from __future__ import annotations

import re
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_SEMITONOS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def nota_a_frecuencia(nota: str) -> float:
    """Frecuencia (Hz) de una nota en temperamento igual con La4 = 440 Hz.

    Ejemplos: ``"A4" -> 440.0``, ``"C4" -> 261.63``, ``"C#5" -> 554.37``.
    Se usa el número MIDI: ``midi = 12*(octava+1) + semitono`` y
    ``f = 440 * 2**((midi-69)/12)``.
    """
    m = re.fullmatch(r"([A-Ga-g])([#b]?)(-?\d)", nota.strip())
    if m is None:
        raise ValueError(f"Nota no reconocida: {nota!r} (use formato 'A4', 'C#5', 'Bb3')")
    letra, alteracion, octava = m.group(1).upper(), m.group(2), int(m.group(3))
    midi = 12 * (octava + 1) + _SEMITONOS[letra]
    midi += 1 if alteracion == "#" else -1 if alteracion == "b" else 0
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


@dataclass
class Senal:
    """Una grabación (o señal sintética) ya cargada en memoria."""

    nombre: str
    instrumento: str
    nota: str | None
    toma: str | None
    fs: int  # frecuencia de muestreo (Hz)
    x: np.ndarray  # muestras en punto flotante, escala completa = ±1
    bits: int  # resolución original del archivo
    canales_originales: int
    ruta: str

    @property
    def n_muestras(self) -> int:
        return len(self.x)

    @property
    def ts(self) -> float:
        """Periodo de muestreo Ts = 1/fs (s)."""
        return 1.0 / self.fs

    @property
    def duracion(self) -> float:
        return self.n_muestras / self.fs

    @property
    def f0_nominal(self) -> float | None:
        """Frecuencia fundamental esperada según la nota del nombre del archivo."""
        if not self.nota:
            return None
        try:
            return nota_a_frecuencia(self.nota)
        except ValueError:
            return None


def leer_wav(ruta: str | Path) -> tuple[np.ndarray, int, int, int]:
    """Lee un WAV PCM y devuelve ``(x, fs, bits, canales)``.

    ``x`` es mono (si el archivo es estéreo se promedian los canales) y está
    normalizada a [-1, 1). Soporta 8, 16, 24 y 32 bits.
    """
    with wave.open(str(ruta), "rb") as w:
        fs = w.getframerate()
        canales = w.getnchannels()
        ancho = w.getsampwidth()
        crudo = w.readframes(w.getnframes())

    if ancho == 1:  # 8 bits: enteros sin signo centrados en 128
        x = (np.frombuffer(crudo, dtype=np.uint8).astype(np.float64) - 128.0) / 128.0
    elif ancho == 2:
        x = np.frombuffer(crudo, dtype="<i2").astype(np.float64) / 32768.0
    elif ancho == 3:  # 24 bits: se arma el entero con signo a mano
        b = np.frombuffer(crudo, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        v = np.where(v >= 2**23, v - 2**24, v)
        x = v.astype(np.float64) / 2.0**23
    elif ancho == 4:
        x = np.frombuffer(crudo, dtype="<i4").astype(np.float64) / 2.0**31
    else:
        raise ValueError(f"Ancho de muestra no soportado: {ancho} bytes")

    if canales > 1:
        x = x.reshape(-1, canales).mean(axis=1)
    return x, fs, 8 * ancho, canales


def escribir_wav(ruta: str | Path, x: np.ndarray, fs: int) -> None:
    """Guarda ``x`` (escala ±1) como WAV mono de 16 bits."""
    pcm = np.clip(np.round(np.asarray(x) * 32767.0), -32768, 32767).astype("<i2")
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(fs))
        w.writeframes(pcm.tobytes())


def interpretar_nombre(ruta: str | Path) -> tuple[str, str | None, str | None]:
    """``guitarra_A4_01.wav`` -> ``("guitarra", "A4", "01")``."""
    partes = Path(ruta).stem.split("_")
    instrumento = partes[0].lower()
    nota = partes[1] if len(partes) > 1 else None
    toma = partes[2] if len(partes) > 2 else None
    return instrumento, nota, toma


def cargar_banco(directorio: str | Path) -> list[Senal]:
    """Carga todos los ``.wav`` de una carpeta, ordenados por nombre."""
    directorio = Path(directorio)
    rutas = sorted(p for p in directorio.glob("*") if p.suffix.lower() == ".wav")
    banco = []
    for ruta in rutas:
        x, fs, bits, canales = leer_wav(ruta)
        instrumento, nota, toma = interpretar_nombre(ruta)
        banco.append(
            Senal(
                nombre=ruta.stem,
                instrumento=instrumento,
                nota=nota,
                toma=toma,
                fs=fs,
                x=x,
                bits=bits,
                canales_originales=canales,
                ruta=str(ruta),
            )
        )
    return banco
