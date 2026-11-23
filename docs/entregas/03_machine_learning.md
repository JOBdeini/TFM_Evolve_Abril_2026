# Proyecto final Evolve Entrega 03 Machine Learning

## VISSOTIA valoración inicial de viviendas

Esta entrega desarrolla y evalúa una primera capacidad de Machine Learning para VISSOTIA: estimar un precio orientativo de publicación antes de que una vivienda salga al mercado. El experimento parte del dataset Gold de la Entrega 02, separa las variables disponibles antes de publicar de las señales que aparecen después y compara una referencia sencilla con Ridge y XGBoost.

La solución elegida para el prototipo académico es XGBoost. En el test temporal de la captura de abril obtiene un MAE de 63.876 euros, un R² de 0,879 y una mediana de error porcentual absoluto del 14,88 %. Mejora el MAE del baseline en un 65,8 % y el de Ridge en un 22,5 %. Una validación posterior con la captura del 16 de noviembre confirma la utilidad del modelo en Madrid, Sevilla y Córdoba, pero detecta una pérdida clara al extrapolar a ciudades no vistas. El resultado permite demostrar valor para un MVP controlado, pero todavía no justifica una valoración nacional ni una integración automática en la versión publicada de VISSOTIA.

## 1 Qué problema resuelve el modelo

VISSOTIA reúne en una única fuente de verdad la información del inmueble, su contexto territorial, la preparación documental y las acciones de comercialización. Dentro de ese flujo, el modelo resuelve un problema de regresión supervisada: estimar el precio de oferta de una vivienda a partir de sus características y ubicación.

El usuario principal es el profesional inmobiliario que prepara la salida al mercado del inmueble. La estimación no sustituye su criterio, una tasación homologada ni una negociación con el propietario. Sirve como referencia cuantitativa para contrastar el precio propuesto, detectar valores que merecen revisión y explicar un rango razonable con datos comparables.

La decisión asistida es el posicionamiento inicial del inmueble. El usuario podrá comparar el precio que pretende publicar con tres salidas del sistema: una estimación central, un intervalo de incertidumbre y una advertencia sobre la cobertura de los datos. Si el precio propuesto queda lejos del intervalo, VISSOTIA deberá pedir una revisión humana y mostrar qué información falta.

Esta entrega separa dos momentos que no deben mezclarse:

- **Valoración inicial.** Se realiza antes de publicar. Puede usar ubicación, superficie, tipología, dormitorios, baños, planta, conservación y equipamiento.
- **Seguimiento comercial.** Se realiza después de publicar. Puede utilizar días en mercado, demanda recibida y evolución del precio para recomendar mantenerlo o revisarlo.

El modelo de esta entrega cubre únicamente la valoración inicial. `dias_publicado` y `demanda` se conservan en el Gold, pero no participan en este primer entrenamiento por motivos distintos. `dias_publicado` solo existe después de publicar y, con una única fecha de extracción, equivale a la antigüedad del anuncio en la captura. `demanda` sí puede representar contexto de mercado disponible por tipología y zona, pero se excluye hasta documentar con precisión cómo la calcula DataVenues, cuándo queda disponible y si incorpora información posterior. Solo después podrá evaluarse mediante una ablación temporal sin fuga.

La variable objetivo es `precio_objetivo_eur`, que representa precio anunciado. No disponemos todavía de precios efectivos de cierre. En consecuencia, el modelo aprende el comportamiento de la oferta publicada y no el valor final de transacción.

## 2 Datos de entrada y salida

El experimento inicial utiliza las 5.605 observaciones y las 30 columnas del Gold generado en la Entrega 02. `fecha_publicacion` abarca desde el 1 de enero de 2018 hasta el 4 de abril de 2026; `fecha_extraccion` es el 6 de abril de 2026 para toda la captura. La muestra se concentra especialmente en 2025 y 2026 y la cobertura geográfica inicial está limitada a Madrid, Sevilla y Córdoba.

### Variables utilizadas

| Grupo | Variables | Disponibilidad en el momento de uso |
| --- | --- | --- |
| Características físicas | `superficie_m2`, `dormitorios`, `banos`, `planta_num`, `es_atico`, `tipologia` | Declaradas por el usuario o contrastadas con documentación y Catastro |
| Equipamiento | `ascensor`, `garaje`, `trastero`, `terraza`, `piscina`, `zonas_verdes`, `zona_deportiva`, `aire_acondicionado` | Disponibles antes de publicar |
| Estado | `conservacion` | Disponible si se ha documentado; se imputa dentro del entrenamiento cuando falta |
| Ubicación minimizada | `codigo_postal`, `municipio`, `provincia`, `distrito`, `barrio`, `latitud_aprox`, `longitud_aprox`, `origen_dataset` | Disponible antes de publicar, sin dirección exacta en el Gold |
| Contexto temporal | Año y mes derivados de `fecha_publicacion` durante el entrenamiento | En uso se sustituyen por el año y mes de la solicitud de valoración |

Los valores numéricos ausentes se imputan con la mediana calculada solo en el conjunto de entrenamiento y se añade un indicador de ausencia. Las variables categóricas se imputan con la moda del entrenamiento y se codifican con one hot encoding. Las categorías desconocidas en validación no detienen la predicción.

### Variables excluidas

| Variable o grupo | Motivo de exclusión |
| --- | --- |
| Precio actual, precio por metro cuadrado y agregaciones construidas con el objetivo | Producirían fuga de información y una predicción circular |
| `dias_publicado` | Solo existe después de publicar y pertenece al futuro modelo de seguimiento |
| `demanda` | Se excluye hasta documentar su fórmula, granularidad y disponibilidad temporal; después se evaluará mediante ablación |
| `id_observacion` | Identificador técnico sin significado predictivo |
| `fecha_publicacion` completa | Se usa para ordenar y separar los datos; el modelo recibe únicamente año y mes del contexto de mercado |
| `fecha_extraccion` | Es trazabilidad de la captura y resulta constante en este conjunto; no aporta señal predictiva |
| `operacion` | Es constante porque el Gold está filtrado a venta |
| Datos personales, texto libre, URL e imagen | Fueron eliminados en la Entrega 02 por privacidad y falta de necesidad |

El notebook histórico del proyecto alcanzaba resultados mucho más altos, pero incluía precio por metro cuadrado y medias territoriales calculadas antes de separar entrenamiento y prueba. Esta nueva versión elimina esas variables y asume métricas más moderadas a cambio de una evaluación defendible.

La salida esperada para cada inmueble es:

1. Precio orientativo central en euros.
2. Intervalo empírico aproximado al 90 % calibrado con residuos de validación temporal.
3. Versión del modelo y fecha de predicción.
4. Indicador de cobertura y calidad de los datos de entrada.
5. Mensaje de cautela: precio de publicación estimado, no precio de cierre ni tasación oficial.

El intervalo no se fija de forma arbitraria. Se calcula en escala logarítmica con los residuos fuera de muestra de las particiones temporales de validación y una corrección conformal finita. En el test final cubre el 91,4 % de los precios observados, cercano al 90 % nominal. Es un intervalo empírico del experimento, no una garantía individual; su amplitud elevada refleja la incertidumbre de los datos actuales.

## 3 Baseline y selección de modelos

Se comparan tres enfoques mediante el mismo conjunto de variables y el mismo test temporal.

### Baseline mediana

El baseline devuelve la mediana de los precios del conjunto de entrenamiento. No utiliza las características del inmueble. Es una referencia exigente en el sentido correcto: cualquier modelo útil debe mejorarla con claridad.

### Ridge

Ridge es un modelo lineal regularizado. Se entrena sobre el logaritmo del precio para reducir el efecto de los inmuebles más caros. Aporta una referencia interpretable y permite comprobar cuánto puede explicarse mediante relaciones aproximadamente lineales después de codificar las variables categóricas.

### XGBoost

XGBoost construye una combinación secuencial de árboles y puede representar interacciones no lineales entre superficie, ubicación, tipología y equipamiento. También se entrena sobre el logaritmo del precio. La configuración utiliza profundidad moderada, regularización, muestreo de filas y columnas y una tasa de aprendizaje baja para limitar el sobreajuste.

No se realiza una búsqueda masiva de hiperparámetros. El objetivo de la entrega es comparar alternativas reproducibles y evaluar fuera de entrenamiento, no optimizar contra el test. Los hiperparámetros quedan fijados en el script y la semilla aleatoria es 42.

### Resultados en el test temporal

| Modelo | MAE | RMSE | R² | MAPE | MdAPE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline mediana | 186.838 € | 329.236 € | -0,090 | 67,66 % | 44,32 % |
| Ridge | 82.371 € | 151.214 € | 0,770 | 30,71 % | 17,95 % |
| XGBoost | **63.876 €** | **109.677 €** | **0,879** | **26,98 %** | **14,88 %** |

XGBoost reduce el MAE un 65,8 % frente al baseline y un 22,5 % frente a Ridge. También reduce el RMSE un 66,7 % frente al baseline y un 27,5 % frente a Ridge. La diferencia entre MAPE y MdAPE muestra que un grupo pequeño de observaciones extremas eleva mucho el promedio porcentual.

La importancia del modelo se concentra en señales de localización y características físicas. La categoría Madrid es la variable transformada con mayor importancia, seguida de determinados códigos postales y distritos; baños, coordenadas, superficie y ascensor también contribuyen. Esta importancia no implica causalidad y puede repartirse de forma inestable entre variables territoriales correlacionadas.

## 4 Validación y evaluación

### Separación temporal

El 20 % más reciente se reserva como test final. Para evitar que una misma fecha quede repartida, todas las observaciones del día de corte pasan al test. El entrenamiento contiene 4.475 viviendas hasta el 14 de marzo de 2026. El test contiene 1.130 viviendas entre el 15 de marzo y el 4 de abril de 2026.

Dentro del entrenamiento se aplica una validación temporal expansiva con cuatro particiones. Cada modelo aprende con observaciones anteriores y valida con un bloque posterior, sin repartir observaciones de una misma fecha entre ambos conjuntos. XGBoost obtiene en estas particiones un MAE medio de 82.926 euros, R² medio de 0,824 y MdAPE medio de 16,71 %. La variación del MAE entre particiones, con una desviación de 15.773 euros, indica que el rendimiento depende del periodo evaluado.

Esta estrategia reproduce mejor el uso real que una separación aleatoria. Una vivienda futura no debe ayudar a construir las imputaciones, las categorías o los parámetros empleados para valorar una vivienda anterior.

### Resultados por ciudad

| Ciudad | Observaciones de test | MAE | R² | MAPE | MdAPE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Córdoba | 317 | 36.727 € | 0,816 | 20,67 % | 13,45 % |
| Madrid | 469 | 88.948 € | 0,860 | 31,85 % | 13,55 % |
| Sevilla | 344 | 54.713 € | 0,834 | 26,15 % | 17,55 % |

Madrid presenta el mayor error absoluto porque concentra viviendas de precio elevado y mayor dispersión. La mediana porcentual, sin embargo, es parecida a la de Córdoba. Esto confirma que una única métrica no describe por completo el comportamiento del modelo.

### Resultados por tramo de precio

| Tramo | Observaciones | MAE | MAPE | MdAPE |
| --- | ---: | ---: | ---: | ---: |
| Hasta 150.000 € | 251 | 45.958 € | 63,29 % | 22,35 % |
| 150.000 a 300.000 € | 467 | 36.043 € | 16,56 % | 12,97 % |
| 300.000 a 600.000 € | 264 | 69.602 € | 16,46 % | 14,78 % |
| Más de 600.000 € | 148 | 171.877 € | 17,02 % | 14,42 % |

El modelo funciona mejor en términos relativos entre 150.000 y 600.000 euros. Los precios muy bajos producen porcentajes extremos y pueden incluir anuncios anómalos. En el test existe, por ejemplo, una vivienda de 103 m² en Madrid anunciada por 20.000 euros; XGBoost estima unos 596.000 euros. También aparece una vivienda de 159 m² en Retiro por 150.000 euros que el modelo sitúa en torno a 1.050.000 euros. Estos casos pueden corresponder a errores, porcentajes de propiedad, subastas, inmuebles con condicionantes no representados o anuncios que requieren revisión manual.

En el extremo alto, el modelo tiende a suavizar los valores y puede infravalorar viviendas singulares. Faltan variables como calidad constructiva, reforma, vistas, exterior o interior, altura real, eficiencia energética y estado documental.

### Generalización geográfica

Se realiza una prueba adicional en la que cada ciudad se elimina por completo del entrenamiento y se utiliza como test. El rendimiento cae de forma acusada:

| Ciudad no vista durante el entrenamiento | MAE | R² | MdAPE |
| --- | ---: | ---: | ---: |
| Córdoba | 79.429 € | 0,550 | 28,97 % |
| Madrid | 452.515 € | -0,478 | 72,97 % |
| Sevilla | 156.364 € | 0,090 | 46,13 % |

La prueba demuestra que Madrid, Sevilla y Córdoba son útiles como tres escalas urbanas de referencia, pero no permiten afirmar que el modelo generalice a una ciudad nunca observada. La población o la condición costera pueden aportar contexto, pero un factor manual no sustituye datos representativos y validación externa.

### Validación externa con la captura de noviembre

Para medir el comportamiento ante anuncios realmente posteriores se utiliza una segunda captura de DataVenues fechada el 16 de noviembre de 2026. Tras aplicar el contrato corregido, eliminar una fila de Arrigorriaga incluida en el fichero de Bilbao, deduplicar dentro de cada descarga y ejecutar los controles de calidad, el Gold queda formado por 11.297 observaciones de A Coruña, Bilbao, Córdoba, Cuenca, Granada, Madrid, Sevilla y Valencia. Los 83 áticos de esta captura se representan mediante `es_atico=1` y ninguno utiliza una planta ficticia 99.

La separación entre capturas excluye 159 coincidencias exactas de `id_observacion`, identificador derivado de referencia o URL. No se eliminan viviendas solo por compartir coordenadas aproximadas, superficie, dormitorios y baños, porque pueden ser unidades distintas de un mismo edificio. El test externo contiene así 11.138 observaciones.

Además del champion XGBoost se calcula una referencia de mercado basada en la mediana de precio por metro cuadrado aprendida únicamente con abril. Exige al menos 10 testigos y amplía progresivamente el nivel desde barrio a código postal, distrito, municipio y mediana global.

| Ámbito externo | Modelo | Observaciones | MAE | R² | MAPE |
| --- | --- | ---: | ---: | ---: | ---: |
| Total | XGBoost champion | 11.138 | 102.260 € | 0,537 | 31,48 % |
| Total | Baseline zona y superficie | 11.138 | **95.156 €** | **0,606** | 32,12 % |
| Madrid, Sevilla y Córdoba | XGBoost champion | 5.662 | **61.568 €** | **0,839** | **22,58 %** |
| Madrid, Sevilla y Córdoba | Baseline zona y superficie | 5.662 | 69.259 € | 0,805 | 27,12 % |
| Ciudades nuevas | XGBoost champion | 5.476 | 144.334 € | 0,097 | 40,68 % |
| Ciudades nuevas | Baseline zona y superficie | 5.476 | **121.932 €** | **0,316** | **37,30 %** |

XGBoost supera al baseline en las tres ciudades conocidas, lo que demuestra que el modelo aporta información más allá de una regla territorial sencilla cuando existe cobertura de entrenamiento. En el conjunto total el baseline obtiene menor MAE porque el champion pierde capacidad en ciudades nuevas. Por tanto, no procede extender automáticamente el modelo de abril a todo el país.

| Ciudad | Observaciones | MAE XGBoost | MAE baseline | R² XGBoost |
| --- | ---: | ---: | ---: | ---: |
| A Coruña | 504 | 183.162 € | **129.747 €** | 0,051 |
| Bilbao | 1.270 | **110.742 €** | 174.656 € | 0,543 |
| Cuenca | 189 | **72.233 €** | 126.681 € | 0,350 |
| Córdoba | 1.808 | **41.884 €** | 52.077 € | 0,736 |
| Granada | 1.529 | 156.160 € | **86.669 €** | -0,383 |
| Madrid | 1.979 | **89.051 €** | 94.254 € | 0,789 |
| Sevilla | 1.875 | **51.543 €** | 59.445 € | 0,811 |
| Valencia | 1.984 | 153.729 € | **112.922 €** | -0,165 |

Bilbao debe interpretarse con cautela: es una ciudad nueva y, a diferencia de las otras descargas, sus anuncios proceden de Idealista por ofrecer mayor cobertura. El efecto de ciudad y el efecto del portal no pueden separarse con esta muestra.

El desglose por precio confirma que XGBoost aporta más en el tramo hasta 150.000 euros, mientras que el baseline obtiene menor MAE en los tres tramos superiores de la muestra externa. En las viviendas de más de 600.000 euros ambos métodos presentan errores absolutos elevados.

| Tramo de precio | Observaciones | MAE XGBoost | MAE baseline |
| --- | ---: | ---: | ---: |
| Hasta 150.000 € | 1.954 | **40.606 €** | 53.628 € |
| 150.000 a 300.000 € | 4.392 | 58.389 € | **53.551 €** |
| 300.000 a 600.000 € | 3.460 | 122.007 € | **107.768 €** |
| Más de 600.000 € | 1.332 | 286.066 € | **260.498 €** |

### Sensibilidad a valores atípicos

Para comprobar si la ventaja del baseline en las ciudades nuevas se explica únicamente por anuncios extremos, se repite la comparación aplicando por ciudad la regla de 1,5 veces el rango intercuartílico. Se ensayan por separado el precio por metro cuadrado observado y el precio total. Estos filtros se utilizan solo como análisis de sensibilidad sobre el test: no modifican el Gold ni se calculan a partir del error de los modelos.

| Filtro en ciudades nuevas | Observaciones | Excluidas | MAE XGBoost | MAE baseline |
| --- | ---: | ---: | ---: | ---: |
| Sin filtro | 5.476 | 0 | 144.334 € | **121.932 €** |
| Sin atípicos de precio/m² por ciudad | 5.321 | 155 | 135.175 € | **111.727 €** |
| Sin atípicos de precio total por ciudad | 5.170 | 306 | 120.110 € | **104.648 €** |

La exclusión reduce el error de ambos métodos, pero no invierte la comparación agregada. Sin los atípicos de precio por metro cuadrado, el baseline continúa obteniendo menor MAE en A Coruña, Granada y Valencia, mientras que XGBoost mantiene la ventaja en Bilbao y Cuenca. Por tanto, los valores extremos influyen, pero no son la causa principal del resultado.

Además, las 5.476 viviendas de ciudades nuevas recurren al nivel global del baseline, con una referencia de 2.708 €/m², porque la captura de abril no contiene testigos de esos territorios. Su robustez procede de escalar la superficie por una mediana global, no de conocer sus zonas. Los sesgos observados por ciudad apuntan principalmente a un cambio de distribución y a la extrapolación geográfica del champion.

Después de cerrar esta evaluación se entrena un challenger con abril y noviembre. Cuando un identificador coincide se conserva la observación más reciente, de modo que el conjunto combinado contiene 16.743 viviendas. El challenger no se promociona: al haber aprendido de noviembre necesita una captura futura no utilizada en entrenamiento antes de sustituir al champion.

### Limitaciones

- El objetivo es precio anunciado, no precio de cierre.
- El champion se entrenó inicialmente con tres ciudades y la distribución temporal de abril está muy concentrada al final del periodo.
- Conservación y planta tienen muchos valores ausentes.
- Las viviendas singulares y los anuncios anómalos generan errores grandes.
- No están disponibles año de construcción, reforma, calidad, certificación energética ni servicios próximos en el Gold actual.
- El intervalo calibrado es amplio y no debe interpretarse como garantía de tasación.
- La prueba por ciudad impide utilizar esta versión fuera de Madrid, Sevilla y Córdoba sin una validación específica.
- La captura de Bilbao procede de un portal distinto y no permite separar el efecto de fuente del efecto territorial.

## 5 Decisión y uso en el producto

Se mantiene XGBoost como champion académico para Madrid, Sevilla y Córdoba porque mejora de forma consistente al baseline y a Ridge en la validación temporal, y también supera al baseline territorial en la captura posterior para esas ciudades. La mejora demuestra que las características del inmueble y su localización aportan una señal útil. El modelo reentrenado con las ocho ciudades queda registrado como challenger sin promover. Ninguno de los dos es suficiente todavía para sustituir la revisión profesional ni para desplegar una valoración automática de ámbito nacional.

El frontal de una futura versión académica de VISSOTIA debería consumir una respuesta similar a esta:

```json
{
  "precio_orientativo_eur": 285000,
  "intervalo_90_eur": [175000, 462000],
  "fecha_valoracion": "2026-04-06",
  "tipo_objetivo": "precio_anunciado",
  "cobertura_geografica": "mercado_con_datos",
  "calidad_entrada": "media",
  "modelo": "valoracion_inicial_v1",
  "requiere_revision_humana": false
}
```

El ejemplo ilustra el contrato de salida, no una valoración real. El intervalo se calculará para cada predicción y podrá ser amplio cuando el modelo sea incierto. El frontal debe explicar que la cifra es una referencia de publicación y mostrar los campos ausentes que reducen su fiabilidad.

La futura integración seguirá una secuencia controlada:

1. Incorporar año de construcción, reforma, estado y superficie contrastada con Catastro cuando estén disponibles.
2. Añadir variables de servicios y accesibilidad de zona con procedencia y fecha.
3. Reentrenar el modelo con esas variables, evitando aplicar correcciones dobles por ciudad, zona o conservación.
4. Comparar mediante ablación el modelo base y cada capa adicional.
5. Calibrar intervalos por ciudad y tramo de precio.
6. Ampliar la cobertura con datos autorizados de nuevas ciudades y repetir la prueba de ciudad no vista.
7. Documentar la definición de `demanda` y medir mediante ablación si mejora la valoración inicial sin introducir información futura.
8. Crear por separado el modelo de seguimiento comercial con días publicado, demanda contemporánea y cambios de precio.
9. Mantener registro de versión, variables, fecha, intervalo y advertencias de cada valoración.

El ajuste por reforma del valorador anterior se conserva como conocimiento de negocio, pero no se integra todavía en este entrenamiento porque el Gold no contiene año y tipo de reforma. Cuando esos datos estén disponibles, se comparará una variable aprendida por el modelo con una capa de reglas expertas. La opción elegida será la que mejore la validación sin duplicar el efecto de conservación o ubicación.

## Reproducción

El experimento se ejecuta desde la raíz del repositorio:

```bash
python scripts/train_vissotia_valuation.py \
  --input data/entregas/02/local_output/vissotia_valoracion_gold.csv \
  --output-dir data/entregas/03/local_output
```

Las dependencias están declaradas en `requirements-entrega-03.txt`. El script genera las métricas, predicciones, residuos de calibración, análisis por segmentos, prueba de ciudad excluida, importancia de variables, gráficos y el artefacto local del modelo. Las salidas permanecen fuera de Git porque derivan de una fuente cuya redistribución debe validarse.

La validación con la captura posterior y el entrenamiento del challenger se reproducen ejecutando `notebooks/03b_validacion_externa_y_challenger.ipynb`. El notebook genera el Gold de noviembre, excluye coincidencias exactas entre capturas, calcula el baseline de zona y superficie, presenta métricas por ciudad y tramo de precio, comprueba la sensibilidad a valores atípicos y guarda el challenger en la salida local protegida.

El código y esta memoria distinguen el resultado reproducible del experimento de la futura implementación en VISSOTIA. No se ha modificado el repositorio ni el valorador de producción de VISSOTIA.
