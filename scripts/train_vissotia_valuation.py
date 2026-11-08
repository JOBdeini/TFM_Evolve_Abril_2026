#!/usr/bin/env python3
"""Entrena y evalúa el primer modelo académico de valoración de VISSOTIA.

El experimento parte del Gold de la Entrega 02 y predice el precio anunciado
de una vivienda antes de publicarla. Por diseño no usa el precio actual ni
variables derivadas del objetivo. Tampoco usa días publicado o demanda, porque
días publicado solo existe después de publicar y la definición y disponibilidad
temporal de demanda todavía no están suficientemente documentadas.

La separación principal es temporal: el 20 % más reciente se reserva como
test final. La selección se apoya además en validación temporal expansiva sobre
el 80 % de entrenamiento. El script no modifica el Gold de entrada.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import time
from pathlib import Path
from typing import Any, Iterable

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBRegressor


RANDOM_STATE = 42
TARGET = "precio_objetivo_eur"
DATE_COLUMN = "fecha_publicacion"
EXTRACTION_DATE_COLUMN = "fecha_extraccion"
ID_COLUMN = "id_observacion"

# Variables disponibles en el momento de la valoración inicial.
NUMERIC_FEATURES = [
    "latitud_aprox",
    "longitud_aprox",
    "planta_num",
    "aire_acondicionado",
    "ascensor",
    "garaje",
    "trastero",
    "terraza",
    "piscina",
    "zonas_verdes",
    "zona_deportiva",
    "dormitorios",
    "banos",
    "superficie_m2",
    "anio_mercado",
]

CATEGORICAL_FEATURES = [
    "tipologia",
    "codigo_postal",
    "municipio",
    "provincia",
    "distrito",
    "barrio",
    "conservacion",
    "origen_dataset",
    "mes_mercado",
]

EXCLUDED_POST_PUBLICATION = ["dias_publicado"]
EXCLUDED_UNVERIFIED_CONTEXT = ["demanda"]
EXCLUDED_METADATA = [ID_COLUMN, DATE_COLUMN, EXTRACTION_DATE_COLUMN, "operacion"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="CSV Gold de la Entrega 02")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--test-size", type=float, default=0.20)
    parser.add_argument("--cv-splits", type=int, default=4)
    return parser.parse_args()


def load_gold(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {
        ID_COLUMN,
        DATE_COLUMN,
        EXTRACTION_DATE_COLUMN,
        TARGET,
        *NUMERIC_FEATURES[:-1],
        *CATEGORICAL_FEATURES[:-1],
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError("Faltan columnas necesarias en el Gold: " + ", ".join(missing))

    frame[DATE_COLUMN] = pd.to_datetime(frame[DATE_COLUMN], errors="coerce")
    frame[EXTRACTION_DATE_COLUMN] = pd.to_datetime(
        frame[EXTRACTION_DATE_COLUMN], errors="coerce"
    )
    if frame[DATE_COLUMN].isna().any():
        raise ValueError("El Gold contiene fechas de publicación no válidas")
    if frame[EXTRACTION_DATE_COLUMN].isna().any():
        raise ValueError("El Gold contiene fechas de extracción no válidas")
    if (frame[DATE_COLUMN] > frame[EXTRACTION_DATE_COLUMN]).any():
        raise ValueError("Existen publicaciones posteriores a su fecha de extracción")
    if frame[TARGET].isna().any() or (frame[TARGET] <= 0).any():
        raise ValueError("La variable objetivo debe ser positiva y no contener nulos")

    frame["codigo_postal"] = frame["codigo_postal"].map(normalize_postcode)
    # En entrenamiento, la fecha de publicación sitúa cada anuncio en su mercado
    # temporal. En inferencia, estos dos campos se rellenarán con la fecha en que
    # el profesional solicita la valoración, no con una fecha futura de publicación.
    frame["anio_mercado"] = frame[DATE_COLUMN].dt.year.astype(float)
    frame["mes_mercado"] = frame[DATE_COLUMN].dt.month.astype("Int64").astype("string")
    for column in CATEGORICAL_FEATURES:
        frame[column] = frame[column].astype(object).where(frame[column].notna(), np.nan)
    return frame.sort_values([DATE_COLUMN, ID_COLUMN]).reset_index(drop=True)


def normalize_postcode(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA
    try:
        return f"{int(float(value)):05d}"
    except (TypeError, ValueError):
        return str(value).strip()


def temporal_holdout(frame: pd.DataFrame, test_size: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not 0 < test_size < 0.5:
        raise ValueError("--test-size debe estar entre 0 y 0.5")
    split_index = int(math.floor(len(frame) * (1 - test_size)))
    split_date = frame.iloc[split_index][DATE_COLUMN]

    # Una misma fecha nunca se reparte entre train y test.
    train = frame.loc[frame[DATE_COLUMN] < split_date].copy()
    test = frame.loc[frame[DATE_COLUMN] >= split_date].copy()
    if train.empty or test.empty:
        raise ValueError("La partición temporal ha producido un conjunto vacío")
    return train, test


def make_preprocessor(scale_numeric: bool) -> ColumnTransformer:
    numeric_steps: list[tuple[str, Any]] = [
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
    ]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))

    numeric_pipeline = Pipeline(numeric_steps)
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", min_frequency=2),
            ),
        ]
    )
    return ColumnTransformer(
        [
            ("num", numeric_pipeline, NUMERIC_FEATURES),
            ("cat", categorical_pipeline, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def make_models() -> dict[str, Any]:
    baseline = Pipeline(
        [
            ("preprocess", make_preprocessor(scale_numeric=False)),
            ("regressor", DummyRegressor(strategy="median")),
        ]
    )
    ridge = TransformedTargetRegressor(
        regressor=Pipeline(
            [
                ("preprocess", make_preprocessor(scale_numeric=True)),
                ("regressor", Ridge(alpha=10.0)),
            ]
        ),
        func=np.log1p,
        inverse_func=np.expm1,
        check_inverse=False,
    )
    xgb = TransformedTargetRegressor(
        regressor=Pipeline(
            [
                ("preprocess", make_preprocessor(scale_numeric=False)),
                (
                    "regressor",
                    XGBRegressor(
                        objective="reg:squarederror",
                        n_estimators=650,
                        learning_rate=0.035,
                        max_depth=4,
                        min_child_weight=3,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        reg_alpha=0.05,
                        reg_lambda=1.5,
                        random_state=RANDOM_STATE,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        func=np.log1p,
        inverse_func=np.expm1,
        check_inverse=False,
    )
    return {"Baseline mediana": baseline, "Ridge": ridge, "XGBoost": xgb}


def feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[NUMERIC_FEATURES + CATEGORICAL_FEATURES]


def regression_metrics(y_true: Iterable[float], y_pred: Iterable[float]) -> dict[str, float]:
    actual = np.asarray(y_true, dtype=float)
    predicted = np.maximum(np.asarray(y_pred, dtype=float), 0.0)
    ape = np.abs((actual - predicted) / actual) * 100.0
    return {
        "mae_eur": float(mean_absolute_error(actual, predicted)),
        "rmse_eur": float(np.sqrt(mean_squared_error(actual, predicted))),
        "r2": float(r2_score(actual, predicted)),
        "mape_pct": float(np.mean(ape)),
        "mdape_pct": float(np.median(ape)),
    }


def temporal_cross_validation(
    train: pd.DataFrame,
    models: dict[str, Any],
    n_splits: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    calibration_rows: list[dict[str, Any]] = []
    x_all = feature_frame(train)
    y_all = train[TARGET]
    dates = train[DATE_COLUMN]

    for fold, (fit_idx, valid_idx) in enumerate(
        grouped_temporal_splits(train, n_splits), start=1
    ):
        for name, model in make_models().items():
            started = time.perf_counter()
            model.fit(x_all.iloc[fit_idx], y_all.iloc[fit_idx])
            prediction = model.predict(x_all.iloc[valid_idx])
            if name == "XGBoost":
                actual_values = y_all.iloc[valid_idx].to_numpy(dtype=float)
                predicted_values = np.maximum(np.asarray(prediction, dtype=float), 0.0)
                log_residuals = np.abs(
                    np.log1p(actual_values) - np.log1p(predicted_values)
                )
                calibration_rows.extend(
                    {
                        "fold": fold,
                        ID_COLUMN: train.iloc[row_index][ID_COLUMN],
                        "residuo_absoluto_log": float(log_residual),
                    }
                    for row_index, log_residual in zip(valid_idx, log_residuals)
                )
            rows.append(
                {
                    "modelo": name,
                    "fold": fold,
                    "train_hasta": dates.iloc[fit_idx].max().date().isoformat(),
                    "validacion_desde": dates.iloc[valid_idx].min().date().isoformat(),
                    "validacion_hasta": dates.iloc[valid_idx].max().date().isoformat(),
                    "n_train": len(fit_idx),
                    "n_validacion": len(valid_idx),
                    "duracion_segundos": time.perf_counter() - started,
                    **regression_metrics(y_all.iloc[valid_idx], prediction),
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(calibration_rows)


def grouped_temporal_splits(
    frame: pd.DataFrame, n_splits: int
) -> Iterable[tuple[np.ndarray, np.ndarray]]:
    """Genera ventanas expansivas sin repartir una fecha entre train y validación."""
    dates = frame[DATE_COLUMN].reset_index(drop=True)
    total = len(frame)
    for fold in range(1, n_splits + 1):
        start_position = int(math.floor(total * fold / (n_splits + 1)))
        end_position = int(math.floor(total * (fold + 1) / (n_splits + 1)))
        start_date = dates.iloc[start_position]
        end_date = dates.iloc[end_position] if fold < n_splits else None

        fit_mask = dates < start_date
        valid_mask = dates >= start_date
        if end_date is not None:
            valid_mask &= dates < end_date

        fit_idx = np.flatnonzero(fit_mask.to_numpy())
        valid_idx = np.flatnonzero(valid_mask.to_numpy())
        if len(fit_idx) == 0 or len(valid_idx) == 0:
            raise ValueError("No se pudo construir una partición temporal no vacía")
        yield fit_idx, valid_idx


def add_calibrated_interval(
    predictions: pd.DataFrame,
    calibration_residuals: pd.DataFrame,
    coverage: float = 0.90,
) -> tuple[pd.DataFrame, float, float]:
    residuals = calibration_residuals["residuo_absoluto_log"].dropna()
    if residuals.empty:
        raise ValueError("No existen residuos para calibrar el intervalo")
    # Corrección conformal finita y cuantíl superior para no interpolar hacia
    # un intervalo artificialmente más estrecho.
    adjusted_level = min(1.0, math.ceil((len(residuals) + 1) * coverage) / len(residuals))
    quantile = float(residuals.quantile(adjusted_level, interpolation="higher"))
    result = predictions.copy()
    center = np.log1p(result["pred_xgboost"].clip(lower=0.0))
    result["pred_xgboost_min_90"] = np.maximum(np.expm1(center - quantile), 0.0)
    result["pred_xgboost_max_90"] = np.expm1(center + quantile)
    observed_coverage = float(
        (
            (result[TARGET] >= result["pred_xgboost_min_90"])
            & (result[TARGET] <= result["pred_xgboost_max_90"])
        ).mean()
    )
    return result, quantile, observed_coverage


def evaluate_holdout(
    train: pd.DataFrame,
    test: pd.DataFrame,
    models: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    metrics_rows: list[dict[str, Any]] = []
    prediction_frame = test[[ID_COLUMN, DATE_COLUMN, "origen_dataset", TARGET]].copy()
    fitted: dict[str, Any] = {}

    for name, model in models.items():
        started = time.perf_counter()
        model.fit(feature_frame(train), train[TARGET])
        prediction = np.maximum(model.predict(feature_frame(test)), 0.0)
        fitted[name] = model
        prediction_frame[f"pred_{slug(name)}"] = prediction
        metrics_rows.append(
            {
                "modelo": name,
                "n_train": len(train),
                "n_test": len(test),
                "train_hasta": train[DATE_COLUMN].max().date().isoformat(),
                "test_desde": test[DATE_COLUMN].min().date().isoformat(),
                "test_hasta": test[DATE_COLUMN].max().date().isoformat(),
                "duracion_segundos": time.perf_counter() - started,
                **regression_metrics(test[TARGET], prediction),
            }
        )
    return pd.DataFrame(metrics_rows), prediction_frame, fitted


def slug(value: str) -> str:
    return value.lower().replace(" ", "_").replace("ó", "o")


def segment_metrics(test: pd.DataFrame, predictions: pd.DataFrame, column: str) -> pd.DataFrame:
    work = test[[ID_COLUMN, TARGET, column]].merge(
        predictions[[ID_COLUMN, "pred_xgboost"]], on=ID_COLUMN, how="inner"
    )
    rows: list[dict[str, Any]] = []
    for label, group in work.groupby(column, observed=True, dropna=False):
        rows.append(
            {
                "segmento": column,
                "valor": str(label),
                "n": len(group),
                **regression_metrics(group[TARGET], group["pred_xgboost"]),
            }
        )
    return pd.DataFrame(rows)


def price_band_metrics(test: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    work = test[[ID_COLUMN, TARGET]].merge(
        predictions[[ID_COLUMN, "pred_xgboost"]], on=ID_COLUMN, how="inner"
    )
    work["tramo_precio"] = pd.cut(
        work[TARGET],
        bins=[0, 150_000, 300_000, 600_000, np.inf],
        labels=["Hasta 150 mil", "150 a 300 mil", "300 a 600 mil", "Más de 600 mil"],
        include_lowest=True,
    )
    rows: list[dict[str, Any]] = []
    for label, group in work.groupby("tramo_precio", observed=True, dropna=False):
        rows.append(
            {
                "segmento": "tramo_precio",
                "valor": str(label),
                "n": len(group),
                **regression_metrics(group[TARGET], group["pred_xgboost"]),
            }
        )
    return pd.DataFrame(rows)


def city_holdout_evaluation(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for city in sorted(frame["origen_dataset"].dropna().unique()):
        fit = frame.loc[frame["origen_dataset"] != city]
        test = frame.loc[frame["origen_dataset"] == city]
        model = make_models()["XGBoost"]
        model.fit(feature_frame(fit), fit[TARGET])
        prediction = model.predict(feature_frame(test))
        rows.append(
            {
                "ciudad_excluida_del_entrenamiento": city,
                "n_train": len(fit),
                "n_test": len(test),
                **regression_metrics(test[TARGET], prediction),
            }
        )
    return pd.DataFrame(rows)


def extract_feature_importance(model: Any) -> pd.DataFrame:
    pipeline = model.regressor_
    preprocessor = pipeline.named_steps["preprocess"]
    regressor = pipeline.named_steps["regressor"]
    names = preprocessor.get_feature_names_out()
    importance = regressor.feature_importances_
    return (
        pd.DataFrame({"variable_transformada": names, "importancia": importance})
        .sort_values("importancia", ascending=False)
        .reset_index(drop=True)
    )


def save_charts(
    output_dir: Path,
    holdout_metrics: pd.DataFrame,
    test: pd.DataFrame,
    predictions: pd.DataFrame,
    city_metrics: pd.DataFrame,
) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")

    ordered = holdout_metrics.sort_values("mae_eur")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    bars = ax.bar(ordered["modelo"], ordered["mae_eur"], color=["#173F5F", "#3CAEA3", "#F6A623"])
    ax.set_title("Error absoluto medio en el test temporal")
    ax.set_ylabel("MAE en euros")
    ax.bar_label(bars, labels=[f"{v:,.0f} €" for v in ordered["mae_eur"]], padding=4)
    fig.tight_layout()
    fig.savefig(output_dir / "comparacion_modelos_mae.png", dpi=180)
    plt.close(fig)

    merged = test[[ID_COLUMN, TARGET]].merge(
        predictions[[ID_COLUMN, "pred_xgboost"]], on=ID_COLUMN, how="inner"
    )
    cap = float(merged[TARGET].quantile(0.99))
    plot_data = merged.loc[(merged[TARGET] <= cap) & (merged["pred_xgboost"] <= cap)]
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.scatter(plot_data[TARGET], plot_data["pred_xgboost"], s=16, alpha=0.45, color="#173F5F")
    ax.plot([0, cap], [0, cap], linestyle="--", color="#C0392B", linewidth=1.5)
    ax.set_title("Precio real y predicción de XGBoost")
    ax.set_xlabel("Precio anunciado real en euros")
    ax.set_ylabel("Predicción en euros")
    fig.tight_layout()
    fig.savefig(output_dir / "real_vs_predicho_xgboost.png", dpi=180)
    plt.close(fig)

    city_order = city_metrics.sort_values("mae_eur")
    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    bars = ax.bar(city_order["valor"], city_order["mae_eur"], color="#3CAEA3")
    ax.set_title("Error de XGBoost por ciudad en el test temporal")
    ax.set_ylabel("MAE en euros")
    ax.tick_params(axis="x", labelsize=9, pad=7)
    ax.margins(x=0.12)
    ax.bar_label(bars, labels=[f"{v:,.0f} €" for v in city_order["mae_eur"]], padding=4)
    fig.tight_layout()
    fig.savefig(output_dir / "error_xgboost_por_ciudad.png", dpi=180)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    frame = load_gold(args.input)
    train, test = temporal_holdout(frame, args.test_size)
    models = make_models()

    cv_results, calibration_residuals = temporal_cross_validation(
        train, models, args.cv_splits
    )
    holdout_metrics, predictions, fitted = evaluate_holdout(train, test, models)
    predictions, interval_log_quantile, interval_test_coverage = add_calibrated_interval(
        predictions, calibration_residuals
    )
    city_metrics = segment_metrics(test, predictions, "origen_dataset")
    band_metrics = price_band_metrics(test, predictions)
    city_holdout = city_holdout_evaluation(frame)
    feature_importance = extract_feature_importance(fitted["XGBoost"])

    cv_summary = (
        cv_results.groupby("modelo", as_index=False)
        .agg(
            mae_eur_media=("mae_eur", "mean"),
            mae_eur_desv=("mae_eur", "std"),
            rmse_eur_media=("rmse_eur", "mean"),
            r2_media=("r2", "mean"),
            mape_pct_media=("mape_pct", "mean"),
            mdape_pct_media=("mdape_pct", "mean"),
        )
        .sort_values("mae_eur_media")
    )

    holdout_metrics.to_csv(args.output_dir / "comparacion_modelos_test_temporal.csv", index=False)
    cv_results.to_csv(args.output_dir / "validacion_temporal_folds.csv", index=False)
    calibration_residuals.to_csv(
        args.output_dir / "residuos_calibracion_xgboost.csv", index=False
    )
    cv_summary.to_csv(args.output_dir / "validacion_temporal_resumen.csv", index=False)
    predictions.to_csv(args.output_dir / "predicciones_test_temporal.csv", index=False)
    city_metrics.to_csv(args.output_dir / "metricas_xgboost_por_ciudad.csv", index=False)
    band_metrics.to_csv(args.output_dir / "metricas_xgboost_por_tramo_precio.csv", index=False)
    city_holdout.to_csv(args.output_dir / "generalizacion_ciudad_excluida.csv", index=False)
    feature_importance.to_csv(args.output_dir / "importancia_variables_xgboost.csv", index=False)
    joblib.dump(fitted["XGBoost"], args.output_dir / "modelo_valoracion_inicial_xgboost.joblib")

    save_charts(args.output_dir, holdout_metrics, test, predictions, city_metrics)

    report = {
        "experiment": "valoracion_inicial_v1_sin_fuga_objetivo",
        "input_path": str(args.input.resolve()),
        "rows_total": len(frame),
        "rows_train": len(train),
        "rows_test": len(test),
        "train_date_min": train[DATE_COLUMN].min().date().isoformat(),
        "train_date_max": train[DATE_COLUMN].max().date().isoformat(),
        "test_date_min": test[DATE_COLUMN].min().date().isoformat(),
        "test_date_max": test[DATE_COLUMN].max().date().isoformat(),
        "target": TARGET,
        "temporal_order_column": DATE_COLUMN,
        "extraction_date_min": frame[EXTRACTION_DATE_COLUMN].min().date().isoformat(),
        "extraction_date_max": frame[EXTRACTION_DATE_COLUMN].max().date().isoformat(),
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "excluded_post_publication": EXCLUDED_POST_PUBLICATION,
        "excluded_unverified_context": EXCLUDED_UNVERIFIED_CONTEXT,
        "excluded_metadata": EXCLUDED_METADATA,
        "metrics_test_temporal": holdout_metrics.to_dict(orient="records"),
        "metrics_cv_temporal": cv_summary.to_dict(orient="records"),
        "prediction_interval": {
            "method": "simetrico_en_escala_log_calibrado_con_residuos_temporales",
            "nominal_coverage": 0.90,
            "absolute_log_residual_quantile": interval_log_quantile,
            "observed_test_coverage": interval_test_coverage,
        },
        "versions": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            "xgboost": xgboost.__version__,
            "joblib": joblib.__version__,
        },
        "random_state": RANDOM_STATE,
    }
    (args.output_dir / "experiment_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
