import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


EVALUATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVALUATION_DIR))


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, EVALUATION_DIR / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GENERATOR = load_module("generate_stress_cases", "generate_stress_cases.py")
STRESS = load_module("evaluate_stress", "evaluate_stress.py")
AUTOMATIC = load_module("evaluate_automatic_stress", "evaluate_automatic.py")
BASE_PATH = EVALUATION_DIR / "stress" / "base_records.jsonl"


class StressSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_records = AUTOMATIC.load_jsonl(BASE_PATH)
        cls.cases = GENERATOR.generate_cases(cls.base_records)

    def test_five_bases_generate_twenty_unique_records(self):
        self.assertEqual(len(self.base_records), 5)
        self.assertEqual(len(self.cases), 20)
        ids = [record["id"] for record in self.cases]
        self.assertEqual(len(ids), len(set(ids)))

    def test_each_base_has_exactly_four_expected_types(self):
        expected = {
            "clean",
            "surface_distractor",
            "relation_corruption",
            "mechanism_omission",
        }
        counts = Counter((record["base_id"], record["stress_type"]) for record in self.cases)
        for base in self.base_records:
            base_id = base["base_id"]
            self.assertEqual(
                {stress_type for candidate_base, stress_type in counts if candidate_base == base_id},
                expected,
            )
            for stress_type in expected:
                self.assertEqual(counts[(base_id, stress_type)], 1)

    def test_generation_is_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.jsonl"
            second = Path(directory) / "second.jsonl"
            GENERATOR.write_jsonl(first, GENERATOR.generate_cases(self.base_records))
            GENERATOR.write_jsonl(second, GENERATOR.generate_cases(self.base_records))
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).hexdigest(),
                hashlib.sha256(second.read_bytes()).hexdigest(),
            )

    def test_relation_corruption_ignores_legacy_flag(self):
        candidates = [
            record
            for record in self.cases
            if record["stress_type"] == "relation_corruption"
        ]
        for record in candidates:
            self.assertTrue(record["output"]["edge_alignments"][0]["direction_preserved"])
            result = AUTOMATIC.evaluate_record(record)
            self.assertLess(result["relation_direction_accuracy"], 1.0)
            self.assertEqual(result["edge_coverage"], 1.0)

    def test_surface_theme_overlap_does_not_create_coverage(self):
        candidates = [
            record
            for record in self.cases
            if record["stress_type"] == "surface_distractor"
        ]
        for record in candidates:
            result = AUTOMATIC.evaluate_record(record)
            self.assertEqual(result["node_coverage"], 0.0)
            self.assertEqual(result["edge_coverage"], 0.0)

    def test_omission_reduces_weighted_coverage(self):
        by_base = {}
        for record in self.cases:
            by_base.setdefault(record["base_id"], {})[record["stress_type"]] = record
        for variants in by_base.values():
            clean = AUTOMATIC.evaluate_record(variants["clean"])
            omitted = AUTOMATIC.evaluate_record(variants["mechanism_omission"])
            self.assertTrue(
                omitted["weighted_node_coverage"] < clean["weighted_node_coverage"]
                or omitted["weighted_edge_coverage"] < clean["weighted_edge_coverage"]
            )

    def test_report_meets_acceptance_thresholds(self):
        report = STRESS.build_report(self.cases)
        self.assertTrue(report["passed"])
        self.assertLessEqual(report["clean_samples"]["false_positive_rate"], 0.1)
        for metrics in report["by_stress_type"].values():
            self.assertGreaterEqual(metrics["detection_rate"], 0.9)

    def test_report_serialization_is_deterministic(self):
        first = json.dumps(
            STRESS.build_report(self.cases),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        second = json.dumps(
            STRESS.build_report(self.cases),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
