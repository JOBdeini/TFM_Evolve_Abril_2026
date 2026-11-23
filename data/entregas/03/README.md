# Resultados locales de la Entrega 03

Esta carpeta contiene las instrucciones de reproducción del experimento de
Machine Learning. Los resultados generados y el artefacto del modelo se guardan
en `local_output/`, que está excluido de Git para evitar publicar datos
derivados de una fuente cuya redistribución debe validarse.

El experimento utiliza el Gold creado en la Entrega 02 sin modificarlo:

```bash
python scripts/train_vissotia_valuation.py \
  --input data/entregas/02/local_output/vissotia_valoracion_gold.csv \
  --output-dir data/entregas/03/local_output
```

El script requiere el contrato actualizado de 30 columnas, con
`fecha_publicacion` y `fecha_extraccion` separadas y la condición `es_atico`
independiente de `planta_num`. La primera fecha ordena la validación temporal;
la segunda se conserva como trazabilidad y no se utiliza como predictor.

Los principales resultados son:

- comparación del baseline, Ridge y XGBoost en un test temporal;
- validación temporal expansiva dentro del conjunto de entrenamiento;
- errores de XGBoost por ciudad y tramo de precio;
- prueba exploratoria dejando cada ciudad completamente fuera del entrenamiento;
- importancia de variables, predicciones del test y gráficos;
- artefacto `modelo_valoracion_inicial_xgboost.joblib`.

La validación externa se ejecuta con
`notebooks/03b_validacion_externa_y_challenger.ipynb`. Utiliza la captura del
16 de noviembre de 2026, excluye coincidencias exactas entre capturas, compara
el champion con un baseline de zona y superficie y presenta resultados por
ciudad y tramo de precio. El modelo combinado se guarda como challenger y no
se promociona hasta disponer de otra captura futura.

`dias_publicado` se excluye porque solo existe después de publicar. `demanda`
también queda fuera de esta versión, pero por una razón diferente: antes de
probarla como contexto de mercado debe documentarse su fórmula y disponibilidad
temporal para descartar fuga de información.

El modelo es académico y estima precio anunciado, no precio de cierre ni una
tasación oficial. No debe integrarse en producción hasta completar la
validación, la calibración de intervalos y las pruebas con datos autorizados.
