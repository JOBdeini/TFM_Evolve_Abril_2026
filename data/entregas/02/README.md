# Acceso a los datos de la entrega 02

Los CSV históricos no se incluyen en el repositorio porque contienen datos de contacto y porque sus condiciones de reutilización deben validarse antes de redistribuirlos.

Para reproducir la preparación, coloque en un directorio local no versionado estos tres ficheros:

- `DataVenues_Madrid.csv`
- `DataVenues_Sevilla.csv`
- `DataVenues_cordoba.csv`

Después ejecute:

```bash
python scripts/prepare_vissotia_data.py \
  --input-dir /ruta/local/a/los/csv \
  --output-dir data/entregas/02/local_output \
  --extraction-date 2026-04-06
```

El resultado incluye `vissotia_valoracion_gold.csv` y `quality_report.json`. El directorio `local_output` está excluido del control de versiones. Los datos se descargaron de forma ordinaria mediante el acceso de la agencia inmobiliaria a DataVenues, respetando el límite de 2.000 observaciones por provincia y sin scraping ni elusión de controles. El uso documentado es académico, local y sin redistribución; la incorporación de estos datos a un producto comercial requeriría un acuerdo expreso.

El proceso también genera `source_manifest.json`, con nombre, tamaño, fecha de modificación, columnas, checksum SHA-256, procedencia operativa, límite de descarga y alcance de uso declarado. El manifiesto no constituye una licencia ni amplía los derechos de reutilización.

El contrato de las 30 columnas se encuentra en `data/entregas/02/diccionario_datos.md`. Distingue `fecha_publicacion` de `fecha_extraccion`, separa la altura numérica de la condición de ático, define la política para binarios desconocidos y diferencia los predictores disponibles al estimar de las señales posteriores. `dias_publicado` se reserva para seguimiento; `demanda` solo podrá entrar en el valorador inicial si estaba disponible y fechada en ese momento.

El directorio `examples/entrega02` contiene una entrada ficticia, su Gold esperado y un informe de calidad sin datos sensibles. Los tests comprueban que el ejemplo se reproduce con el código actual.

Para instalar el entorno mínimo de esta entrega:

```bash
python -m pip install -r requirements-entrega-02.txt
```

Para ejecutar las pruebas sin utilizar los CSV reales:

```bash
python -m unittest discover -s tests -p 'test_prepare_vissotia_data.py'
```

El informe de calidad desglosa los fallos y descartes por regla. También contrasta la fecha de extracción declarada con el diagnóstico `fecha_publicacion + dias_publicado`.
