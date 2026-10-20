"""Pruebas de las funciones de procesamiento con señales cuya respuesta se conoce.

Ejecutar desde la raíz del repositorio con cualquiera de:
    python -m pytest -q
    python -m tests.test_basico
"""
import numpy as np

from src.audio_io import escribir_wav, leer_wav, nota_a_frecuencia
from src.caracteristicas import (
    caracteristicas_temporales,
    encontrar_parciales,
    error_en_cents,
    espectro_magnitud,
    estimar_f0,
)
from src.ruido import agregar_ruido_awgn, medir_snr_db
from src.segmentacion import seleccionar_segmento
from src.sintesis import sintetizar

FS = 44100


def _seno(f, amp=1.0, dur=0.2, fs=FS):
    t = np.arange(int(dur * fs)) / fs
    return amp * np.sin(2 * np.pi * f * t)


def test_nota_a_frecuencia():
    assert abs(nota_a_frecuencia("A4") - 440.0) < 1e-9
    assert abs(nota_a_frecuencia("C4") - 261.6256) < 1e-3
    assert abs(nota_a_frecuencia("A5") - 880.0) < 1e-9


def test_wav_ida_y_vuelta(tmp_path):
    x = 0.5 * _seno(440)
    ruta = tmp_path / "prueba.wav"
    escribir_wav(ruta, x, FS)
    y, fs, bits, canales = leer_wav(ruta)
    assert fs == FS and bits == 16 and canales == 1
    assert np.max(np.abs(x - y)) < 1e-4  # error de cuantización de 16 bits


def test_caracteristicas_temporales_de_un_seno():
    x = _seno(1000, amp=0.5, dur=1.0)
    c = caracteristicas_temporales(x, FS)
    assert c["n_muestras"] == FS
    assert abs(c["duracion_s"] - 1.0) < 1e-12
    assert abs(c["rms"] - 0.5 / np.sqrt(2)) < 1e-3  # RMS de un seno = A/sqrt(2)
    assert abs(c["cruces_por_cero_s"] - 2000) < 5  # 2 cruces por periodo


def test_espectro_calibrado_en_amplitud():
    x = _seno(2000, amp=0.5)
    f, mag = espectro_magnitud(x, FS)
    k = np.argmax(mag)
    assert abs(f[k] - 2000) < 5
    assert abs(mag[k] - 0.5) < 0.02  # el pico de la FFT reproduce la amplitud


def test_estimar_f0_de_un_seno():
    for f0 in (110.0, 440.0, 1000.0):
        est = estimar_f0(_seno(f0), FS)
        assert abs(error_en_cents(est, f0)) < 1.0


def test_estimar_f0_con_armonicos_no_da_error_de_octava():
    x = sum(_seno(440 * n, amp=1.0 / n) for n in range(1, 6))
    assert abs(error_en_cents(estimar_f0(x, FS), 440.0)) < 1.0


def test_parciales_de_un_tono_armonico():
    x = _seno(440, 1.0) + _seno(880, 0.5) + _seno(1320, 0.25)
    f, mag = espectro_magnitud(x, FS)
    parciales = encontrar_parciales(f, mag, 440.0)
    razones = [round(p["razon_f0"]) for p in parciales]
    assert razones == [1, 2, 3]
    assert abs(parciales[1]["nivel_db_re_f0"] - (-6.02)) < 0.3  # amplitud mitad = -6 dB


def test_ruido_alcanza_la_snr_pedida():
    rng = np.random.default_rng(0)
    x = _seno(440, dur=1.0)
    for snr in (20, 10, 0):
        y = agregar_ruido_awgn(x, snr, rng)
        assert abs(medir_snr_db(x, y) - snr) < 0.5


def test_segmentos_comparables_tienen_el_mismo_tamano():
    n_esperado = int(round(0.2 * FS))
    for instrumento in ("guitarra", "flauta", "piano", "xilofono"):
        x = sintetizar(instrumento, "A4")
        segmento, _, _ = seleccionar_segmento(x, FS, 0.2, 0.1)
        assert len(segmento) == n_esperado


def test_sintesis_es_reproducible_y_tiene_la_f0_correcta():
    a = sintetizar("guitarra", "A4", semilla=1)
    b = sintetizar("guitarra", "A4", semilla=1)
    assert np.array_equal(a, b)
    segmento, _, _ = seleccionar_segmento(a, FS)
    assert abs(error_en_cents(estimar_f0(segmento, FS), 440.0)) < 2.0


if __name__ == "__main__":  # ejecución sin pytest
    import inspect
    import tempfile
    from pathlib import Path

    pruebas = [(n, f) for n, f in globals().items() if n.startswith("test_")]
    for nombre, funcion in pruebas:
        if "tmp_path" in inspect.signature(funcion).parameters:
            with tempfile.TemporaryDirectory() as d:
                funcion(Path(d))
        else:
            funcion()
        print("OK ", nombre)
    print(f"\n{len(pruebas)} pruebas pasaron correctamente.")
