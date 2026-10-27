import sys
import unittest
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


if __name__ == "__main__":
    unittest.main()
