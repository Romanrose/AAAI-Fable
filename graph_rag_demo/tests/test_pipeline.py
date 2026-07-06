import json
import tempfile
import unittest
from pathlib import Path

from graph_rag_demo.backends import BackendError, DeepSeekBackend
from graph_rag_demo.fixtures import generation_fixture, mechanism_fixture
from graph_rag_demo.pipeline import (
    PipelineError,
    run_demo,
    validate_generation,
)


class PipelineTests(unittest.TestCase):
    @staticmethod
    def _story_generation_for(mechanism):
        node_anchors = [
            f"石阶{index}"
            for index, _node in enumerate(mechanism["mechanism_graph"]["nodes"], start=1)
        ]
        edge_anchors = [
            f"转弯{index}"
            for index, _edge in enumerate(mechanism["mechanism_graph"]["edges"], start=1)
        ]
        narrative = (
            "清晨，学徒穿过"
            + "、".join(node_anchors[: min(3, len(node_anchors))])
            + "，又在院子深处记住"
            + "、".join(node_anchors[min(3, len(node_anchors)) :])
            + "。随后他沿着"
            + "、".join(edge_anchors)
            + "慢慢前进，每过一处都换一种做法。等夕阳落下，他终于把整套工序连成一气，也明白前一步总会推着后一步继续发生。"
        )
        return {
            "narrative": narrative,
            "node_alignments": [
                {
                    "concept_node_id": node["id"],
                    "narrative_element": f"故事中的{anchor}",
                    "evidence": f"{node['text']}对应故事中的{anchor}",
                    "narrative_anchor": anchor,
                }
                for node, anchor in zip(
                    mechanism["mechanism_graph"]["nodes"], node_anchors, strict=False
                )
            ],
            "edge_alignments": [
                {
                    "concept_edge_id": edge["id"],
                    "narrative_relation": f"{anchor}推动下一步",
                    "evidence": f"{edge['relation']}在故事中体现为{anchor}推动下一步",
                    "narrative_anchor": anchor,
                    "narrative_source_concept_node_id": edge["source"],
                    "narrative_target_concept_node_id": edge["target"],
                    "direction_preserved": True,
                }
                for edge, anchor in zip(
                    mechanism["mechanism_graph"]["edges"], edge_anchors, strict=False
                )
            ],
        }

    def test_fixture_demo_runs_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            report = run_demo(
                concept="光合作用",
                subject="biology",
                backend_name="fixture",
                output_dir=output,
            )
            for name in (
                "01_retrieved_subgraph.json",
                "02_mechanism_graph.json",
                "03_generation.jsonl",
                "04_metrics.json",
            ):
                self.assertTrue((output / name).is_file(), name)

            summary = report["summary"]
            for metric in (
                "format_validity",
                "node_coverage",
                "edge_coverage",
                "alignment_precision",
                "relation_direction_accuracy",
            ):
                self.assertEqual(summary[metric], 1.0, metric)
            self.assertEqual(summary["exact_concept_leakage"], 0.0)
            self.assertEqual(summary["soft_term_leakage"], 0.0)

            record = json.loads(
                (output / "03_generation.jsonl").read_text(encoding="utf-8")
            )
            self.assertEqual(record["retrieval"]["selected_edge_count"], 12)
            self.assertIn("retrieval_analysis", record)
            self.assertIn("mechanism_plan", json.loads(
                (output / "02_mechanism_graph.json").read_text(encoding="utf-8")
            ))

    def test_path_dual_fixture_demo_runs_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            report = run_demo(
                concept="光合作用",
                subject="biology",
                backend_name="fixture",
                output_dir=output,
                retrieval_mode="path_dual",
                max_hops=2,
                max_paths=5,
                max_edges=16,
            )
            subgraph = json.loads(
                (output / "01_retrieved_subgraph.json").read_text(encoding="utf-8")
            )
            self.assertEqual(subgraph["retrieval"]["retrieval_mode"], "path_dual")
            self.assertTrue(subgraph["selected_paths"])
            self.assertIn("definition_summary", subgraph["topic_summary"])

            record = json.loads(
                (output / "03_generation.jsonl").read_text(encoding="utf-8")
            )
            self.assertEqual(record["retrieval"]["retrieval_mode"], "path_dual")
            self.assertGreater(record["retrieval"]["selected_path_count"], 0)
            self.assertGreater(record["retrieval_analysis"]["retrieval_path_count"], 0)
            self.assertEqual(report["summary"]["node_coverage"], 1.0)
            self.assertEqual(report["summary"]["edge_coverage"], 1.0)

    def test_invalid_generation_is_rejected(self):
        generation = generation_fixture()
        generation["narrative"] = "太短"
        errors = validate_generation(generation, mechanism_fixture())
        self.assertTrue(any("90 to 260" in error for error in errors))

    def test_leaky_generation_is_rejected(self):
        generation = generation_fixture()
        generation["narrative"] += "光合作用"
        errors = validate_generation(generation, mechanism_fixture())
        self.assertTrue(any("leaks forbidden terms" in error for error in errors))

    def test_missing_concept_preserves_no_fake_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with self.assertRaisesRegex(ValueError, "was not found"):
                run_demo(
                    concept="不存在的概念",
                    subject="biology",
                    output_dir=output,
                )
            self.assertFalse((output / "03_generation.jsonl").exists())

    def test_missing_api_key_preserves_retrieved_subgraph(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            backend = DeepSeekBackend(api_key="")
            with self.assertRaises(BackendError):
                run_demo(
                    concept="光合作用",
                    subject="biology",
                    output_dir=output,
                    backend=backend,
                )
            self.assertTrue((output / "01_retrieved_subgraph.json").is_file())
            self.assertFalse((output / "02_mechanism_graph.json").exists())

    def test_invalid_model_generation_preserves_mechanism(self):
        class InvalidBackend:
            name = "invalid"

            def extract_mechanism(self, subgraph):
                return mechanism_fixture()

            def generate_narrative(self, mechanism):
                value = generation_fixture()
                value["narrative"] = "太短"
                return value

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with self.assertRaises(PipelineError):
                run_demo(
                    concept="光合作用",
                    subject="biology",
                    output_dir=output,
                    backend=InvalidBackend(),
                )
            self.assertTrue((output / "01_retrieved_subgraph.json").is_file())
            self.assertTrue((output / "02_mechanism_graph.json").is_file())
            self.assertFalse((output / "03_generation.jsonl").exists())

    def test_invalid_mechanism_is_repaired_before_generation(self):
        class RepairBackend:
            name = "repair"

            def extract_mechanism(self, subgraph):
                value = mechanism_fixture()
                value["mechanism_plan"]["steps"] = value["mechanism_plan"]["steps"][:2]
                value["mechanism_plan"]["dependencies"] = value["mechanism_plan"][
                    "dependencies"
                ][:1]
                value["mechanism_graph"]["nodes"] = value["mechanism_graph"]["nodes"][:2]
                value["mechanism_graph"]["edges"] = value["mechanism_graph"]["edges"][:1]
                value["grounding"]["source_edge_ids"] = ["missing-edge"]
                return value

            def generate_narrative(self, mechanism):
                return PipelineTests._story_generation_for(mechanism)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            report = run_demo(
                concept="光合作用",
                subject="biology",
                output_dir=output,
                backend=RepairBackend(),
            )
            mechanism = json.loads(
                (output / "02_mechanism_graph.json").read_text(encoding="utf-8")
            )
            self.assertGreaterEqual(len(mechanism["mechanism_graph"]["nodes"]), 4)
            self.assertLessEqual(len(mechanism["mechanism_graph"]["nodes"]), 6)
            self.assertGreaterEqual(len(mechanism["mechanism_graph"]["edges"]), 3)
            self.assertLessEqual(len(mechanism["mechanism_graph"]["edges"]), 6)
            self.assertEqual(report["summary"]["format_validity"], 1.0)
            self.assertEqual(report["summary"]["alignment_precision"], 1.0)

    def test_generation_validation_can_repair_twice(self):
        class TwoStepRepairBackend:
            name = "two_step_repair"

            def __init__(self):
                self.calls = 0

            def extract_mechanism(self, subgraph):
                return mechanism_fixture()

            def generate_narrative(self, mechanism, repair_errors=None):
                self.calls += 1
                value = PipelineTests._story_generation_for(mechanism)
                if self.calls == 1:
                    value["narrative"] = "太短"
                    return value
                if self.calls == 2:
                    value["edge_alignments"][0][
                        "narrative_source_concept_node_id"
                    ] = value["edge_alignments"][0][
                        "narrative_target_concept_node_id"
                    ]
                    return value
                return value

        backend = TwoStepRepairBackend()
        with tempfile.TemporaryDirectory() as directory:
            report = run_demo(
                concept="光合作用",
                subject="biology",
                output_dir=Path(directory),
                backend=backend,
            )
            self.assertEqual(backend.calls, 3)
            self.assertEqual(report["generation_repair_attempts"], 2)
            self.assertEqual(report["summary"]["format_validity"], 1.0)
            self.assertEqual(report["summary"]["relation_direction_accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
