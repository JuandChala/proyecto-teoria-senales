# Modelo de síntesis de las señales simuladas

Las señales de `data/audio_sintetico/` se generan en `src/sintesis.py`. Son **simulaciones**:
sirven para tener señales con propiedades conocidas y comprobar que el análisis las recupera.
Los parámetros son **supuestos de modelado** inspirados en la acústica de instrumentos
(Fletcher & Rossing, 1998); no fueron medidos en instrumentos reales.

## Modelo general (síntesis aditiva)

$$x(t)=\sum_{k} A_k\,e^{-t/\tau_k}\,\sin\!\left(2\pi f_k t+\varphi_k\right)\cdot a(t) \;+\; w(t)$$

* $f_k$: frecuencia del parcial $k$ (múltiplo de $f_0$ en un sonido armónico).
* $A_k$, $\tau_k$: amplitud inicial y constante de decaimiento (s) del parcial.
* $\varphi_k$: fase inicial aleatoria (semilla fija).
* $a(t)$: envolvente de ataque (y de liberación en la flauta).
* $w(t)$: ruido de fondo gaussiano, $\sigma = 10^{-3}$ respecto a una señal de pico 1.

Al final la señal se escala a valor pico 0.8 y se guarda en 16 bits, 44 100 Hz, mono.

## Parámetros por instrumento

| Instrumento | Parciales $f_k$ | Amplitudes $A_k$ | Decaimiento $\tau_k$ | Ataque | Particularidad |
|---|---|---|---|---|---|
| **Guitarra** | $n f_0$, $n=1..12$ | $\lvert\sin(n\pi p)\rvert / n^{1.1}$, $p=0.18$ | $1.6/n^{0.7}$ s | ≈ 4 ms | $p$ = posición de pulsado: ciertos armónicos quedan atenuados; los agudos se apagan antes |
| **Piano** | $n f_0\sqrt{1+Bn^2}$, $B=4\times10^{-4}$, $n=1..14$ | $1/n^{1.1}$ | $3.0/(1+0.35(n-1))$ s | ≈ 3 ms | **Inarmonicidad**: la rigidez de la cuerda "estira" los parciales |
| **Flauta** | $n f_0$, $n=1..5$ | 1, 0.45, 0.15, 0.06, 0.03 | sostenido | rampa de 60 ms | Liberación de 200 ms al final; ruido de soplido ($\sigma=0.01$) |
| **Xilófono** | $f_0$, $3f_0$, $6f_0$ | 1, 0.5, 0.2 | 0.45, 0.15, 0.06 s | ≈ 1 ms | Barra afinada (parciales 1 : 3 : 6) y "clic" de la baqueta |

## Qué permite y qué no permite concluir

* Permite **validar el pipeline**: si el análisis detecta f0 correcta, la rejilla armónica, la
  inarmonicidad del piano o los parciales 1 : 3 : 6 del xilófono, el código funciona.
* **No** demuestra que los instrumentos reales se distingan exactamente así: las diferencias
  observadas fueron puestas por construcción en el modelo.
* Para la entrega final se recomienda reemplazar (o complementar) estas señales con
  grabaciones reales (`docs/protocolo_grabacion.md`).

## Referencia

Fletcher, N. H., & Rossing, T. D. (1998). *The Physics of Musical Instruments* (2.ª ed.). Springer.
