#!/usr/bin/env python3
"""Prepara un dataset Gold minimizado para la valoración residencial de Vissotia.

El script espera tres CSV históricos en un directorio local y no modifica los
ficheros de origen. Los datos personales y los identificadores del anuncio no
se incorporan al resultado. Tampoco se generan variables derivadas del precio
objetivo para evitar fuga de información en la fase de modelado.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


INPUT_FILES = {
    "DataVenues_Madrid.csv": "Madrid",
    "DataVenues_Sevilla.csv": "Sevilla",
    "DataVenues_cordoba.csv": "Córdoba",
}

DEFAULT_EXTRACTION_DATE = "2026-04-06"

BOOLEAN_COLUMNS = [
    "aire_acondicionado",
    "ascensor",
    "garaje",
    "trastero",
    "terraza",
    "piscina",
    "zonas_verdes",
    "zona_deportiva",
]

OUTPUT_COLUMNS = [
    "id_observacion",
    "fecha_publicacion",
    "fecha_extraccion",
    "operacion",
    "tipologia",
    "codigo_postal",
    "municipio",
    "provincia",
    "distrito",
    "barrio",
    "latitud_aprox",
    "longitud_aprox",
    "planta_num",
    *BOOLEAN_COLUMNS,
    "conservacion",
    "dormitorios",
    "banos",
    "superficie_m2",
    "dias_publicado",
    "demanda",
    "origen_dataset",
    "precio_objetivo_eur",
]


def normalize_column(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


def valid_iso_date(value: str) -> str:
    """Valida y normaliza una fecha ISO YYYY-MM-DD."""
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Fecha no válida: {value!r}. Use el formato YYYY-MM-DD."
        ) from exc


def normalize_boolean(value: object) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip().lower()
    if text in {"1", "si", "sí", "true", "verdadero", "yes", "x"}:
        return 1.0
    if text in {"0", "no", "false", "falso"}:
        return 0.0
    return np.nan


def normalize_floor(value: object) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip().lower()
    if "bajo" in text:
        return 0.0
    if "entreplanta" in text:
        return 0.5
    if "atico" in normalize_column(text):
        return 99.0
    match = re.search(r"-?\d+(?:[.,]\d+)?", text)
    return float(match.group(0).replace(",", ".")) if match else np.nan


def stable_observation_id(row: pd.Series) -> str:
    """Genera un identificador técnico que no depende del precio objetivo.

    Siempre que existe referencia o URL, ``_identity_basis`` contiene su
    versión normalizada. Si ambas faltan se usa una huella de atributos no
    personales. El valor original nunca se exporta al Gold.
    """
    identity_basis = row.get("_identity_basis")
    if pd.isna(identity_basis) or not str(identity_basis).strip():
        fallback = [
            row.get("fecha_publicacion"),
            row.get("municipio"),
            row.get("distrito"),
            row.get("barrio"),
            row.get("tipologia"),
            row.get("superficie_m2"),
            row.get("dormitorios"),
            row.get("banos"),
            row.get("latitud_aprox"),
            row.get("longitud_aprox"),
        ]
        identity_basis = "fallback|" + "|".join(
            "" if pd.isna(value) else str(value) for value in fallback
        )
    parts = [row.get("origen_dataset"), identity_basis]
    raw = "|".join("" if pd.isna(value) else str(value) for value in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def fallback_identity_basis(row: pd.Series) -> str:
    """Crea una identidad de último recurso para la extracción actual.

    El número de fila solo se incorpora cuando la fuente carece tanto de
    referencia como de URL. Así se mantiene unicidad sin mezclar el precio.
    """
    parts = [
        row.get("fecha_publicacion"),
        row.get("municipio"),
        row.get("distrito"),
        row.get("barrio"),
        row.get("tipologia"),
        row.get("superficie_m2"),
        row.get("dormitorios"),
        row.get("banos"),
        row.get("latitud_aprox"),
        row.get("longitud_aprox"),
        row.get("_source_row_number"),
    ]
    return "fallback|" + "|".join(
        "" if pd.isna(value) else str(value) for value in parts
    )


def normalized_identity_series(frame: pd.DataFrame) -> pd.Series:
    """Prioriza referencia y usa URL como alternativa, solo en memoria."""
    empty = pd.Series(pd.NA, index=frame.index, dtype="string")
    reference = frame.get("referencia", empty).astype("string").str.strip()
    url = frame.get("url", empty).astype("string").str.strip()
    reference = reference.mask(reference.eq(""))
    url = url.mask(url.eq(""))
    return ("ref|" + reference).fillna("url|" + url)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_manifest(
    input_dir: Path, extraction_date: str = DEFAULT_EXTRACTION_DATE
) -> dict[str, object]:
    """Crea trazabilidad técnica y deja explícito el alcance de uso acreditado."""
    files: list[dict[str, object]] = []
    for filename, origin in INPUT_FILES.items():
        path = input_dir / filename
        stat = path.stat()
        header = pd.read_csv(path, nrows=0)
        row_count = len(pd.read_csv(path, usecols=[0]))
        files.append(
            {
                "fichero": filename,
                "origen_dataset": origin,
                "tamano_bytes": stat.st_size,
                "modificado_utc": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
                "sha256": sha256_file(path),
                "filas": row_count,
                "columnas": [str(column) for column in header.columns],
                "proveedor": "DataVenues",
                "modalidad_acceso": (
                    "Descarga ordinaria mediante el acceso de la agencia inmobiliaria"
                ),
                "limite_descarga_registros_por_provincia": 2000,
                "scraping_o_elusion_de_limites": False,
            }
        )
    return {
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "fecha_extraccion_declarada": extraction_date,
        "relacion_con_proveedor": (
            "DataVenues es proveedor de la agencia inmobiliaria en la que trabaja "
            "el responsable del proyecto"
        ),
        "alcance_uso_documentado": (
            "Proyecto académico local, con minimización y sin redistribución"
        ),
        "autorizacion_integracion_producto_comercial": (
            "No documentada; requiere acuerdo expreso antes de reutilizar los datos "
            "en un producto comercial"
        ),
        "nota": (
            "Este manifiesto acredita integridad y procedencia operativa, pero no "
            "constituye una licencia ni amplía los derechos de reutilización."
        ),
        "ficheros": files,
    }


def load_bronze(input_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    missing: list[str] = []
    for filename, origin in INPUT_FILES.items():
        path = input_dir / filename
        if not path.exists():
            missing.append(filename)
            continue
        frame = pd.read_csv(path)
        frame.columns = [normalize_column(column) for column in frame.columns]
        frame["origen_dataset"] = origin
        frame["_source_row_number"] = np.arange(len(frame), dtype=int)
        frames.append(frame)
    if missing:
        raise FileNotFoundError(
            "Faltan ficheros de entrada: " + ", ".join(sorted(missing))
        )
    return pd.concat(frames, ignore_index=True)


def build_silver(
    bronze: pd.DataFrame, extraction_date: str = DEFAULT_EXTRACTION_DATE
) -> tuple[pd.DataFrame, dict[str, object]]:
    extraction_date = valid_iso_date(extraction_date)
    frame = bronze.copy()
    initial_rows = len(frame)

    # La URL y la referencia solo se usan para deduplicar e identificar en
    # memoria. Las filas sin ambas claves se conservan para evitar colapsarlas.
    frame = frame.assign(_identity_basis=normalized_identity_series(frame))
    has_identity = frame["_identity_basis"].notna()
    keyed = frame.loc[has_identity].drop_duplicates(
        subset=["origen_dataset", "_identity_basis"], keep="first"
    )
    unkeyed = frame.loc[~has_identity]
    frame = pd.concat([keyed, unkeyed]).sort_index()
    after_deduplication = len(frame)
    rows_without_identity = int((~has_identity).sum())

    numeric_map = {
        "c_p": "codigo_postal",
        "latitud": "latitud_aprox",
        "longitud": "longitud_aprox",
        "dormitorios": "dormitorios",
        "banos": "banos",
        "superficie": "superficie_m2",
        "dias": "dias_publicado",
        "precio": "precio_objetivo_eur",
    }
    for source, target in numeric_map.items():
        frame[target] = pd.to_numeric(frame.get(source), errors="coerce")

    frame["codigo_postal"] = frame["codigo_postal"].round().astype("Int64")
    frame["latitud_aprox"] = frame["latitud_aprox"].round(3)
    frame["longitud_aprox"] = frame["longitud_aprox"].round(3)
    frame["planta_num"] = frame.get("planta", pd.Series(index=frame.index)).map(normalize_floor)
    frame["fecha_publicacion"] = pd.to_datetime(
        frame.get("fecha_de_creacion"), errors="coerce"
    ).dt.date.astype("string")
    frame["fecha_extraccion"] = extraction_date

    for column in BOOLEAN_COLUMNS:
        frame[column] = frame.get(column, pd.Series(index=frame.index)).map(normalize_boolean).astype("Int64")

    for column in [
        "operacion",
        "tipologia",
        "municipio",
        "provincia",
        "distrito",
        "barrio",
        "conservacion",
        "demanda",
    ]:
        frame[column] = frame.get(column, pd.Series(index=frame.index, dtype="string")).astype("string").str.strip()

    rules = {
        "operacion_venta": frame["operacion"].str.casefold().eq("venta"),
        "precio_superior_10000": frame["precio_objetivo_eur"].gt(10_000),
        "superficie_entre_15_y_1000": frame["superficie_m2"].between(15, 1_000),
        "dormitorios_entre_0_y_15_o_nulo": (
            frame["dormitorios"].isna() | frame["dormitorios"].between(0, 15)
        ),
        "banos_entre_0_y_10_o_nulo": (
            frame["banos"].isna() | frame["banos"].between(0, 10)
        ),
    }
    valid = pd.Series(True, index=frame.index)
    sequential_rejections: dict[str, int] = {}
    for name, rule in rules.items():
        rule = rule.fillna(False)
        sequential_rejections[name] = int((valid & ~rule).sum())
        valid &= rule
    independent_failures = {
        name: int((~rule.fillna(False)).sum()) for name, rule in rules.items()
    }
    frame = frame.loc[valid].copy()
    after_quality_filters = len(frame)

    missing_identity = frame["_identity_basis"].isna()
    frame.loc[missing_identity, "_identity_basis"] = frame.loc[
        missing_identity
    ].apply(fallback_identity_basis, axis=1)
    frame["id_observacion"] = frame.apply(stable_observation_id, axis=1)
    frame = frame.drop_duplicates(subset=["id_observacion"], keep="first")

    quality = {
        "filas_bronze": initial_rows,
        "filas_tras_deduplicacion": after_deduplication,
        "duplicados_eliminados": initial_rows - after_deduplication,
        "filas_sin_referencia_ni_url": rows_without_identity,
        "fallos_independientes_por_regla": independent_failures,
        "descartes_secuenciales_por_regla": sequential_rejections,
        "filas_tras_filtros_calidad": after_quality_filters,
        "filas_silver": len(frame),
        "fecha_extraccion_declarada": extraction_date,
    }
    return frame, quality


def build_gold(silver: pd.DataFrame) -> pd.DataFrame:
    gold = silver.reindex(columns=OUTPUT_COLUMNS).copy()
    return gold.sort_values(
        ["origen_dataset", "fecha_publicacion", "id_observacion"],
        na_position="last",
    ).reset_index(drop=True)


def reference_date_diagnostic(gold: pd.DataFrame) -> dict[str, object]:
    publication_date = pd.to_datetime(gold["fecha_publicacion"], errors="coerce")
    days = pd.to_numeric(gold["dias_publicado"], errors="coerce")
    candidate = publication_date + pd.to_timedelta(days, unit="D")
    valid = candidate.dropna()
    if valid.empty:
        return {
            "fecha_referencia_inferida": None,
            "porcentaje_consistencia": 0.0,
            "nota": "No existen observaciones suficientes para inferir la fecha.",
        }
    counts = valid.dt.date.value_counts()
    inferred = counts.index[0]
    consistency = float(counts.iloc[0] / len(valid))
    extraction_dates = gold.get(
        "fecha_extraccion", pd.Series(dtype="string")
    ).dropna().astype("string").unique()
    declared = extraction_dates[0] if len(extraction_dates) == 1 else None
    return {
        "fecha_referencia_inferida": inferred.isoformat(),
        "fecha_extraccion_declarada": declared,
        "coincide_con_fecha_extraccion_declarada": (
            declared == inferred.isoformat() if declared else None
        ),
        "porcentaje_consistencia": round(consistency * 100, 4),
        "observaciones_evaluadas": int(len(valid)),
        "nota": (
            "Diagnóstico calculado como fecha_publicacion + dias_publicado y "
            "contrastado con la fecha de extracción declarada."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--extraction-date",
        type=valid_iso_date,
        default=DEFAULT_EXTRACTION_DATE,
        help="Fecha de extracción de la captura en formato YYYY-MM-DD.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=0,
        help="0 conserva todas las filas; un valor positivo genera una muestra estable.",
    )
    args = parser.parse_args()

    bronze = load_bronze(args.input_dir)
    silver, quality = build_silver(bronze, extraction_date=args.extraction_date)
    gold = build_gold(silver)

    if args.sample_size > 0 and args.sample_size < len(gold):
        gold = gold.sample(args.sample_size, random_state=42).sort_values("id_observacion")
        gold = gold.reset_index(drop=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    gold_path = args.output_dir / "vissotia_valoracion_gold.csv"
    report_path = args.output_dir / "quality_report.json"
    manifest_path = args.output_dir / "source_manifest.json"
    gold.to_csv(gold_path, index=False)

    quality.update(
        {
            "filas_gold_exportadas": len(gold),
            "columnas_gold": len(gold.columns),
            "diagnostico_fecha_referencia": reference_date_diagnostic(gold),
            "nulos_por_columna": {
                column: int(gold[column].isna().sum()) for column in gold.columns
            },
            "campos_excluidos_por_privacidad": [
                "anunciante",
                "empresa",
                "telefono",
                "email",
                "titulo",
                "url",
                "imagen",
                "comentarios",
                "referencia",
            ],
            "campos_excluidos_por_fuga_objetivo": [
                "precio_unitario",
                "precio_m2_calc",
                "media_precio_barrio",
                "media_precio_distrito",
                "media_precio_municipio",
                "score_zona_precio",
            ],
        }
    )
    report_path.write_text(
        json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest_path.write_text(
        json.dumps(
            source_manifest(args.input_dir, args.extraction_date),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "gold": str(gold_path),
                "quality_report": str(report_path),
                "source_manifest": str(manifest_path),
                "quality": quality,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
