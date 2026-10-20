# Protocolo para grabar audios reales

El programa acepta cualquier `.wav` PCM (8, 16, 24 o 32 bits; mono o estéreo; cualquier fs).
Los estéreo se promedian a mono y **cada archivo conserva su propia fs** (se documenta en
`results/metadatos_senales.csv`).

## 1. Qué grabar

* Mínimo 2 instrumentos (el proyecto contempla 4: cuerda, viento, percusión de altura definida).
* **Las mismas notas en todos los instrumentos** (recomendado: **A4** y **C5**). Así los
  instrumentos comparten f0 y las diferencias que se vean son de **timbre**.
* Una nota sostenida/golpeada y dejada sonar de 2 a 3 s; 2 o 3 tomas por nota.

## 2. Cómo grabar

1. Lugar silencioso (apagar ventiladores, TV, ventanas abiertas). Misma sala y misma distancia
   (20–30 cm del micrófono) para todos los instrumentos.
2. Celular: app de grabadora que permita formato sin comprimir, o grabar en `.m4a` y convertir.
3. Evitar saturación: el nivel de la grabación no debe llegar al máximo (la forma de onda no
   debe verse "recortada" en los picos).
4. Dejar ~0.5 s de silencio antes de tocar (permite medir el ruido de fondo).

## 3. Convertir a WAV (si hace falta)

* **Audacity** (gratis): *Archivo → Exportar → WAV (Microsoft) 16 bits PCM*; *Pistas → Mezclar → Mono*.
* **ffmpeg**: `ffmpeg -i entrada.m4a -ac 1 -ar 44100 -sample_fmt s16 guitarra_A4_01.wav`

## 4. Nombre y ubicación

`data/audio_real/instrumento_nota_toma.wav`, por ejemplo `data/audio_real/piano_A4_01.wav`.

## 5. Ejecutar el análisis

```bash
python -m src.main --audio-dir data/audio_real
```

Los resultados se guardan en `results/` (use `--salida results_real` para no sobrescribir los
de las señales simuladas).

## 6. Ficha de la grabación (completar y guardar en `docs/`)

| Campo | Valor |
|---|---|
| Dispositivo / micrófono | |
| Frecuencia de muestreo y bits de la grabación original | |
| Instrumento (modelo) | |
| Lugar | |
| Distancia al micrófono | |
| Fecha | |
