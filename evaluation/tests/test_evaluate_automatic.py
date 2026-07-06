import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "evaluate_automatic.py"
SPEC = importlib.util.spec_from_file_location("evaluate_automatic", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def valid_record():
    return {
        "id": "sample",
        "method": "full",
        "concept": {
            "name": "路径依赖",
            "aliases": ["path dependence"],
            "forbidden_terms": ["正反馈"],
        },
        "mechanism_graph": {
            "nodes": [
                {"id": "n1", "text": "初始选择"},
                {"id": "n2", "text": "强化"},
            ],
            "edges": [
                {
                    "id": "e1",
                    "source": "n1",
                    "target": "n2",
                    "relation": "enables",
                }
            ],
        },
        "output": {
            "narrative": "店主先买了一口炉，菜单随后都围着这口炉设计。",
            "node_alignments": [
                {
                    "concept_node_id": "n1",
                    "narrative_element": "买炉",
                    "evidence": "最初选择了炉子",
                    "narrative_anchor": "店主先买了一口炉",
                },
                {
                    "concept_node_id": "n2",
                    "narrative_element": "菜单适应",
                    "evidence": "后续安排围绕旧选择展开",
                    "narrative_anchor": "菜单随后都围着这口炉设计",
                },
            ],
            "edge_alignments": [
                {
                    "concept_edge_id": "e1",
                    "narrative_relation": "买炉促使菜单适应",
                    "evidence": "初始选择推动后续适应",
                    "narrative_anchor": "菜单随后都围着这口炉设计",
                    "narrative_source_concept_node_id": "n1",
                    "narrative_target_concept_node_id": "n2",
                    "direction_preserved": True,
                }
            ],
        },
    }


class EvaluationTests(unittest.TestCase):
    def test_valid_record_scores_full_coverage(self):
        result = MODULE.evaluate_record(valid_record())
        self.assertEqual(result["format_validity"], 1.0)
        self.assertEqual(result["node_coverage"], 1.0)
        self.assertEqual(result["edge_coverage"], 1.0)
        self.assertEqual(result["alignment_precision"], 1.0)
        self.assertEqual(result["relation_direction_accuracy"], 1.0)
        self.assertEqual(result["exact_concept_leakage"], 0.0)

    def test_leakage_is_case_and_whitespace_insensitive(self):
        record = valid_record()
        record["output"]["narrative"] += " PATH  DEPENDENCE 与正反馈"
        result = MODULE.evaluate_record(record)
        self.assertEqual(result["exact_concept_leakage"], 1.0)
        self.assertEqual(result["soft_term_leakage"], 1.0)

    def test_unknown_id_and_missing_evidence_are_hallucinations(self):
        record = valid_record()
        record["output"]["node_alignments"].append(
            {
                "concept_node_id": "unknown",
                "narrative_element": "虚构",
                "evidence": "正文没有的证据",
            }
        )
        result = MODULE.evaluate_record(record)
        self.assertAlmostEqual(result["alignment_precision"], 0.75)
        self.assertAlmostEqual(result["alignment_hallucination_rate"], 0.25)
        self.assertEqual(result["node_coverage"], 1.0)

    def test_invalid_graph_reference_fails_format_validation(self):
        record = valid_record()
        record["mechanism_graph"]["edges"][0]["target"] = "missing"
        result = MODULE.evaluate_record(record)
        self.assertEqual(result["format_validity"], 0.0)
        self.assertTrue(result["validation_errors"])
        self.assertNotIn("node_coverage", result)

    def test_empty_edges_have_full_vacuous_coverage(self):
        record = valid_record()
        record["mechanism_graph"]["edges"] = []
        record["output"]["edge_alignments"] = []
        result = MODULE.evaluate_record(record)
        self.assertEqual(result["edge_coverage"], 1.0)
        self.assertIsNone(result["relation_direction_accuracy"])

    def test_direction_is_computed_from_structure_not_legacy_flag(self):
        record = valid_record()
        alignment = record["output"]["edge_alignments"][0]
        alignment["narrative_source_concept_node_id"] = "n2"
        alignment["narrative_target_concept_node_id"] = "n1"
        alignment["direction_preserved"] = True
        result = MODULE.evaluate_record(record)
        self.assertEqual(result["edge_coverage"], 1.0)
        self.assertEqual(result["relation_direction_accuracy"], 0.0)

    def test_load_jsonl_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            path.write_text("{bad json}\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                MODULE.load_jsonl(path)

    def test_aggregate_groups_methods(self):
        first = MODULE.evaluate_record(valid_record())
        second_record = valid_record()
        second_record["id"] = "sample-2"
        second_record["method"] = "direct"
        second = MODULE.evaluate_record(second_record)
        grouped = MODULE.group_by_method([first, second])
        self.assertEqual(grouped["full"]["sample_count"], 1)
        self.assertEqual(grouped["direct"]["sample_count"], 1)


if __name__ == "__main__":
    unittest.main()
