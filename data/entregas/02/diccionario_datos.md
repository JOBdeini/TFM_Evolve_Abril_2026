# Diccionario de datos de la Entrega 02

Este documento define el contrato actual de `vissotia_valoracion_gold.csv`. Se distinguen explícitamente la fecha de publicación del anuncio y la fecha de extracción de la captura, fijada para este conjunto en el 6 de abril de 2026.

| Campo | Tipo esperado | Definición y unidad | Nulos | Momento de disponibilidad | Rol previsto |
| --- | --- | --- | --- | --- | --- |
| `id_observacion` | texto | Hash técnico no reversible basado en referencia o URL normalizada; no depende del precio. Si ambas faltan, se crea una identidad limitada a la extracción actual. | No | Preparación | Identificación técnica |
| `fecha_publicacion` | fecha ISO | Fecha de creación o publicación informada por la fuente. | No | Publicación | Trazabilidad temporal |
| `fecha_extraccion` | fecha ISO | Fecha en que se obtuvo la captura usada en esta entrega: 2026-04-06. | No | Extracción | Trazabilidad y control de fuga |
| `operacion` | categoría | Tipo de operación. El Gold solo admite venta. | No | Antes de publicar | Control de calidad |
| `tipologia` | categoría | Tipo de vivienda anunciado. | No | Antes de publicar | Predictor inicial |
| `codigo_postal` | entero/categoría | Código postal de la ubicación. | Sí | Antes de publicar | Predictor inicial |
| `municipio` | categoría | Municipio normalizado. | No | Antes de publicar | Predictor inicial |
| `provincia` | categoría | Provincia normalizada. | No | Antes de publicar | Predictor inicial |
| `distrito` | categoría | Distrito del inmueble cuando está disponible. | Sí | Antes de publicar | Predictor inicial |
| `barrio` | categoría | Barrio del inmueble cuando está disponible. | Sí | Antes de publicar | Predictor inicial |
| `latitud_aprox` | decimal | Latitud redondeada a tres decimales. | No | Antes de publicar | Predictor inicial restringido |
| `longitud_aprox` | decimal | Longitud redondeada a tres decimales. | No | Antes de publicar | Predictor inicial restringido |
| `planta_num` | decimal | Altura numérica declarada; bajo 0 y entreplanta 0,5. Un ático sin altura explícita no se convierte en una planta ficticia. | Sí | Antes de publicar | Predictor inicial |
| `es_atico` | binario | 1 si la fuente declara ático; 0 si declara otra planta; nulo si no existe información de planta. | Sí | Antes de publicar | Predictor inicial |
| `aire_acondicionado` | binario | 1 si se declara; 0 si se niega; nulo si falta o el valor no se reconoce. | Sí | Antes de publicar | Predictor inicial |
| `ascensor` | binario | 1 si se declara; 0 si se niega; nulo si falta o el valor no se reconoce. | Sí | Antes de publicar | Predictor inicial |
| `garaje` | binario | 1 si se declara; 0 si se niega; nulo si falta o el valor no se reconoce. | Sí | Antes de publicar | Predictor inicial |
| `trastero` | binario | 1 si se declara; 0 si se niega; nulo si falta o el valor no se reconoce. | Sí | Antes de publicar | Predictor inicial |
| `terraza` | binario | 1 si se declara; 0 si se niega; nulo si falta o el valor no se reconoce. | Sí | Antes de publicar | Predictor inicial |
| `piscina` | binario | 1 si se declara; 0 si se niega; nulo si falta o el valor no se reconoce. | Sí | Antes de publicar | Predictor inicial |
| `zonas_verdes` | binario | 1 si se declara; 0 si se niega; nulo si falta o el valor no se reconoce. | Sí | Antes de publicar | Predictor inicial |
| `zona_deportiva` | binario | 1 si se declara; 0 si se niega; nulo si falta o el valor no se reconoce. | Sí | Antes de publicar | Predictor inicial |
| `conservacion` | categoría | Estado de conservación declarado en el anuncio. | Sí | Antes de publicar | Predictor inicial |
| `dormitorios` | decimal/entero | Número de dormitorios; rango admitido de 0 a 15. | Sí | Antes de publicar | Predictor inicial |
| `banos` | decimal/entero | Número de baños; rango admitido de 0 a 10. | Sí | Antes de publicar | Predictor inicial |
| `superficie_m2` | decimal | Superficie anunciada en metros cuadrados; rango admitido de 15 a 1.000. | No | Antes de publicar | Predictor inicial |
| `dias_publicado` | entero | Días transcurridos desde la publicación hasta la fecha de referencia de la captura. | No | Después de publicar | Seguimiento o reestimación |
| `demanda` | categoría | Señal de mercado informada por DataVenues sobre el volumen proporcional de clientes para la tipología y zona. | Condicional | Extracción | Valoración inicial si estaba disponible y fechada al estimar; en caso contrario, seguimiento |
| `origen_dataset` | categoría | Ciudad y fichero lógico de procedencia. | No | Preparación | Trazabilidad y segmentación |
| `precio_objetivo_eur` | decimal | Precio anunciado en euros; no es precio de cierre ni tasación. | No | Publicación | Variable objetivo |

## Variables excluidas

- Datos personales o de contacto: anunciante, empresa, teléfono y correo electrónico.
- Contenido identificativo o no necesario: título, comentarios, imagen, URL y referencia original.
- Variables con fuga del objetivo: precio unitario, precio por metro cuadrado y agregados territoriales calculados con todo el dataset.

## Contratos temporales

- **Valoración inicial:** solo utiliza variables disponibles antes de publicar el inmueble.
- **Seguimiento o reestimación:** puede evaluar `dias_publicado`, ya que solo existe después de publicar y puede reflejar demanda, desajuste de precio o calidad del anuncio.
- **Demanda:** puede evaluarse en el valorador inicial únicamente si el valor estaba disponible en la fecha de extracción y se demuestra que no incorpora información futura. Si no se puede acreditar, se reserva para seguimiento.

## Controles efectivos antes de exportar

El pipeline detiene la ejecución si falta una columna obligatoria de la fuente. Antes de Gold descarta y contabiliza las filas que incumplen alguno de estos controles:

- fecha de publicación válida y no posterior a la extracción;
- tipología, municipio, provincia y origen informados;
- latitud entre -90 y 90 y longitud entre -180 y 180;
- operación de venta;
- precio superior a 10.000 euros;
- superficie entre 15 y 1.000 metros cuadrados;
- dormitorios y baños dentro de los rangos declarados cuando existen.

Después de construir Gold se ejecuta una segunda validación que comprueba columnas, nulos obligatorios, fechas, coordenadas, rangos, operación, codificación binaria y ausencia del valor ficticio 99 en `planta_num`. Un incumplimiento impide exportar el dataset.
