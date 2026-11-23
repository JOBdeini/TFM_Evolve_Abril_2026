# Ejemplo ficticio de preparación de datos

Estos archivos permiten seguir el recorrido Bronze a Gold sin disponer de los CSV de la agencia. Todos los valores son inventados y no representan inmuebles, anunciantes ni contactos reales.

- `bronze_ficticio.csv` contiene tres anuncios de prueba con el esquema de DataVenues.
- `gold_esperado.csv` contiene la única fila que supera los controles.
- `quality_report_ficticio.json` muestra los descartes y la política aplicada a datos desconocidos.

El ejemplo incluye un ático sin altura numérica, un valor binario desconocido, una coordenada inválida y una fecha posterior a la extracción. El ático se conserva mediante `es_atico=1`, el binario desconocido permanece nulo y las dos filas inválidas se excluyen antes de Gold.

