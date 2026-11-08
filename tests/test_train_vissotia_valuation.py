import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import train_vissotia_valuation as training


def gold_row(index: int, publication_date: str) -> dict[str, object]:
    row: dict[str, object] = {
        "id_observacion": f"id-{index}",
        "fecha_publicacion": publication_date,
        "fecha_extraccion": "2026-04-06",
        "precio_objetivo_eur": 200_000 + index * 1_000,
        "operacion": "Venta",
        "tipologia": "Plurifamiliar",
        "codigo_postal": 28001,
        "municipio": "Madrid",
        "provincia": "Madrid",
        "distrito": "Centro",
        "barrio": "Sol",
        "conservacion": "Bueno",
        "origen_dataset": "Madrid",
        "demanda": "Moderada",
        "dias_publicado": 10,
    }
    for column in training.NUMERIC_FEATURES[:-1]:
        row.setdefault(column, 1.0)
    return row


class TrainingTests(unittest.TestCase):
    def test_load_gold_uses_new_temporal_contract(self):
        frame = pd.DataFrame([gold_row(1, "2026-03-15")])
        path = ROOT / ".codex_tmp" / "test_gold_entrega03.csv"
        path.parent.mkdir(exist_ok=True)
        frame.to_csv(path, index=False)
        loaded = training.load_gold(path)
        self.assertEqual(loaded.loc[0, "anio_mercado"], 2026.0)
        self.assertEqual(loaded.loc[0, "mes_mercado"], "3")
        self.assertEqual(training.DATE_COLUMN, "fecha_publicacion")

    def test_publication_after_extraction_is_rejected(self):
        frame = pd.DataFrame([gold_row(1, "2026-04-07")])
        path = ROOT / ".codex_tmp" / "test_gold_future_publication.csv"
        path.parent.mkdir(exist_ok=True)
        frame.to_csv(path, index=False)
        with self.assertRaisesRegex(ValueError, "posteriores"):
            training.load_gold(path)

    def test_temporal_holdout_does_not_split_same_day(self):
        dates = ["2026-03-01"] * 4 + ["2026-03-02"] * 4 + ["2026-03-03"] * 4
        frame = pd.DataFrame([gold_row(i, value) for i, value in enumerate(dates)])
        frame[training.DATE_COLUMN] = pd.to_datetime(frame[training.DATE_COLUMN])
        train, test = training.temporal_holdout(frame, 0.25)
        self.assertLess(train[training.DATE_COLUMN].max(), test[training.DATE_COLUMN].min())
        self.assertTrue(set(train[training.DATE_COLUMN]).isdisjoint(test[training.DATE_COLUMN]))

    def test_demand_is_not_a_feature_until_its_semantics_are_documented(self):
        features = set(training.NUMERIC_FEATURES + training.CATEGORICAL_FEATURES)
        self.assertNotIn("demanda", features)
        self.assertIn("demanda", training.EXCLUDED_UNVERIFIED_CONTEXT)


if __name__ == "__main__":
    unittest.main()
