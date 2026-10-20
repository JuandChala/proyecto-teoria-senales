# Parámetros y decisiones de diseño

| Decisión | Valor | Justificación |
|---|---|---|
| Frecuencia de muestreo | 44 100 Hz ($T_s \approx 22.68\ \mu s$) | Nyquist = 22 050 Hz. Las señales analizadas tienen parciales hasta ≈ 6 kHz, así que bastaría $f_s > 12$ kHz; 44.1 kHz es el estándar de audio y deja un margen amplio. |
| Resolución | 16 bits mono | 65 536 niveles; paso de cuantización $\Delta = 2/2^{16}\approx 3.05\times10^{-5}$; SNR de cuantización teórica de un seno a escala completa ≈ $6.02\cdot16+1.76 \approx 98$ dB. |
| Envolvente | RMS con ventana de 10 ms | Más larga que un periodo de la nota más grave (≈ 2.3 ms para A4) para que la envolvente no oscile con la onda. |
| Inicio de la nota | envolvente ≥ 10 % del máximo | Criterio simple y repetible para todos los instrumentos. |
| Segmento comparable | 0.20 s, empezando 0.10 s después del inicio | Descarta el transitorio de ataque (el más largo es el de la flauta: ≈ 60 ms) y deja el mismo número de muestras (8 820) en todos los instrumentos. |
| Ventana espectral | Hann | Reduce la fuga espectral (lóbulos laterales a −31 dB y decaimiento de 18 dB/octava) frente a la ventana rectangular (−13 dB); a cambio, el lóbulo principal es el doble de ancho (Harris, 1978). |
| Resolución en frecuencia | $\approx f_s/N = 44100/8820 = 5$ Hz (lóbulo principal de Hann: ±2 bins ≈ ±10 Hz) | Suficiente para separar parciales de una nota con $f_0 \ge 260$ Hz. |
| Relleno con ceros (al menos ×8) | $N_{FFT}$ = 2^17 = 131 072 (la siguiente potencia de 2 que supera 8·N) | Solo interpola el espectro (picos más suaves y mejor ubicados); **no** mejora la resolución real. |
| Estimación de $f_0$ | Autocorrelación (primer máximo ≥ 85 % del mayor) + refinamiento con pico de la FFT (±4 %) y parábola | El primer máximo alto evita errores de octava; el refinamiento da error < 1 cent. |
| Detección de parciales | máximos locales ≥ −50 dB respecto al pico mayor, separados ≥ 0.4·$f_0$, máx. 10 | Evita contar lóbulos laterales y ruido como parciales. |
| Acierto de $f_0$ | error < 50 cents (un cuarto de tono) | Criterio usual: por debajo de eso la nota sigue siendo la correcta. |
| Ruido | AWGN con varianza fijada por la SNR | $\sigma^2 = P_x / 10^{SNR/10}$; semilla fija (`--semilla`, por defecto 2026) para reproducir las figuras. |

## Limitaciones conocidas

* Con señales sintéticas, las diferencias entre instrumentos están impuestas por el modelo.
* La detección de inicio con umbral del 10 % puede fallar si la grabación real tiene ruido de
  fondo alto o ruidos previos a la nota; en ese caso conviene recortar el audio.
* El estimador de $f_0$ está pensado para notas individuales (monofónicas).

## Referencias

* Harris, F. J. (1978). On the use of windows for harmonic analysis with the discrete Fourier
  transform. *Proceedings of the IEEE, 66*(1), 51–83.
