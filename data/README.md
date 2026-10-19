# Datos del proyecto

| Carpeta | Contenido | Origen |
|---|---|---|
| `audio_sintetico/` | 8 archivos `.wav` (4 instrumentos × notas A4 y C5), 44 100 Hz, 16 bits, mono, 2.0 s | **Generados por computador** con `python -m src.sintesis` (síntesis aditiva, semilla 2026). No son grabaciones de instrumentos reales. |
| `audio_real/` | Grabaciones propias del grupo (si existen) | Ver `docs/protocolo_grabacion.md` |

## Nomenclatura

`instrumento_nota_toma.wav` → `guitarra_A4_01.wav`

* **instrumento**: guitarra, flauta, piano, xilofono (cualquier nombre sirve; las gráficas
  solo usan colores fijos para estos cuatro).
* **nota**: nombre en notación anglosajona con octava (A4 = La4 = 440 Hz). Con ella el
  programa calcula la frecuencia fundamental esperada y la compara con la medida.
* **toma**: número de repetición.

## Regenerar las señales sintéticas

```bash
python -m src.sintesis                 # reescribe data/audio_sintetico/
```

La generación es determinista (misma semilla → mismos archivos).
Detalle de los modelos: [`docs/modelo_sintesis.md`](../docs/modelo_sintesis.md).
