import unittest

from graph_rag_demo.retrieval import (
    RetrievalError,
    resolve_concept,
    retrieve_one_hop,
    retrieve_subgraph,
    serialize_subgraph,
)


def sample_graph():
    return {
        "nodes": [
            {
                "id": "c1",
                "label": "Concept",
                "name": "目标",
                "properties": {"definition": "定义"},
            },
            {"id": "c2", "label": "Concept", "name": "前提", "properties": {}},
            {"id": "c3", "label": "Concept", "name": "相关", "properties": {}},
            {
                "id": "c4",
                "label": "Concept",
                "name": "结果",
                "properties": {"definition": "过程产生结果"},
            },
            {"id": "s1", "label": "Section", "name": "章节", "properties": {}},
        ],
        "edges": [
            {
                "source": "c1",
                "source_name": "目标",
                "target": "s1",
                "target_name": "章节",
                "type": "appears_in",
            },
            {
                "source": "c1",
                "source_name": "目标",
                "target": "c3",
                "target_name": "相关",
                "type": "relates_to",
                "properties": {"evidence": "相关证据"},
            },
            {
                "source": "c2",
                "source_name": "前提",
                "target": "c1",
                "target_name": "目标",
                "type": "prerequisites_for",
                "properties": {"evidence": "前提证据"},
            },
            {
                "source": "c3",
                "source_name": "相关",
                "target": "c1",
                "target_name": "目标",
                "type": "is_a",
            },
            {
                "source": "c1",
                "source_name": "目标",
                "target_name_to_ids": {"缺失": ["x"]},
                "type": "tests_concept",
            },
            {
                "source": "c3",
                "source_name": "相关",
                "target": "c4",
                "target_name": "结果",
                "type": "leads_to",
                "properties": {"evidence": "相关过程带来结果"},
            },
            {
                "source": "c1",
                "source_name": "目标",
                "target": "s1",
                "target_name": "章节",
                "type": "relates_to",
                "properties": {"evidence": "章节噪声"},
            },
        ],
    }


class RetrievalTests(unittest.TestCase):
    def test_resolve_exact_and_alias(self):
        nodes = sample_graph()["nodes"]
        nodes[0]["properties"]["aliases"] = ["target"]
        self.assertEqual(resolve_concept(nodes, "目标")["id"], "c1")
        self.assertEqual(resolve_concept(nodes, "TARGET")["id"], "c1")

    def test_ambiguous_fuzzy_query_is_rejected(self):
        nodes = [
            {"id": "1", "label": "Concept", "name": "光合作用"},
            {"id": "2", "label": "Concept", "name": "光合作用的产物"},
        ]
        with self.assertRaisesRegex(RetrievalError, "ambiguous"):
            resolve_concept(nodes, "光合")

    def test_relation_filter_priority_and_source_ids(self):
        subgraph = retrieve_one_hop(sample_graph(), "目标", "biology", max_edges=2)
        self.assertEqual(
            [edge["relation"] for edge in subgraph["edges"]],
            ["prerequisites_for", "is_a"],
        )
        self.assertEqual(
            [edge["source_edge_id"] for edge in subgraph["edges"]],
            ["biology:edge:2", "biology:edge:3"],
        )
        self.assertNotIn("appears_in", {edge["relation"] for edge in subgraph["edges"]})

    def test_serialization_contains_evidence_and_ids(self):
        subgraph = retrieve_one_hop(sample_graph(), "目标", "biology")
        text = serialize_subgraph(subgraph)
        self.assertIn("biology:edge:2", text)
        self.assertIn("前提证据", text)
        self.assertIn("c1", text)

    def test_path_pruned_generates_acyclic_paths_and_filters_sections(self):
        subgraph = retrieve_subgraph(
            sample_graph(),
            "目标",
            "biology",
            retrieval_mode="path_pruned",
            max_hops=2,
            max_paths=4,
            max_edges=6,
        )
        self.assertEqual(subgraph["retrieval"]["retrieval_mode"], "path_pruned")
        self.assertTrue(subgraph["selected_paths"])
        for path in subgraph["selected_paths"]:
            self.assertEqual(len(path["node_ids"]), len(set(path["node_ids"])))
            self.assertNotIn("s1", path["node_ids"])
        self.assertTrue(
            any("c4" in path["node_ids"] for path in subgraph["selected_paths"])
        )
        self.assertNotIn("s1", {node["source_node_id"] for node in subgraph["nodes"]})

    def test_dual_level_adds_topic_summary_without_paths(self):
        subgraph = retrieve_subgraph(
            sample_graph(),
            "目标",
            "biology",
            retrieval_mode="dual_level",
            max_edges=6,
        )
        self.assertEqual(subgraph["retrieval"]["retrieval_mode"], "dual_level")
        self.assertEqual(subgraph["selected_paths"], [])
        self.assertEqual(
            subgraph["topic_summary"]["definition_summary"]["name"],
            "目标",
        )
        self.assertIn("condition_summary", subgraph["topic_summary"])

    def test_retrieval_package_contains_stats_for_batch_analysis(self):
        subgraph = retrieve_subgraph(
            sample_graph(),
            "目标",
            "biology",
            retrieval_mode="path_dual",
            max_hops=2,
            max_paths=4,
            max_edges=6,
        )
        package = subgraph["retrieval_package"]
        self.assertEqual(package["target"]["source_node_id"], "c1")
        self.assertEqual(package["raw_edges"], subgraph["edges"])
        self.assertEqual(package["selected_paths"], subgraph["selected_paths"])
        stats = package["retrieval_stats"]
        self.assertGreater(stats["retrieval_context_chars"], 0)
        self.assertGreater(stats["avg_path_length"], 0)
        self.assertIn("non_mechanism_node_ratio", stats)

    def test_path_dual_serialization_exposes_prompt_contract_sections(self):
        subgraph = retrieve_subgraph(
            sample_graph(),
            "目标",
            "biology",
            retrieval_mode="path_dual",
            max_hops=2,
            max_paths=4,
            max_edges=6,
        )
        text = serialize_subgraph(subgraph)
        self.assertIn("raw_edges", text)
        self.assertIn("selected_paths", text)
        self.assertIn("topic_summary", text)

    def test_unknown_retrieval_mode_is_rejected(self):
        with self.assertRaisesRegex(RetrievalError, "unsupported retrieval mode"):
            retrieve_subgraph(
                sample_graph(),
                "目标",
                "biology",
                retrieval_mode="bad_mode",
            )


if __name__ == "__main__":
    unittest.main()
