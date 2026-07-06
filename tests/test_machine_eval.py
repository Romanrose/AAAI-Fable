from __future__ import annotations

from pathlib import Path

from kg_rag.pipeline import machine_eval
from kg_rag.pipeline.machine_eval import MachineEvalOptions, run_machine_eval


def test_run_machine_eval_uses_agentic_graphrag_defaults(tmp_path: Path, monkeypatch) -> None:
    normalized_graph_path = tmp_path / "normalized.json"
    captured = {}

    def fake_normalize_k12_graph(**kwargs):
        normalized_graph_path.write_text("{}", encoding="utf-8")
        return {}

    def fake_select_concept_nodes(**kwargs):
        return {"concept_count": 1}

    def fake_build_concept_cards(**kwargs):
        return {"concept_card_count": 1}

    def fake_enrich_concept_cards(**kwargs):
        return {"card_count": 1, "enriched_count": 1}

    def fake_auto_concept_run_dir(**kwargs):
        return tmp_path / "runs" / "smoke"

    def fake_run_concept_fable_batch(**kwargs):
        captured.update(kwargs)
        return {"failed_count": 0}

    def fake_verify_eval_run(run_dir, expected_count):
        return {"ok": True, "run_dir": str(run_dir), "expected_count": expected_count}

    monkeypatch.setattr(machine_eval, "normalize_k12_graph", fake_normalize_k12_graph)
    monkeypatch.setattr(machine_eval, "select_concept_nodes", fake_select_concept_nodes)
    monkeypatch.setattr(machine_eval, "build_concept_cards", fake_build_concept_cards)
    monkeypatch.setattr(machine_eval, "enrich_concept_cards", fake_enrich_concept_cards)
    monkeypatch.setattr(machine_eval, "auto_concept_run_dir", fake_auto_concept_run_dir)
    monkeypatch.setattr(machine_eval, "run_concept_fable_batch", fake_run_concept_fable_batch)
    monkeypatch.setattr(machine_eval, "verify_eval_run", fake_verify_eval_run)

    result = run_machine_eval(
        output_root=tmp_path / "derived",
        normalized_graph_path=normalized_graph_path,
        concept_runs_root=tmp_path / "runs",
        options=MachineEvalOptions(
            subjects="biology",
            limit=1,
            limit_per_subject=1,
            mode="local",
            evaluate_mode="rules",
            language="zh-CN",
            no_normalize=False,
            no_resume=True,
        ),
    )

    options = captured["options"]
    assert result["ok"] is True
    assert captured["normalized_graph_path"] == normalized_graph_path
    assert options.workflow == "agentic"
    assert options.retrieval_mode == "dual_level"
    assert options.max_edges == 16
    assert options.revision_rounds == 0
    assert options.template_blacklist == "default"
