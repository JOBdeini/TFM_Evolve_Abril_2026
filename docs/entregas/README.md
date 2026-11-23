# Índice de entregas previas

Este directorio conserva cada ejercicio con numeración estable para que la evolución del TFM pueda seguirse sin sustituir entregas anteriores.

## Entrega 01 Ideas de producto

- `01_ideas_producto.md`
- Selección y justificación inicial de Vissotia como proyecto del TFM.

## Entrega 02 Datos y preparación

- `02_datos_y_preparacion.md`
- `02_datos_y_preparacion.docx`
- `../../scripts/prepare_vissotia_data.py`
- `../../data/entregas/02/README.md`
- `../../data/entregas/02/diccionario_datos.md`
- `../../requirements-entrega-02.txt`
- `../../tests/test_prepare_vissotia_data.py`

La Entrega 02 define las fuentes, la minimización de datos personales y el flujo Bronze, Silver y Gold para el caso de uso de valoración residencial. Incluye el contrato de las 30 columnas, controles efectivos antes de exportar, controles de calidad desglosados y un ejemplo ficticio reproducible. Los datos brutos y la salida local permanecen fuera del control de versiones.

## Entrega 03 Machine Learning

- `03_machine_learning.md`
- `03_machine_learning.docx`
- `../../scripts/train_vissotia_valuation.py`
- `../../notebooks/03b_validacion_externa_y_challenger.ipynb`
- `../../data/entregas/03/README.md`
- `../../requirements-entrega-03.txt`
- `../../tests/test_train_vissotia_valuation.py`

La Entrega 03 compara modelos sin fuga del objetivo, utiliza validación temporal y presenta errores por ciudad y tramo de precio. La validación externa incorpora una captura posterior, controla coincidencias exactas entre capturas, compara XGBoost con una referencia por zona y superficie, analiza la sensibilidad a valores atípicos y mantiene el nuevo modelo como challenger pendiente de otra prueba futura.

## Entrega 04 Diseño frontal y experiencia de usuario

- `04_diseno_frontal_ux.md`
- `04_diseno_frontal_ux.docx`
- `assets/04_mockup_valoracion_vissotia.png`
- `assets/04_mockup_valoracion_vissotia.html`
- `assets/04_vissotia_logo.png`

La Entrega 04 diseña el flujo principal de un valorador de vivienda autónomo. Permite realizar consultas anónimas o identificadas voluntariamente, recoge la ubicación y las características del inmueble y presenta la estimación central, el intervalo de incertidumbre, la cobertura y la calidad de los datos. El mockup diferencia los resultados del modelo de los escenarios comerciales posteriores y documenta la conexión prevista con Google Places, la API de predicción y la futura persistencia de clientes, inmuebles y valoraciones.


## Convención para próximas entregas

Las memorias se nombrarán con un prefijo numérico de dos dígitos, seguido de un nombre descriptivo. El código y los datos auxiliares se incorporarán en `scripts` y `data/entregas`, manteniendo la misma numeración de entrega.
