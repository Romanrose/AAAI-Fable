"""第二部分 agent 流水线的端到端测试 (Mock LLM)。"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.m2na import M2NAPipeline, MockLLMClient
from src.m2na.fixtures import ALL_FIXTURES, overfitting, path_dependence
from src.m2na.types import M2NAInput, MechanismGraph, MechanismNode


@pytest.fixture
def pipeline() -> M2NAPipeline:
    return M2NAPipeline(MockLLMClient())


@pytest.mark.parametrize("concept", list(ALL_FIXTURES))
def test_pipeline_runs_end_to_end(pipeline: M2NAPipeline, concept: str) -> None:
    # Arrange
    inp = ALL_FIXTURES[concept]()

    # Act
    result = pipeline.run(inp)

    # Assert：四阶段产物都非空
    assert result.narrative.strip()
    assert result.plan.mappings
    assert result.alignment


def test_concealment_no_hard_leak(pipeline: M2NAPipeline) -> None:
    result = pipeline.run(path_dependence())
    assert result.report.hard_leaks == ()


def test_mechanism_fully_covered(pipeline: M2NAPipeline) -> None:
    # 对齐应覆盖机制图全部节点
    inp = overfitting()
    result = pipeline.run(inp)
    assert result.report.uncovered_elements == ()
    assert result.report.passed is True


def test_alignment_only_references_real_nodes(pipeline: M2NAPipeline) -> None:
    inp = path_dependence()
    result = pipeline.run(inp)
    valid_ids = set(inp.mechanism.node_ids())
    for pair in result.alignment:
        assert pair.concept_element in valid_ids


def test_uncovered_node_is_reported() -> None:
    # Arrange：给 path dependence 加一个 Mock 不会覆盖的节点
    base = path_dependence().mechanism
    extra = MechanismGraph(
        concept=base.concept,
        domain=base.domain,
        nodes=base.nodes + (MechanismNode("unmapped_extra", "an element with no carrier"),),
        edges=base.edges,
    )
    inp = M2NAInput(mechanism=extra, forbidden_terms=path_dependence().forbidden_terms)
    pipeline = M2NAPipeline(MockLLMClient())

    # Act
    result = pipeline.run(inp)

    # Assert：缺失节点被自检捕获
    assert "unmapped_extra" in result.report.uncovered_elements
    assert result.report.passed is False
