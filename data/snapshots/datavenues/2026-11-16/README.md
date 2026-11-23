# Captura DataVenues del 16 de noviembre de 2026

Esta carpeta documenta la segunda captura de anuncios inmobiliarios destinada a la validación temporal externa y al posterior reentrenamiento del valorador de VISSOTIA. La extracción se realizó mediante DataVenues el 16 de noviembre de 2026.

## Finalidad

La captura de abril utilizada en las entregas anteriores no permite medir por sí sola el comportamiento del modelo ante anuncios obtenidos en una fecha posterior. Esta captura se conserva separada para:

1. evaluar el modelo vigente sobre datos posteriores a abril;
2. impedir que una vivienda republicada quede simultáneamente en entrenamiento y prueba;
3. comparar XGBoost con una referencia sencilla basada en zona y superficie;
4. analizar el error por municipio y tramo de precio;
5. incorporar los datos al entrenamiento de un modelo candidato únicamente después de cerrar la evaluación externa.

Los CSV de `bronze/` son ficheros fuente y no deben modificarse. Cualquier limpieza, normalización, deduplicación o anonimización debe producir una nueva capa derivada, manteniendo trazabilidad mediante el manifiesto y los hashes SHA-256.

## Inventario

| Municipio/carpeta | Archivo | Filas | Columnas | Fuente observada |
|---|---|---:|---:|---|
| A Coruña | `datavenues_a_coruna_fotocasa_2026-11-16.csv` | 507 | 41 | Fotocasa |
| Bilbao | `datavenues_bilbao_2026-11-16.csv` | 1.271 | 41 | Idealista (excepción aprobada por mayor cobertura) |
| Córdoba | `datavenues_cordoba_fotocasa_2026-11-16.csv` | 2.000 | 41 | Fotocasa |
| Cuenca | `dataVenues_cuenca_2026-11-16.csv` | 189 | 41 | Fotocasa |
| Granada | `dataVenues_granada_2026-11-16.csv` | 1.540 | 41 | Fotocasa |
| Madrid | `dataVenues_madrid_2026-11-16.csv` | 2.000 | 41 | Fotocasa |
| Sevilla | `dataVenues_sevilla_2026-11-16.csv` | 2.000 | 41 | Fotocasa |
| Valencia | `dataVenues_valencia_2026-11-16.csv` | 2.000 | 41 | Fotocasa |
| **Total** | **8 CSV** | **11.507** | **41 comunes** | — |

La revisión se ha realizado sobre la columna `Fuente`, considerando equivalentes las repeticiones del mismo portal dentro de un registro, por ejemplo `Fotocasa,Fotocasa`. Los ocho CSV comparten exactamente las mismas 41 columnas, con idénticos nombres y orden, codificación UTF-8 con BOM y separador por comas. El esquema común tiene la huella SHA-256 `ac9b1a7f53bac9d4168040d3999f1273b236e2009415fc51afb971f9245e2805`.

El CSV de Bilbao se mantiene por decisión del jefe de proyecto: en ese municipio Idealista ofrece una cobertura de anuncios superior a Fotocasa. Se trata de una excepción de procedencia documentada, no de una incompatibilidad estructural.

## Controles antes de usar la captura

- Eliminar en la capa de tratamiento la observación de Arrigorriaga incluida en el CSV de Bilbao. Esta regla está implementada y verificada en `notebooks/03b_validacion_externa_y_challenger.ipynb`; Bronze permanece intacto.
- Completar en `filters.md` los filtros exactos aplicados durante cada descarga.
- Excluir del test temporal únicamente las republicaciones confirmadas mediante coincidencia exacta del identificador técnico derivado de referencia o URL. La similitud de municipio, coordenadas, superficie, dormitorios y baños no se considera prueba suficiente porque puede corresponder a viviendas distintas de un mismo edificio.
- Excluir del modelado los campos identificativos o de contacto (`Anunciante`, `Empresa`, `Teléfono`, `Email`, `URL`, `Imagen`, títulos y comentarios), conservándolos solo localmente cuando sean imprescindibles para deduplicación controlada.

La captura es homogénea en esquema, pero no en portal. Como Bilbao e Idealista coinciden en esta muestra, el posible efecto del portal queda confundido con el efecto de la ciudad. Por ello, los resultados deberán desglosarse por municipio y mencionar esta limitación; no debe interpretarse una diferencia en Bilbao como causada exclusivamente por el mercado local o exclusivamente por el portal.

El notebook reproducible genera el Gold de noviembre, excluye republicaciones confirmadas del test externo, compara el champion con un baseline de zona y superficie y entrena un challenger sin promoverlo automáticamente. El baseline exige al menos 10 testigos en cada nivel y amplía progresivamente la referencia desde barrio a código postal, distrito, municipio y mediana global. Sus salidas se guardan en `local_output/`, protegido frente a Git.

## Protección y versionado

El `.gitignore` de esta carpeta excluye `bronze/`, las capas derivadas y los formatos de datos y modelos. Por tanto, Git solo debe versionar la documentación y el código reproducible, nunca los anuncios ni los datos de contacto.

El uso previsto es académico, local y sin redistribución. El acceso a través de la agencia y la disponibilidad técnica de la descarga no constituyen por sí mismos autorización para publicar los datos ni para incorporarlos a un producto comercial.

## Flujo previsto

```text
bronze (inmutable, local)
  -> validación de esquema y fuente
  -> silver (limpieza y normalización)
  -> control de republicaciones abril/noviembre
  -> external_test (evaluación congelada)
  -> candidate_training (solo tras cerrar la evaluación)
  -> modelo candidato/challenger
```

