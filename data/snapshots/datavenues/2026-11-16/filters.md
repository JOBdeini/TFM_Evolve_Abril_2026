# Filtros de la captura del 16 de noviembre de 2026

Este documento registra los criterios utilizados antes de descargar los CSV desde DataVenues. Distinguir el filtrado de origen de la limpieza posterior es necesario para poder reproducir la muestra y explicar qué población representa el modelo.

## Criterios confirmados

| Criterio | Valor |
|---|---|
| Fecha de extracción | 2026-11-16 |
| Proveedor | DataVenues |
| Operación observada en los CSV | Venta |
| Unidad de descarga | Un CSV por municipio/capital |
| Portal de referencia | Fotocasa; Idealista en Bilbao como excepción aprobada |
| Selección previa | Se aplicaron filtros para reducir valores atípicos |
| Límite operativo conocido | Hasta 2.000 observaciones por descarga |

## Parámetros que debe confirmar el jefe de proyecto

Los valores exactos no pueden deducirse de forma fiable a partir del mínimo y máximo observado en cada CSV. Deben consignarse tal como se aplicaron en DataVenues:

| Parámetro | Valor aplicado |
|---|---|
| Precio mínimo | Pendiente de confirmar |
| Precio máximo | Pendiente de confirmar |
| Superficie mínima | Pendiente de confirmar |
| Superficie máxima | Pendiente de confirmar |
| Tipologías incluidas/excluidas | Pendiente de confirmar |
| Estado del anuncio | Pendiente de confirmar |
| Dormitorios/baños | Pendiente de confirmar |
| Otros filtros de DataVenues | Pendiente de confirmar |

Si los parámetros variaron entre municipios, deberán documentarse por separado en la tabla siguiente.

| Municipio/carpeta | Portal previsto | Filtros específicos | Estado documental |
|---|---|---|---|
| A Coruña | Fotocasa | Pendiente de confirmar | Fuente verificada |
| Bilbao | Idealista | Pendiente de confirmar | Excepción aprobada por mayor cobertura |
| Córdoba | Fotocasa | Pendiente de confirmar | Fuente verificada |
| Cuenca | Fotocasa | Pendiente de confirmar | Fuente verificada |
| Granada | Fotocasa | Pendiente de confirmar | Fuente verificada |
| Madrid | Fotocasa | Pendiente de confirmar | Fuente verificada |
| Sevilla | Fotocasa | Pendiente de confirmar | Fuente verificada |
| Valencia | Fotocasa | Pendiente de confirmar | Fuente verificada |

## Reglas que se aplicarán después de la descarga

Estas reglas pertenecen al pipeline y no deben confundirse con los filtros de DataVenues:

- conservar Bronze sin cambios;
- eliminar de la capa procesada la única fila de Arrigorriaga incluida en el CSV de Bilbao;
- normalizar nombres, tipos y unidades en Silver;
- retirar datos personales e identificativos del conjunto analítico;
- comprobar precios, superficies y coordenadas inválidos mediante reglas trazables;
- localizar duplicados dentro de la captura;
- localizar viviendas republicadas entre abril y noviembre únicamente mediante coincidencia exacta del identificador técnico; no excluir inmuebles por similitud de características;
- separar las variables disponibles en el momento de estimación de las señales posteriores, como `Días`;
- mantener `Demanda` fuera del modelo hasta documentar su definición y disponibilidad temporal.

No se eliminarán observaciones de forma silenciosa: cada regla deberá registrar el número de filas afectadas y el motivo.

