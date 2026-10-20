"""Gráficas del proyecto. Todas se guardan como PNG (backend sin ventanas)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # solo se guardan imágenes; evita errores por falta de entorno gráfico
import matplotlib.pyplot as plt
import numpy as np

from .caracteristicas import espectro_magnitud, mag_a_db

COLORES = {"guitarra": "#1f77b4", "flauta": "#2ca02c", "piano": "#d62728", "xilofono": "#ff7f0e"}
DPI = 130


def _color(instrumento: str) -> str:
    return COLORES.get(instrumento, "#444444")


def _guardar(fig, ruta) -> str:
    fig.tight_layout()
    fig.savefig(ruta, dpi=DPI)
    plt.close(fig)
    return str(ruta)


def graficar_formas_de_onda(analisis: list[dict], nota: str, ruta) -> str:
    """Forma de onda completa de cada instrumento, con su envolvente y el segmento analizado."""
    n = len(analisis)
    fig, axs = plt.subplots(n, 1, figsize=(10, 2.1 * n), sharex=True, sharey=True)
    axs = np.atleast_1d(axs)
    for ax, a in zip(axs, analisis):
        s = a["senal"]
        t = np.arange(s.n_muestras) / s.fs
        ax.plot(t, s.x, lw=0.4, color=_color(s.instrumento))
        ax.plot(t, a["envolvente"], "k", lw=1.0, label="envolvente RMS (10 ms)")
        ax.plot(t, -a["envolvente"], "k", lw=1.0)
        ax.axvspan(a["i0"] / s.fs, (a["i0"] + len(a["segmento"])) / s.fs, color="gold", alpha=0.4, label="segmento analizado")
        ax.set_ylabel("Amplitud\n(escala completa)")
        ax.set_title(f"{s.instrumento} — nota {nota}   (fs = {s.fs} Hz, N = {s.n_muestras} muestras)", fontsize=10, loc="left")
        ax.grid(alpha=0.3)
    axs[0].legend(loc="upper right", fontsize=8)
    axs[-1].set_xlabel("Tiempo (s)")
    fig.suptitle(f"Representación temporal x(t) de la nota {nota} en cuatro instrumentos", y=1.0)
    return _guardar(fig, ruta)


def graficar_ventana_periodica(analisis: list[dict], nota: str, ruta, dur_ms: float = 12.0) -> str:
    """Zoom de ~12 ms del segmento: se ve la periodicidad y la forma de un periodo."""
    n = len(analisis)
    fig, axs = plt.subplots(n, 1, figsize=(10, 2.0 * n), sharex=True, sharey=True)
    axs = np.atleast_1d(axs)
    for ax, a in zip(axs, analisis):
        s = a["senal"]
        n_ventana = int(round(dur_ms * 1e-3 * s.fs))
        y = a["segmento"][:n_ventana]
        t_ms = 1000.0 * np.arange(len(y)) / s.fs
        ax.plot(t_ms, y, "-o", ms=2, lw=0.8, color=_color(s.instrumento))
        f0 = a["f0"]
        titulo = f"{s.instrumento}"
        if f0:
            t0 = 1000.0 / f0
            titulo += f" — f0 ≈ {f0:.1f} Hz  →  T0 = 1/f0 ≈ {t0:.2f} ms"
            for k in range(1, int(dur_ms / t0) + 1):
                ax.axvline(k * t0, color="gray", ls=":", lw=0.8)
        ax.set_title(titulo, fontsize=10, loc="left")
        ax.set_ylabel("Amplitud")
        ax.grid(alpha=0.3)
    axs[-1].set_xlabel("Tiempo dentro del segmento (ms)   [líneas punteadas: múltiplos de T0]")
    fig.suptitle(f"Ventana de {dur_ms:.0f} ms del segmento analizado — nota {nota}", y=1.0)
    return _guardar(fig, ruta)


def graficar_espectros(analisis: list[dict], nota: str, ruta, f_max: float = 6000.0) -> str:
    """Espectro de magnitud (dB) del segmento; líneas grises = rejilla armónica n·f0."""
    n = len(analisis)
    fig, axs = plt.subplots(n, 1, figsize=(10, 2.3 * n), sharex=True)
    axs = np.atleast_1d(axs)
    for ax, a in zip(axs, analisis):
        s = a["senal"]
        f, mag = espectro_magnitud(a["segmento"], s.fs)
        m = f <= f_max
        f0 = a["f0"]
        if f0:
            for k in range(1, int(f_max / f0) + 1):
                ax.axvline(k * f0, color="lightgray", ls="--", lw=0.8, zorder=0)
        ax.plot(f[m], mag_a_db(mag)[m], color=_color(s.instrumento), lw=1.0)
        for p in a["parciales"]:
            ax.plot(p["frecuencia_hz"], p["nivel_db_re_max"], "ko", ms=4)
        ax.set_ylim(-90, 5)
        ax.set_xlim(0, f_max)
        ax.set_ylabel("Magnitud (dB\nre. pico máx.)")
        ax.set_title(f"{s.instrumento} — {len(a['parciales'])} parciales marcados (puntos negros; se listan como máximo 10)", fontsize=10, loc="left")
        ax.grid(alpha=0.3)
    axs[-1].set_xlabel("Frecuencia (Hz)   [f = k·fs/N_fft;  líneas grises: n·f0]")
    fig.suptitle(f"Espectro de magnitud (FFT, ventana de Hann) del segmento — nota {nota}", y=1.0)
    return _guardar(fig, ruta)


def graficar_espectrogramas(analisis: list[dict], nota: str, ruta, f_max: float = 6000.0) -> str:
    """Espectrograma (STFT) de la nota completa: evolución de las frecuencias en el tiempo."""
    n = len(analisis)
    filas = int(np.ceil(n / 2))
    fig, axs = plt.subplots(filas, 2, figsize=(11, 3.0 * filas), squeeze=False)
    for ax in axs.ravel()[n:]:
        ax.axis("off")
    for ax, a in zip(axs.ravel(), analisis):
        s = a["senal"]
        _, _, _, im = ax.specgram(s.x, NFFT=2048, Fs=s.fs, noverlap=1536, cmap="magma")
        vmax = im.get_array().max()
        im.set_clim(vmax - 90, vmax)
        ax.set_ylim(0, f_max)
        ax.set_title(s.instrumento, fontsize=10, loc="left")
        ax.set_xlabel("Tiempo (s)")
        ax.set_ylabel("Frecuencia (Hz)")
    fig.suptitle(f"Espectrogramas (STFT, ventana de 2048 muestras ≈ 46 ms) — nota {nota}", y=1.0)
    return _guardar(fig, ruta)


def graficar_efecto_ruido(analisis: dict, versiones: list[tuple[float, np.ndarray]], ruta, f_max: float = 6000.0, dur_ms: float = 12.0) -> str:
    """Señal original y versiones con ruido: tiempo (izquierda) y espectro (derecha).

    ``versiones`` = lista de (snr_db, segmento); snr_db = inf significa sin ruido.
    """
    s = analisis["senal"]
    n = len(versiones)
    fig, axs = plt.subplots(n, 2, figsize=(11, 2.1 * n), sharex="col")
    for fila, (snr, y) in enumerate(versiones):
        etiqueta = "original (sin ruido)" if np.isinf(snr) else f"SNR = {snr:g} dB"
        n_ventana = int(round(dur_ms * 1e-3 * s.fs))
        axs[fila, 0].plot(1000.0 * np.arange(n_ventana) / s.fs, y[:n_ventana], lw=0.9, color=_color(s.instrumento))
        axs[fila, 0].set_ylabel("Amplitud")
        axs[fila, 0].set_title(etiqueta, fontsize=10, loc="left")
        axs[fila, 0].grid(alpha=0.3)
        f, mag = espectro_magnitud(y, s.fs)
        m = f <= f_max
        axs[fila, 1].plot(f[m], mag_a_db(mag, ref=1.0)[m], lw=0.8, color=_color(s.instrumento))
        axs[fila, 1].set_ylim(-110, 0)
        axs[fila, 1].set_ylabel("Magnitud (dB re. 1)")
        axs[fila, 1].grid(alpha=0.3)
    axs[-1, 0].set_xlabel("Tiempo (ms)")
    axs[-1, 1].set_xlabel("Frecuencia (Hz)")
    fig.suptitle(f"Efecto del ruido blanco gaussiano aditivo — {s.instrumento} {s.nota}", y=1.0)
    return _guardar(fig, ruta)


def graficar_robustez(resultados: dict[str, list[tuple[float, float]]], ruta, n_realizaciones: int = 20) -> str:
    """Tasa de acierto de f0 (error < 50 cents) en función de la SNR, por instrumento."""
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for instrumento, puntos in resultados.items():
        puntos = sorted(puntos)
        ax.plot([p[0] for p in puntos], [p[1] for p in puntos], "-o", color=_color(instrumento), label=instrumento)
    ax.set_xlabel("SNR (dB)")
    ax.set_ylabel("Estimaciones de f0 correctas (%)")
    ax.set_title(f"Robustez de la estimación de f0 frente al ruido ({n_realizaciones} realizaciones por punto)")
    ax.set_ylim(-5, 105)
    ax.grid(alpha=0.3)
    ax.legend()
    return _guardar(fig, ruta)


def graficar_aliasing(x: np.ndarray, fs: int, f0: float, factor: int, nombre: str, ruta, f_max: float = 8000.0) -> str:
    """Submuestreo ingenuo (x[::factor]) SIN filtro anti-aliasing y su efecto en el espectro."""
    x_sub = x[::factor]
    fs_sub = fs / factor
    f1, m1 = espectro_magnitud(x, fs)
    f2, m2 = espectro_magnitud(x_sub, fs_sub)

    fig, axs = plt.subplots(2, 1, figsize=(10, 6))
    sel = f1 <= f_max
    axs[0].plot(f1[sel], mag_a_db(m1)[sel], color="#1f77b4")
    axs[0].set_title(f"Original: fs = {fs} Hz  (frecuencia de Nyquist = {fs / 2:.0f} Hz)", fontsize=10, loc="left")

    axs[1].plot(f2, mag_a_db(m2), color="crimson")
    axs[1].axvline(fs_sub / 2, color="k", ls=":", lw=1)
    axs[1].text(fs_sub / 2, 3, " Nyquist", fontsize=8, va="bottom")
    db1 = mag_a_db(m1)
    n = 1
    while n * f0 < fs / 2:
        f_arm = n * f0
        existe = db1[np.abs(f1 - f_arm) <= 0.3 * f0].max() > -60  # el armónico está realmente en la señal
        if existe and f_arm > fs_sub / 2:
            f_alias = abs(f_arm - fs_sub * round(f_arm / fs_sub))  # frecuencia aparente tras el submuestreo
            axs[1].axvline(f_alias, color="red", ls="--", lw=0.8, alpha=0.8)
        n += 1
    axs[1].set_title(
        f"Submuestreado por {factor}: fs' = {fs_sub:.0f} Hz (Nyquist = {fs_sub / 2:.0f} Hz). "
        "Líneas rojas: alias previstos |f − k·fs'|",
        fontsize=10,
        loc="left",
    )
    for ax in axs:
        ax.set_ylim(-90, 8)
        ax.set_ylabel("Magnitud (dB re. máx.)")
        ax.grid(alpha=0.3)
    axs[0].set_xlim(0, f_max)
    axs[1].set_xlim(0, f_max)
    axs[1].set_xlabel("Frecuencia (Hz)")
    fig.suptitle(f"Aliasing al violar el teorema de muestreo — {nombre}", y=1.0)
    return _guardar(fig, ruta)
