import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from graph_rag_demo import run_batch


class BatchRunnerTests(unittest.TestCase):
    def test_retrieval_only_default_pilot_writes_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                sys,
                "argv",
                [
                    "run_batch",
                    "--run-mode",
                    "retrieval_only",
                    "--output-dir",
                    directory,
                ],
            ):
                self.assertEqual(run_batch.main(), 0)

            output = Path(directory)
            for name in (
                "batch_report.json",
                "batch_report.md",
                "batch_runs.jsonl",
                "retrieval_table.csv",
            ):
                self.assertTrue((output / name).is_file(), name)

            report = json.loads(
                (output / "batch_report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["run_metadata"]["ok_count"], 40)
            self.assertEqual(report["run_metadata"]["failed_count"], 0)
            self.assertIn("path_dual", report["retrieval_summary_by_mode"])
            self.assertIn(
                "unused_raw_edge_ratio",
                report["retrieval_summary_by_mode"]["path_dual"],
            )

    def test_full_generation_without_deepseek_key_writes_failure_report(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {}, clear=True), patch.object(
                sys,
                "argv",
                [
                    "run_batch",
                    "--run-mode",
                    "full_generation",
                    "--backend",
                    "deepseek",
                    "--output-dir",
                    directory,
                ],
            ):
                self.assertEqual(run_batch.main(), 1)

            report = json.loads(
                (Path(directory) / "batch_report.json").read_text(encoding="utf-8")
            )
            self.assertTrue(report["run_metadata"]["full_generation_blocked"])
            self.assertEqual(report["run_metadata"]["ok_count"], 0)
            self.assertEqual(report["run_metadata"]["failed_count"], 40)
            self.assertIn("DEEPSEEK_API_KEY", report["failures"][0]["error"])


if __name__ == "__main__":
    unittest.main()
