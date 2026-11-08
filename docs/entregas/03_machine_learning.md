# Proyecto final Evolve Entrega 03 Machine Learning

## VISSOTIA valoración inicial de viviendas

Esta entrega desarrolla y evalúa una primera capacidad de Machine Learning para VISSOTIA: estimar un precio orientativo de publicación antes de que una vivienda salga al mercado. El experimento parte del dataset Gold de la Entrega 02, separa las variables disponibles antes de publicar de las señales que aparecen después y compara una referencia sencilla con Ridge y XGBoost.

La solución elegida para el prototipo académico es XGBoost. En un test formado por las observaciones temporalmente más recientes obtiene un MAE de 63.648 euros, un R² de 0,878 y una mediana de error porcentual absoluto del 14,93 %. Mejora el MAE del baseline en un 65,9 % y el de Ridge en un 22,9 %. El resultado permite demostrar valor para un MVP acotado a Madrid, Sevilla y Córdoba, pero todavía no justifica una valoración nacional ni una integración automática en la versión publicada de VISSOTIA.

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

El experimento utiliza las 5.605 observaciones y las 29 columnas del Gold generado en la Entrega 02. `fecha_publicacion` abarca desde el 1 de enero de 2018 hasta el 4 de abril de 2026; `fecha_extraccion` es el 6 de abril de 2026 para toda la captura. La muestra se concentra especialmente en 2025 y 2026 y la cobertura geográfica está limitada a Madrid, Sevilla y Córdoba.

### Variables utilizadas

| Grupo | Variables | Disponibilidad en el momento de uso |
| --- | --- | --- |
| Características físicas | `superficie_m2`, `dormitorios`, `banos`, `planta_num`, `tipologia` | Declaradas por el usuario o contrastadas con documentación y Catastro |
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

El intervalo no se fija de forma arbitraria. Se calcula en escala logarítmica con los residuos fuera de muestra de las particiones temporales de validación y una corrección conformal finita. En el test final cubre el 91,8 % de los precios observados, cercano al 90 % nominal. Es un intervalo empírico del experimento, no una garantía individual; su amplitud elevada refleja la incertidumbre de los datos actuales.

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
| Ridge | 82.521 € | 151.617 € | 0,769 | 30,71 % | 17,96 % |
| XGBoost | **63.648 €** | **109.976 €** | **0,878** | **27,07 %** | **14,93 %** |

XGBoost reduce el MAE un 65,9 % frente al baseline y un 22,9 % frente a Ridge. También reduce el RMSE un 66,6 % frente al baseline y un 27,5 % frente a Ridge. La diferencia entre MAPE y MdAPE muestra que un grupo pequeño de observaciones extremas eleva mucho el promedio porcentual.

La importancia del modelo se concentra en señales de localización y características físicas. La categoría Madrid es la variable transformada con mayor importancia, seguida de determinados códigos postales y distritos; baños, coordenadas, superficie y ascensor también contribuyen. Esta importancia no implica causalidad y puede repartirse de forma inestable entre variables territoriales correlacionadas.

## 4 Validación y evaluación

### Separación temporal

El 20 % más reciente se reserva como test final. Para evitar que una misma fecha quede repartida, todas las observaciones del día de corte pasan al test. El entrenamiento contiene 4.475 viviendas hasta el 14 de marzo de 2026. El test contiene 1.130 viviendas entre el 15 de marzo y el 4 de abril de 2026.

Dentro del entrenamiento se aplica una validación temporal expansiva con cuatro particiones. Cada modelo aprende con observaciones anteriores y valida con un bloque posterior, sin repartir observaciones de una misma fecha entre ambos conjuntos. XGBoost obtiene en estas particiones un MAE medio de 82.337 euros, R² medio de 0,826 y MdAPE medio de 16,62 %. La variación del MAE entre particiones, con una desviación de 16.191 euros, indica que el rendimiento depende del periodo evaluado.

Esta estrategia reproduce mejor el uso real que una separación aleatoria. Una vivienda futura no debe ayudar a construir las imputaciones, las categorías o los parámetros empleados para valorar una vivienda anterior.

### Resultados por ciudad

| Ciudad | Observaciones de test | MAE | R² | MAPE | MdAPE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Córdoba | 317 | 35.866 € | 0,817 | 20,25 % | 13,97 % |
| Madrid | 469 | 89.362 € | 0,860 | 32,41 % | 13,90 % |
| Sevilla | 344 | 54.194 € | 0,832 | 26,08 % | 16,48 % |

Madrid presenta el mayor error absoluto porque concentra viviendas de precio elevado y mayor dispersión. La mediana porcentual, sin embargo, es parecida a la de Córdoba. Esto confirma que una única métrica no describe por completo el comportamiento del modelo.

### Resultados por tramo de precio

| Tramo | Observaciones | MAE | MAPE | MdAPE |
| --- | ---: | ---: | ---: | ---: |
| Hasta 150.000 € | 251 | 45.701 € | 64,12 % | 22,10 % |
| 150.000 a 300.000 € | 467 | 35.728 € | 16,40 % | 13,24 % |
| 300.000 a 600.000 € | 264 | 68.573 € | 16,25 % | 14,63 % |
| Más de 600.000 € | 148 | 173.402 € | 17,24 % | 14,89 % |

El modelo funciona mejor en términos relativos entre 150.000 y 600.000 euros. Los precios muy bajos producen porcentajes extremos y pueden incluir anuncios anómalos. En el test existe, por ejemplo, una vivienda de 103 m² en Madrid anunciada por 20.000 euros; XGBoost estima unos 596.000 euros. También aparece una vivienda de 159 m² en Retiro por 150.000 euros que el modelo sitúa en torno a 1.050.000 euros. Estos casos pueden corresponder a errores, porcentajes de propiedad, subastas, inmuebles con condicionantes no representados o anuncios que requieren revisión manual.

En el extremo alto, el modelo tiende a suavizar los valores y puede infravalorar viviendas singulares. Faltan variables como calidad constructiva, reforma, vistas, exterior o interior, altura real, eficiencia energética y estado documental.

### Generalización geográfica

Se realiza una prueba adicional en la que cada ciudad se elimina por completo del entrenamiento y se utiliza como test. El rendimiento cae de forma acusada:

| Ciudad no vista durante el entrenamiento | MAE | R² | MdAPE |
| --- | ---: | ---: | ---: |
| Córdoba | 81.658 € | 0,527 | 30,12 % |
| Madrid | 449.154 € | -0,472 | 72,26 % |
| Sevilla | 170.054 € | -0,008 | 50,73 % |

La prueba demuestra que Madrid, Sevilla y Córdoba son útiles como tres escalas urbanas de referencia, pero no permiten afirmar que el modelo generalice a una ciudad nunca observada. La población o la condición costera pueden aportar contexto, pero un factor manual no sustituye datos representativos y validación externa.

### Limitaciones

- El objetivo es precio anunciado, no precio de cierre.
- Solo existen tres ciudades y la distribución temporal está muy concentrada al final del periodo.
- Conservación y planta tienen muchos valores ausentes.
- Las viviendas singulares y los anuncios anómalos generan errores grandes.
- No están disponibles año de construcción, reforma, calidad, certificación energética ni servicios próximos en el Gold actual.
- El intervalo calibrado es amplio y no debe interpretarse como garantía de tasación.
- La prueba por ciudad impide utilizar esta versión fuera de Madrid, Sevilla y Córdoba sin una validación específica.

## 5 Decisión y uso en el producto

Se selecciona XGBoost como modelo candidato para el MVP académico porque mejora de forma consistente al baseline y a Ridge en la validación temporal y en el test final. La mejora es suficiente para demostrar que las características del inmueble y su localización aportan una señal útil. No es suficiente todavía para sustituir la revisión profesional ni para desplegar una valoración automática de ámbito nacional.

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

El código y esta memoria distinguen el resultado reproducible del experimento de la futura implementación en VISSOTIA. No se ha modificado el repositorio ni el valorador de producción de VISSOTIA.
