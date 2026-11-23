# Proyecto final Evolve Entrega 02 Datos y preparación

## Contexto y alcance

Vissotia es una plataforma de inteligencia para la comercialización de viviendas. Reúne en un único proyecto los datos del inmueble, su contexto territorial, la valoración, la documentación, los contenidos comerciales y la actividad de venta. El problema que aborda es la fragmentación de información que obliga a un profesional inmobiliario a consultar varias herramientas y a tomar decisiones con datos incompletos o poco trazables.

Esta entrega acota el trabajo al primer caso de uso de ciencia de datos: preparar observaciones de viviendas en venta para una futura estimación de precio. El resultado no es todavía una tasación oficial ni un modelo listo para producción. Es un dataset reproducible que permite iniciar la fase de machine learning y, al mismo tiempo, detectar las limitaciones de la información disponible.

## 1 Qué datos necesita el producto

Una observación representa un anuncio de una vivienda en venta, publicado en una fecha determinada y presente en la captura disponible. La variable objetivo es el precio anunciado en euros. Por tanto, el primer modelo aprenderá a estimar precio de oferta, no precio efectivo de cierre. Esta distinción es importante: el precio anunciado sirve como referencia comercial, pero no equivale al valor de transacción ni a una tasación homologada.

Los datos imprescindibles son la tipología, la ubicación agregada, la superficie, los dormitorios, los baños, la fecha de publicación y el precio anunciado. La ubicación se conserva a nivel de código postal, municipio, distrito o barrio. Las coordenadas se redondean a tres decimales para reducir la posibilidad de identificar una vivienda concreta.

Como variables deseables se incluyen planta, conservación, ascensor, garaje, trastero, terraza, piscina, zonas verdes, aire acondicionado, días publicado y nivel de demanda. En una evolución posterior podrían añadirse año de construcción, reforma, superficie catastral, eficiencia energética, indicadores oficiales de zona y distancias a servicios. Estas variables mejoran la explicación del precio, pero no son necesarias para demostrar el flujo inicial.

La granularidad es una fila por anuncio presente en la captura disponible. Para la entrega se utilizan tres ficheros de Madrid, Sevilla y Córdoba con 2.000 registros cada uno. DataVenues limita la descarga a 2.000 observaciones por provincia y ese límite se ha respetado. El campo de origen `fecha_de_creacion` se exporta como `fecha_publicacion`; además, `fecha_extraccion` registra de forma configurable el 6 de abril de 2026. El control `fecha_publicacion + dias_publicado` coincide con esa fecha en las 5.605 observaciones del Gold. Por tanto, el conjunto es una fotografía transversal con anuncios de distinta antigüedad, no un histórico longitudinal de capturas. Para estudiar estacionalidad o cambios de ciclo se necesitarían extracciones periódicas y, preferiblemente, operaciones cerradas o datos contratados a un proveedor autorizado.

No se incluyen como predictores el precio por metro cuadrado ni medias de precio calculadas con todo el dataset. Esas variables se derivan del propio objetivo y provocarían fuga de información. Los agregados territoriales, si se usan en la siguiente fase, deberán calcularse únicamente con el conjunto de entrenamiento de cada partición.

## 2 Fuentes reales y viabilidad

| Fuente | Acceso y contenido | Cobertura y actualización | Estabilidad y alternativa |
| --- | --- | --- | --- |
| Ficheros de anuncios DataVenues | Tres CSV obtenidos mediante la descarga ordinaria disponible para la agencia inmobiliaria en la que trabaja el responsable del proyecto. No se ha realizado scraping ni se han eludido límites. Contienen características, ubicación, fecha, precio y campos de contacto que se eliminan antes de Silver. | 6.000 filas brutas: el máximo permitido de 2.000 observaciones por provincia para Madrid, Sevilla y Córdoba. Forman una captura de anuncios, no compraventas cerradas. | Uso académico local, minimizado y sin redistribución. No existe autorización expresa documentada para integrar estos datos en el producto comercial; antes de hacerlo se requerirá un acuerdo específico, un feed licenciado o datos propios. |
| Dirección General del Catastro | Servicios web de consulta de datos no protegidos y descargas sujetas a sus condiciones. Aporta referencia, superficie, uso, antigüedad y características constructivas cuando están disponibles. | Cobertura estatal con las particularidades territoriales del Catastro y mantenimiento continuo. | Fuente pública estable. Si la consulta falla, se mantiene el dato declarado por el usuario con estado pendiente de validación y se permite incorporar documentación acreditativa. |
| Instituto Nacional de Estadística | API JSON de INEbase y descargas oficiales. Aporta variables agregadas de población, vivienda y actividad territorial. | Cobertura nacional con periodicidad propia de cada operación estadística. | Fuente oficial estable. Como alternativa se conserva una extracción fechada y trazable hasta la siguiente actualización, citando siempre al INE. |
| Google Geocoding y Places | APIs autenticadas para normalizar una dirección y consultar servicios próximos. En Vissotia se usan coordenadas, componentes de dirección, identificadores de lugar, categorías y distancias. | Buena cobertura operativa y consulta bajo demanda. Depende de cuota, coste, cambios de API y condiciones contractuales. | No forma parte del Gold académico. Si el servicio no está disponible, el flujo puede continuar con la dirección validada por el usuario, Catastro y sin variables de puntos de interés. |
| Datos propios del proyecto y de la agencia | Formularios, documentos autorizados, OCR y actividad comercial aportada por usuarios con permisos. | Crece con el uso de Vissotia y puede recoger el resultado real de la venta. | Es la fuente estratégica para mejorar el modelo. Si falta un campo, se conserva como nulo y se solicita validación humana; no se inventa ni se infiere un dato sensible. |

La viabilidad técnica está demostrada porque Vissotia ya dispone de servicios para ubicación, Catastro, INE, enriquecimiento de zona y valoración, y existe un artefacto de modelo local. La viabilidad estadística es más limitada: la muestra actual permite construir un prototipo, pero no representa todo el mercado español ni contiene el precio final de las operaciones.

## 3 Uso privacidad y datos personales

Los CSV históricos contienen nombres o alias de anunciantes, empresas, teléfonos, correos electrónicos, URLs, imágenes y coordenadas precisas. Ninguno de esos campos es necesario para estimar el precio de una vivienda. El proceso los excluye del dataset Silver y del Gold. La referencia y la URL solo se usan en memoria para detectar duplicados y construir un hash técnico no reversible; no se exportan. El identificador no depende del precio. Si excepcionalmente faltaran referencia y URL, el proceso conservaría la fila y generaría una identidad limitada a esa extracción. Las coordenadas se reducen en precisión.

El repositorio no contiene los CSV originales ni una copia de sus registros. DataVenues es proveedor de la agencia inmobiliaria en la que trabaja el responsable del proyecto y los ficheros se obtuvieron mediante el mecanismo ordinario de descarga, respetando su límite de 2.000 observaciones por provincia. No se realizó scraping ni se forzó la obtención de registros. Para esta entrega se documenta un uso académico, local, minimizado y sin redistribución. Como no existe una autorización expresa documentada para reutilizarlos dentro del producto comercial Vissotia, un despliegue productivo deberá apoyarse en un acuerdo de datos específico, una API o feed autorizado, o datos propios de las agencias.

Para Catastro solo se consultarán datos no protegidos. Los datos de titularidad y los valores catastrales individualizados no se incorporarán salvo que exista una legitimación específica y un diseño separado de permisos. La información del INE cuya fuente original es el propio organismo puede reutilizarse bajo CC BY 4.0 con atribución y fecha de actualización.

Los resultados de Google Maps y Places están sujetos a sus condiciones, incluidas las reglas de atribución y almacenamiento. En esta entrega no se copian al dataset de entrenamiento. Su uso productivo se limitará a la funcionalidad permitida por el contrato vigente y se revisará antes de persistir contenido o generar variables derivadas.

En producción, Vissotia aplicará control de acceso por proyecto, registro de procedencia y fecha, plazos de conservación, borrado y revisión humana. Los documentos aportados por usuarios se procesarán para una finalidad concreta y no se reutilizarán para entrenar modelos generales sin una base jurídica y una autorización separadas.

## 4 Del dato bruto al dato utilizable

### Bronze Raw

La capa Bronze conserva los tres CSV originales sin cambios y fuera del repositorio. El proceso genera localmente `source_manifest.json` con nombre, tamaño, fecha de modificación, columnas, checksum SHA-256, fecha de extracción, modalidad de acceso, límite de descarga y alcance de uso declarado. Este manifiesto acredita integridad y procedencia operativa, pero no constituye una licencia ni amplía los derechos de reutilización. El acceso se documenta en `data/entregas/02/README.md`. No se suben datos personales ni datos de portales a Git.

### Silver

El script `scripts/prepare_vissotia_data.py` concatena las tres fuentes y añade su ciudad de origen. Antes de transformar comprueba que la fuente contiene las columnas obligatorias. Después normaliza nombres, fechas, números, plantas y variables binarias; elimina duplicados; filtra operaciones distintas de venta y valores físicamente implausibles; y descarta todos los campos de contacto, texto libre, URL, imagen y referencia. La deduplicación prioriza la referencia y utiliza la URL como alternativa; si ambas faltan, conserva la observación en lugar de agrupar indebidamente todos los nulos. También redondea coordenadas y registra los fallos independientes y los descartes secuenciales de cada control.

Las fechas inválidas, las publicaciones posteriores a la extracción, las coordenadas fuera de rango y la ausencia de tipología, municipio, provincia u origen impiden que una fila llegue a Gold. Los valores binarios no reconocidos no se convierten en una ausencia falsa: se conservan como nulos, se contabilizan en el informe y se imputan dentro del entrenamiento. La planta numérica se separa de la condición de ático mediante `planta_num` y `es_atico`; un ático sin altura declarada mantiene la planta nula en lugar de recibir el valor artificial 99.

La transformación evita imputar valores de negocio en esta fase. Los nulos se conservan para que el notebook de modelado compare estrategias de imputación dentro de cada partición de entrenamiento. Así se evita usar información del conjunto de prueba durante la preparación.

### Gold

El Gold es `vissotia_valoracion_gold.csv`. Cada fila representa un anuncio residencial en venta presente en la captura de referencia. Contiene 30 columnas y separa con claridad predictores, objetivo y señales posteriores a la publicación. El contrato detallado se encuentra en `data/entregas/02/diccionario_datos.md`.

| Grupo | Columnas principales | Uso posterior |
| --- | --- | --- |
| Identificación técnica | `id_observacion`, `fecha_publicacion`, `fecha_extraccion`, `origen_dataset` | Trazabilidad temporal y control de disponibilidad de cada variable |
| Ubicación minimizada | `codigo_postal`, `municipio`, `provincia`, `distrito`, `barrio`, `latitud_aprox`, `longitud_aprox` | Captar diferencias territoriales sin publicar una dirección exacta |
| Características | `tipologia`, `planta_num`, `es_atico`, `dormitorios`, `banos`, `superficie_m2`, `conservacion` | Variables estructurales de la vivienda |
| Equipamiento | `ascensor`, `garaje`, `trastero`, `terraza`, `piscina`, `zonas_verdes`, `zona_deportiva`, `aire_acondicionado` | Explicar parte del diferencial de precio |
| Señales de mercado | `dias_publicado`, `demanda` | `dias_publicado` se reserva para seguimiento. `demanda` puede probarse en valoración inicial solo si estaba disponible y fechada al estimar; de lo contrario, se reserva para seguimiento |
| Objetivo | `precio_objetivo_eur` | Variable que predecirá el primer modelo |

La ejecución reproducible es:

```bash
python scripts/prepare_vissotia_data.py \
  --input-dir /ruta/local/a/los/csv \
  --output-dir data/entregas/02/local_output \
  --extraction-date 2026-04-06
```

Además del CSV, el proceso crea `quality_report.json` con el número de filas por etapa, los descartes por regla, los nulos por columna, los binarios desconocidos, el diagnóstico de fecha de referencia, la validación final del contrato y la relación de campos excluidos por privacidad o por fuga del objetivo. También crea `source_manifest.json` con la huella técnica de las fuentes. Otra persona puede ejecutar el mismo comando si dispone de los tres ficheros autorizados.

La ejecución realizada para esta entrega partió de 6.000 filas Bronze. Tras eliminar 347 duplicados quedaron 5.653 y, después de aplicar los controles de calidad, el Gold quedó formado por 5.605 observaciones y 30 columnas. Los descartes secuenciales fueron 2 por precio, 41 por superficie, 2 por dormitorios y 3 por baños; todas las operaciones eran de venta. La validación final no detectó incumplimientos del contrato. El informe registró 3.018 valores ausentes en planta, 2.904 en la condición de ático, 1.854 en conservación, 191 en dormitorios, 189 en baños y 118 en barrio. No aparecieron valores binarios desconocidos en la captura de abril. Estas ausencias se mantienen como nulos para tratarlas correctamente dentro de la fase de modelado.

Para reproducir el recorrido sin acceder a datos restringidos, `examples/entrega02` contiene una entrada Bronze ficticia, su Gold esperado y un informe de calidad sin datos sensibles. El ejemplo demuestra la exclusión de una fecha futura y una coordenada inválida, la conservación de un binario desconocido como nulo y el tratamiento separado de un ático.

## 5 Riesgos y limitaciones

El dato más importante que falta es el precio real de cierre; el objetivo disponible es precio anunciado y puede incorporar expectativas o estrategias comerciales. La muestra solo cubre Madrid, Sevilla y Córdoba y es una captura transversal de anuncios activos, por lo que tendrá sesgo geográfico y sesgo de supervivencia: los inmuebles que permanecen más tiempo publicados pueden estar sobrerrepresentados. Las variables de barrio calculadas con el precio deben construirse dentro del entrenamiento para evitar fuga de información. Si los datos de portal no pueden utilizarse, el proyecto continuará con feeds licenciados y datos propios de agencias. Si falla una fuente de enriquecimiento, Vissotia conservará el último dato oficial fechado o trabajará sin esa variable, mostrando la limitación al usuario.

## Referencias de uso y acceso

- Dirección General del Catastro. Acceso a información catastral no protegida y servicios web: https://www.catastro.hacienda.gob.es/es-es/acceso_infocat.html
- Instituto Nacional de Estadística. Datos abiertos y API JSON: https://www.ine.es/datosabiertos/
- Instituto Nacional de Estadística. Condiciones de reutilización y CC BY 4.0: https://www.ine.es/aviso_legal/
- Google Maps Platform. Políticas de Places API: https://developers.google.com/maps/documentation/places/web-service/policies

Consulta realizada el 25 de octubre de 2026.
