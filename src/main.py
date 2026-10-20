"""Demostración principal (Entrega 2).

Ejecutar desde la raíz del repositorio:

    python -m src.main                      # señales sintéticas de data/audio_sintetico
    python -m src.main --audio-dir data/audio_real     # grabaciones propias
    python ejecutar_demo.py                 # equivalente (para IDEs con botón "Run")

Pasos: 1) cargar señales y documentar fs/Ts/N  2) caracterización temporal
3) segmento comparable  4) análisis frecuencial  5) ruido controlado
6) demostración de aliasing.  Todo se guarda en ``results/``.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

from . import graficas
from .audio_io import Senal, cargar_banco
from .caracteristicas import (
    caracteristicas_temporales,
    centroide_espectral,
    encontrar_parciales,
    error_en_cents,
    espectro_magnitud,
    estimar_f0,
    parametros_envolvente,
)
from .ruido import agregar_ruido_awgn, medir_snr_db
from .segmentacion import envolvente_rms, seleccionar_segmento

RAIZ = Path(__file__).resolve().parent.parent
SNR_BARRIDO = [30, 20, 10, 0, -5, -10, -15, -20]  # dB, para el experimento de robustez
REALIZACIONES = 40
UMBRAL_ACIERTO_CENTS = 50.0  # un cuarto de tono
FACTOR_ALIASING = 9  # 44100/9 = 4900 Hz (no es múltiplo de f0, así los alias se distinguen)


# ----------------------------------------------------------------------
# Análisis de una señal
# ----------------------------------------------------------------------
def analizar_senal(s: Senal, dur_seg: float, desplazamiento: float) -> dict:
    """Aplica toda la caracterización a una señal y devuelve un diccionario de resultados."""
    segmento, i0, inicio = seleccionar_segmento(s.x, s.fs, dur_seg, desplazamiento)
    f0 = estimar_f0(segmento, s.fs)
    f, mag = espectro_magnitud(segmento, s.fs)
    parciales = encontrar_parciales(f, mag, f0) if f0 else []
    return {
        "senal": s,
        "temporales": caracteristicas_temporales(s.x, s.fs),
        "envolvente": envolvente_rms(s.x, s.fs),
        "env_params": parametros_envolvente(s.x, s.fs),
        "inicio": inicio,
        "i0": i0,
        "segmento": segmento,
        "f0": f0,
        "error_cents": error_en_cents(f0, s.f0_nominal) if (f0 and s.f0_nominal) else float("nan"),
        "parciales": parciales,
        "centroide": centroide_espectral(f, mag),
    }


def elegir_comparacion(analisis: list[dict], nota: str, instrumentos: list[str] | None = None) -> tuple[list[dict], str]:
    """Un análisis por instrumento, todos con la misma nota (para aislar el timbre)."""
    notas = {}
    for a in analisis:
        notas.setdefault(a["senal"].nota, set()).add(a["senal"].instrumento)
    if nota not in notas or len(notas[nota]) < 2:  # nota pedida no sirve: usar la más compartida
        nota = max(notas, key=lambda k: len(notas[k]))
    elegidos, vistos = [], set()
    for a in analisis:
        s = a["senal"]
        if s.nota == nota and s.instrumento not in vistos and (instrumentos is None or s.instrumento in instrumentos):
            elegidos.append(a)
            vistos.add(s.instrumento)
    return elegidos, nota


# ----------------------------------------------------------------------
# Experimento de ruido
# ----------------------------------------------------------------------
def experimento_robustez(comparacion: list[dict], semilla: int) -> list[dict]:
    """Tasa de acierto de f0 vs SNR con ``REALIZACIONES`` ruidos distintos por punto."""
    filas = []
    for i, a in enumerate(comparacion):
        s = a["senal"]
        if not s.f0_nominal:
            continue
        for snr in SNR_BARRIDO:
            rng = np.random.default_rng([semilla, i, int(snr) + 100])
            errores = []
            for _ in range(REALIZACIONES):
                y = agregar_ruido_awgn(a["segmento"], snr, rng)
                f0 = estimar_f0(y, s.fs)
                errores.append(abs(error_en_cents(f0, s.f0_nominal)) if f0 else np.inf)
            errores = np.array(errores)
            filas.append(
                {
                    "instrumento": s.instrumento,
                    "nota": s.nota,
                    "snr_db": snr,
                    "tasa_acierto_pct": 100.0 * np.mean(errores < UMBRAL_ACIERTO_CENTS),
                    "mediana_error_abs_cents": float(np.median(errores)),
                }
            )
    return filas


# ----------------------------------------------------------------------
# Escritura de tablas
# ----------------------------------------------------------------------
def _csv(ruta: Path, filas: list[dict]) -> None:
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()), lineterminator="\n")
        w.writeheader()
        for fila in filas:
            w.writerow({k: (float(f"{v:.6g}") + 0.0 if isinstance(v, float) else v) for k, v in fila.items()})


def tabla_metadatos(analisis: list[dict]) -> list[dict]:
    filas = []
    for a in analisis:
        s, t = a["senal"], a["temporales"]
        filas.append(
            {
                "archivo": s.nombre,
                "instrumento": s.instrumento,
                "nota": s.nota,
                "fs_hz": s.fs,
                "Ts_s": s.ts,
                "bits": s.bits,
                "canales_originales": s.canales_originales,
                **t,
            }
        )
    return filas


def tabla_segmentos(analisis: list[dict]) -> list[dict]:
    filas = []
    for a in analisis:
        s = a["senal"]
        filas.append(
            {
                "archivo": s.nombre,
                "instrumento": s.instrumento,
                "nota": s.nota,
                "inicio_nota_s": a["inicio"] / s.fs,
                "inicio_segmento_s": a["i0"] / s.fs,
                "n_muestras_segmento": len(a["segmento"]),
                "f0_nominal_hz": s.f0_nominal,
                "f0_estimada_hz": a["f0"],
                "error_cents": a["error_cents"],
                "T0_ms": 1000.0 / a["f0"] if a["f0"] else float("nan"),
                "tiempo_ataque_ms": a["env_params"]["tiempo_ataque_ms"],
                "tiempo_a_mitad_s": a["env_params"]["tiempo_a_mitad_s"],
                "centroide_hz": a["centroide"],
                "n_parciales": len(a["parciales"]),
            }
        )
    return filas


def tabla_parciales(comparacion: list[dict]) -> list[dict]:
    filas = []
    for a in comparacion:
        for i, p in enumerate(a["parciales"], start=1):
            filas.append(
                {
                    "instrumento": a["senal"].instrumento,
                    "nota": a["senal"].nota,
                    "parcial": i,
                    "frecuencia_hz": p["frecuencia_hz"],
                    "razon_f_f0": p["razon_f0"],
                    "nivel_db_re_f0": p["nivel_db_re_f0"],
                }
            )
    return filas


# ----------------------------------------------------------------------
# Interacción opcional
# ----------------------------------------------------------------------
def preguntar_opciones(analisis: list[dict], nota: str) -> tuple[str, list[str] | None]:
    """Menú simple: nota a comparar e instrumentos a incluir."""
    notas = sorted({a["senal"].nota for a in analisis if a["senal"].nota})
    instrumentos = sorted({a["senal"].instrumento for a in analisis})
    print(f"\nNotas disponibles: {', '.join(notas)}")
    resp = input(f"Nota para comparar instrumentos (Enter = {nota}): ").strip()
    nota = resp or nota
    print(f"Instrumentos disponibles: {', '.join(instrumentos)}")
    resp = input("Instrumentos a comparar, separados por coma (Enter = todos): ").strip()
    elegidos = [r.strip().lower() for r in resp.split(",") if r.strip()] or None
    return nota, elegidos


# ----------------------------------------------------------------------
# Programa principal
# ----------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Reconocimiento de instrumentos por análisis espectral — Entrega 2")
    p.add_argument("--audio-dir", default=str(RAIZ / "data" / "audio_sintetico"), help="carpeta con archivos .wav")
    p.add_argument("--salida", default=str(RAIZ / "results"), help="carpeta de resultados")
    p.add_argument("--nota", default="A4", help="nota usada para comparar instrumentos")
    p.add_argument("--duracion-segmento", type=float, default=0.20, help="duración del segmento (s)")
    p.add_argument("--desplazamiento", type=float, default=0.10, help="tiempo descartado tras el inicio de la nota (s)")
    p.add_argument("--snr", type=float, nargs="+", default=[20.0, 10.0, 0.0], help="SNR (dB) de la figura de ruido")
    p.add_argument("--semilla", type=int, default=2026, help="semilla del generador de ruido (reproducibilidad)")
    p.add_argument("--interactivo", action="store_true", help="preguntar nota e instrumentos por consola")
    args = p.parse_args(argv)

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    # 1. ADQUISICIÓN / CARGA -------------------------------------------------
    banco = cargar_banco(args.audio_dir)
    if not banco:
        print(f"No se encontraron archivos .wav en {args.audio_dir}.")
        print("Para generar las señales sintéticas de ejemplo ejecute:  python -m src.sintesis")
        return 1
    print(f"Señales cargadas desde {args.audio_dir}: {len(banco)}")
    print(f"{'archivo':<22}{'fs (Hz)':>9}{'Ts (µs)':>10}{'N':>9}{'dur (s)':>9}{'bits':>6}")
    for s in banco:
        print(f"{s.nombre:<22}{s.fs:>9}{1e6 * s.ts:>10.2f}{s.n_muestras:>9}{s.duracion:>9.2f}{s.bits:>6}")

    # 2-4. CARACTERIZACIÓN TEMPORAL, SEGMENTACIÓN Y ANÁLISIS FRECUENCIAL --------
    analisis = [analizar_senal(s, args.duracion_segmento, args.desplazamiento) for s in banco]
    nota, instrumentos = args.nota, None
    if args.interactivo:
        nota, instrumentos = preguntar_opciones(analisis, nota)
    comparacion, nota = elegir_comparacion(analisis, nota, instrumentos)
    if len(comparacion) < 2:
        print("Se necesitan al menos dos instrumentos con la misma nota para comparar.")
        return 1

    _csv(salida / "metadatos_senales.csv", tabla_metadatos(analisis))
    _csv(salida / "caracteristicas_segmentos.csv", tabla_segmentos(analisis))
    _csv(salida / f"parciales_{nota}.csv", tabla_parciales(comparacion))

    print(f"\nComparación de timbre con la nota {nota}:")
    print(f"{'instrumento':<11}{'f0 est. (Hz)':>13}{'error (cents)':>14}{'ataque (ms)':>12}{'t½ (s)':>8}{'centroide (Hz)':>15}")
    for a in comparacion:
        print(
            f"{a['senal'].instrumento:<11}{a['f0']:>13.2f}{a['error_cents']:>14.2f}"
            f"{a['env_params']['tiempo_ataque_ms']:>12.1f}{a['env_params']['tiempo_a_mitad_s']:>8.2f}{a['centroide']:>15.0f}"
        )

    figuras = [
        graficas.graficar_formas_de_onda(comparacion, nota, salida / f"01_formas_de_onda_{nota}.png"),
        graficas.graficar_ventana_periodica(comparacion, nota, salida / f"02_ventana_periodica_{nota}.png"),
        graficas.graficar_espectros(comparacion, nota, salida / f"03_espectros_{nota}.png"),
        graficas.graficar_espectrogramas(comparacion, nota, salida / f"04_espectrogramas_{nota}.png"),
    ]

    # 5. RUIDO / DEGRADACIÓN --------------------------------------------------
    objetivo = next((a for a in comparacion if a["senal"].instrumento == "guitarra"), comparacion[0])
    rng = np.random.default_rng(args.semilla)
    versiones = [(np.inf, objetivo["segmento"])]
    for snr in args.snr:
        y = agregar_ruido_awgn(objetivo["segmento"], snr, rng)
        print(f"Ruido añadido: SNR pedida = {snr:g} dB, SNR medida = {medir_snr_db(objetivo['segmento'], y):.2f} dB")
        versiones.append((snr, y))
    figuras.append(graficas.graficar_efecto_ruido(objetivo, versiones, salida / f"05_efecto_ruido_{objetivo['senal'].instrumento}_{nota}.png"))

    robustez = experimento_robustez(comparacion, args.semilla)
    if robustez:
        _csv(salida / "robustez_ruido.csv", robustez)
        curvas: dict[str, list[tuple[float, float]]] = {}
        for fila in robustez:
            curvas.setdefault(fila["instrumento"], []).append((fila["snr_db"], fila["tasa_acierto_pct"]))
        figuras.append(graficas.graficar_robustez(curvas, salida / "06_robustez_f0_vs_snr.png", REALIZACIONES))

    # 6. MUESTREO: ALIASING ---------------------------------------------------
    rico = max(comparacion, key=lambda a: len(a["parciales"]))  # señal con más parciales
    s = rico["senal"]
    figuras.append(graficas.graficar_aliasing(s.x[rico["i0"] : rico["i0"] + 4 * len(rico["segmento"])], s.fs, rico["f0"], FACTOR_ALIASING, f"{s.instrumento} {s.nota}", salida / "07_aliasing.png"))

    print("\nFiguras y tablas guardadas en:", salida)
    for f in figuras:
        print("  -", Path(f).name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
