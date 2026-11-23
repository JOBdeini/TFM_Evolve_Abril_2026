import sys
import unittest
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_vissotia_data as prep


def valid_row(**overrides):
    row = {
        "referencia": "REF-1",
        "url": "https://example.invalid/1",
        "origen_dataset": "Madrid",
        "_source_row_number": 0,
        "operacion": "Venta",
        "precio": 250000,
        "superficie": 90,
        "dormitorios": 3,
        "banos": 2,
        "c_p": 28001,
        "latitud": 40.4168,
        "longitud": -3.7038,
        "planta": "2",
        "fecha_de_creacion": "2026-01-01",
        "tipologia": "Piso",
        "municipio": "Madrid",
        "provincia": "Madrid",
        "distrito": "Centro",
        "barrio": "Sol",
        "conservacion": "Buen estado",
        "demanda": "media",
        "dias": 95,
    }
    row.update({column: "No" for column in prep.BOOLEAN_COLUMNS})
    row.update(overrides)
    return row


class PreparationTests(unittest.TestCase):
    def test_missing_required_source_column_is_rejected(self):
        frame = pd.DataFrame([valid_row()]).drop(columns=["municipio"])
        with self.assertRaisesRegex(ValueError, "municipio"):
            prep.build_silver(frame)

    def test_rows_without_reference_and_url_are_not_collapsed(self):
        rows = [
            valid_row(referencia=np.nan, url=np.nan, _source_row_number=0),
            valid_row(referencia=np.nan, url=np.nan, _source_row_number=1),
        ]
        silver, quality = prep.build_silver(pd.DataFrame(rows))
        self.assertEqual(len(silver), 2)
        self.assertEqual(quality["filas_sin_referencia_ni_url"], 2)

    def test_identifier_does_not_depend_on_price(self):
        base = pd.Series({"origen_dataset": "Madrid", "_identity_basis": "ref|REF-1", "precio_objetivo_eur": 100000})
        changed = base.copy()
        changed["precio_objetivo_eur"] = 200000
        self.assertEqual(
            prep.stable_observation_id(base), prep.stable_observation_id(changed)
        )

    def test_quality_report_breaks_down_rejections(self):
        rows = [
            valid_row(referencia="A", url="u1"),
            valid_row(referencia="B", url="u2", operacion="Alquiler"),
            valid_row(referencia="C", url="u3", precio=5000),
            valid_row(referencia="D", url="u4", superficie=5),
        ]
        silver, quality = prep.build_silver(pd.DataFrame(rows))
        self.assertEqual(len(silver), 1)
        self.assertEqual(quality["descartes_secuenciales_por_regla"]["operacion_venta"], 1)
        self.assertEqual(quality["descartes_secuenciales_por_regla"]["precio_superior_10000"], 1)
        self.assertEqual(quality["descartes_secuenciales_por_regla"]["superficie_entre_15_y_1000"], 1)

    def test_reference_date_diagnostic(self):
        gold = pd.DataFrame(
            {
                "fecha_publicacion": ["2026-04-01", "2026-03-30"],
                "fecha_extraccion": ["2026-04-06", "2026-04-06"],
                "dias_publicado": [5, 7],
            }
        )
        diagnostic = prep.reference_date_diagnostic(gold)
        self.assertEqual(diagnostic["fecha_referencia_inferida"], "2026-04-06")
        self.assertEqual(diagnostic["porcentaje_consistencia"], 100.0)
        self.assertTrue(diagnostic["coincide_con_fecha_extraccion_declarada"])

    def test_extraction_date_is_explicit_and_configurable(self):
        silver, _ = prep.build_silver(
            pd.DataFrame([valid_row()]), extraction_date="2026-04-06"
        )
        self.assertEqual(silver.loc[silver.index[0], "fecha_publicacion"], "2026-01-01")
        self.assertEqual(silver.loc[silver.index[0], "fecha_extraccion"], "2026-04-06")

    def test_invalid_date_and_coordinates_are_rejected_before_gold(self):
        rows = [
            valid_row(referencia="A", fecha_de_creacion="fecha-invalida"),
            valid_row(referencia="B", latitud=120.0),
            valid_row(referencia="C", fecha_de_creacion="2026-04-07"),
        ]
        silver, quality = prep.build_silver(pd.DataFrame(rows))
        self.assertTrue(silver.empty)
        failures = quality["fallos_independientes_por_regla"]
        self.assertEqual(failures["fecha_publicacion_valida"], 1)
        self.assertEqual(failures["fecha_no_posterior_extraccion"], 2)
        self.assertEqual(failures["coordenadas_validas"], 1)

    def test_unknown_binary_is_preserved_as_null_and_reported(self):
        silver, quality = prep.build_silver(
            pd.DataFrame([valid_row(ascensor="Sin información")])
        )
        self.assertTrue(pd.isna(silver.loc[silver.index[0], "ascensor"]))
        self.assertEqual(
            quality["valores_binarios_desconocidos_por_columna"]["ascensor"], 1
        )
        gold = prep.build_gold(silver)
        self.assertEqual(prep.validate_gold_contract(gold)["estado"], "correcto")

    def test_attic_is_separate_from_numeric_floor(self):
        rows = [
            valid_row(referencia="A", planta="Ático"),
            valid_row(referencia="B", planta="Ático 5"),
        ]
        silver, _ = prep.build_silver(pd.DataFrame(rows))
        attic_only = silver.loc[silver["referencia"].eq("A")].iloc[0]
        attic_with_height = silver.loc[silver["referencia"].eq("B")].iloc[0]
        self.assertTrue(pd.isna(attic_only["planta_num"]))
        self.assertEqual(attic_only["es_atico"], 1)
        self.assertEqual(attic_with_height["planta_num"], 5.0)
        self.assertEqual(attic_with_height["es_atico"], 1)

    def test_gold_contract_rejects_required_null(self):
        silver, _ = prep.build_silver(pd.DataFrame([valid_row()]))
        gold = prep.build_gold(silver)
        gold.loc[0, "municipio"] = pd.NA
        with self.assertRaisesRegex(ValueError, "nulos_en_campos_obligatorios"):
            prep.validate_gold_contract(gold)

    def test_fictitious_example_reproduces_expected_gold_and_quality(self):
        example_dir = ROOT / "examples" / "entrega02"
        bronze = pd.read_csv(example_dir / "bronze_ficticio.csv")
        bronze.columns = [prep.normalize_column(column) for column in bronze.columns]
        bronze["origen_dataset"] = "Ejemplo ficticio"
        bronze["_source_row_number"] = np.arange(len(bronze), dtype=int)
        silver, quality = prep.build_silver(bronze, extraction_date="2026-04-06")
        gold = prep.build_gold(silver)
        expected_gold = pd.read_csv(example_dir / "gold_esperado.csv")
        pd.testing.assert_frame_equal(gold, expected_gold, check_dtype=False)

        expected_quality = json.loads(
            (example_dir / "quality_report_ficticio.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            quality["fallos_independientes_por_regla"],
            expected_quality["fallos_independientes_por_regla"],
        )
        self.assertEqual(
            quality["valores_binarios_desconocidos_por_columna"],
            expected_quality["valores_binarios_desconocidos_por_columna"],
        )


if __name__ == "__main__":
    unittest.main()
