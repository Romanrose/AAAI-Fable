# ConceptFableBench: Method and Experimental Design

## Abstract

We introduce **ConceptFableBench**, a benchmark for converting curriculum concepts into short educational fables that hide the target terminology while preserving the underlying conceptual mechanism. The benchmark is built from **6,574 Concept nodes** in a K--12 knowledge graph covering biology, chemistry, mathematics, and physics. Each instance contains a target concept, a cleaned concept card, a graph-retrieved conceptual context, a mechanism-oriented representation, a narrative plan, a generated fable, and an explicit alignment between conceptual mechanisms and narrative elements.

The paper contributes three artifacts:

1. **A concept-to-fable dataset** built from K--12 curriculum concept nodes.
2. **A graph-grounded data generation method** for producing concealed but mechanism-faithful educational fables.
3. **An evaluation benchmark** combining six-dimensional pedagogical quality judgments with structural M2NA alignment metrics.

The method follows the planning-oriented tradition of controllable story generation and plan-and-write systems, while adapting graph-constrained generation ideas to educational analogy. The experimental design compares direct prompting, card-only generation, graph retrieval variants, mechanism planning, analogy planning, and revision-based full generation under automatic, human, and stress-test evaluation protocols.

---

## 1. Method

### 1.1 Task Formulation

We study **Mechanism-to-Narrative Analogy Generation** (**M2NA**), a graph-grounded version of educational fable generation.

Given a target curriculum concept `c`, the system receives:

- `D_c`: the concept definition or textbook explanation;
- `G_c = (V_c, E_c)`: a concept-centered graph context or mechanism graph;
- `T_c`: a forbidden term set containing the concept name, aliases, and high-leakage terminology.

The goal is to generate:

- `N`: a short narrative or fable;
- `A`: an alignment between conceptual mechanism elements and narrative elements.

The generated story should satisfy three constraints:

1. **Lexical concealment**: the story body should not directly reveal terms in `T_c`.
2. **Mechanism preservation**: the characters, objects, events, and causal chain should preserve the mechanism encoded by `G_c`.
3. **Auditable alignment**: the system should provide an explicit alignment `A` connecting conceptual elements to narrative elements.

Formally, each benchmark example is represented as:

```text
x_c = {c, D_c, G_c, T_c, P_c, N_c, A_c, E_c}
```

where:

- `P_c` is the narrative plan;
- `N_c` is the generated fable;
- `A_c` is the mechanism-to-narrative alignment;
- `E_c` is the evaluation record.

This task differs from ordinary story generation in three ways:

1. The output is not only a fluent narrative but also an instructional analogy.
2. The target concept should be inferable from structure rather than named in the text.
3. The output must be auditable through explicit mechanism-to-story alignment.

---

### 1.2 Benchmark Construction

The dataset is derived from a K--12 knowledge graph with:

| Node / Edge Type | Count |
|---|---:|
| Total nodes | 10,685 |
| Total edges | 23,278 |
| Concept nodes | 6,574 |
| Book nodes | 48 |
| Chapter nodes | 264 |
| Exercise nodes | 1,174 |
| Experiment nodes | 652 |
| Section nodes | 609 |
| Skill nodes | 1,364 |

We focus on the **6,574 nodes labeled `Concept`**. Non-Concept nodes such as chapters, sections, exercises, skills, books, and experiments are retained only as retrieval context.

The first release covers four subjects:

| Subject | Concept Nodes |
|---|---:|
| Chemistry | 2,302 |
| Biology | 1,648 |
| Mathematics | 1,470 |
| Physics | 1,154 |
| **Total** | **6,574** |

For each Concept node, we construct a **concept card**. A concept card contains:

- stable concept identifier;
- subject;
- canonical name;
- definition;
- aliases;
- examples;
- teaching level;
- concept type;
- graph neighborhood summary;
- mechanism notes;
- misconceptions;
- subject-specific constraints;
- forbidden terms.

Each example is classified into one of four priority levels:

| Priority | Definition | Use |
|---|---|---|
| `gold` | Readable name, usable definition, and rich graph context | Main generation set |
| `silver` | Usable text but weaker context | Main or extended set after enrichment |
| `bronze` | Short definition or weak mechanism structure | Conservative generation |
| `repair` | Missing or corrupted text | Excluded unless repaired |

The benchmark supports three use cases:

1. A **dataset** of concept-to-fable instances for model development.
2. A **data generation protocol** for producing aligned educational fables at scale.
3. An **evaluation benchmark** for measuring conceptual faithfulness, concealment, alignment quality, pedagogical usefulness, and structural consistency.

---

### 1.3 Graph-Grounded Data Generation

The generation pipeline follows a staged **plan-and-generate** design inspired by controllable story generation and plan-and-write systems, but replaces free-form story planning with a graph-grounded mechanism planning step.

The high-level workflow is:

```text
Concept Card
-> Dual-Level GraphRAG
-> Mechanism Plan
-> Analogy Plan
-> Fable Writer
-> Alignment Builder
-> Evaluation and Revision
```

This design follows three intuitions:

1. Story generation should be grounded in retrieved graph evidence.
2. Narrative planning should operate over mechanisms rather than keywords.
3. Evaluation should inspect both the surface story and the structural alignment.

---

### 1.4 Concept Selection and Cleaning

We first normalize the K--12 graph and select nodes whose label is `Concept`.

Text fields are cleaned without modifying raw graph files. Definitions, aliases, and examples are extracted from node properties when available. Nodes with missing or suspicious text are marked for enrichment; unrecoverable text is placed in a repair queue rather than silently treated as clean input.

The output of this stage is a Concept selection file:

```json
{
  "concept_id": "biology_7a_rjb_cpt1",
  "subject": "biology",
  "name": "biology concept name",
  "definition": "textbook definition",
  "degree": 12,
  "edge_types": ["appears_in", "is_a", "prerequisites_for"],
  "has_definition": true,
  "text_quality": "good",
  "context_quality": "high",
  "generation_priority": "gold",
  "recommended_action": "generate",
  "story_language": "zh-CN"
}
```

---

### 1.5 Concept Card Construction

The concept card is the canonical input for all downstream generation, evaluation, and rewriting stages.

Example schema:

```json
{
  "concept_id": "biology_7a_rjb_cpt1",
  "subject": "biology",
  "story_language": "zh-CN",
  "canonical_name": "target concept",
  "definition": "concept definition",
  "aliases": ["alias 1", "alias 2"],
  "examples": ["example 1", "example 2"],
  "teaching_level": "middle_school",
  "concept_type": "definition",
  "graph_context": {
    "prerequisites": [],
    "related_concepts": [],
    "outcomes": [],
    "experiments": [],
    "exercises": [],
    "hierarchy": []
  },
  "core_mechanism_zh": [],
  "must_preserve_zh": [],
  "common_misconceptions_zh": [],
  "forbidden_terms_zh": ["target concept", "alias"],
  "subject_constraints_zh": [],
  "generation_notes_zh": [],
  "data_quality": {
    "text_quality": "good",
    "context_quality": "high",
    "needs_llm_enrichment": false,
    "generation_priority": "gold"
  }
}
```

The two most important fields are:

- `must_preserve_zh`: mechanism constraints that must survive in the story;
- `forbidden_terms_zh`: terms that must not appear in the story body.

This means the model is not asked to explain the concept directly. Instead, it must preserve the mechanism while hiding the terminology.

---

### 1.6 Dual-Level GraphRAG Retrieval

For each target concept, a retriever collects local graph evidence while preserving node and edge identifiers.

The retrieval package contains two levels:

1. **Raw KG evidence**: original graph edges and neighboring nodes for traceability.
2. **High-level topic summary**: compact context organized around conditions, processes, effects, prerequisites, related concepts, hierarchy, exercises, and experiments.

This stage produces:

```text
retrieval_package.json
subgraph_pack.json
```

The goal is to expose both symbolic graph evidence and compact reasoning context. The graph context prevents the system from inventing a mechanism unsupported by the curriculum graph.

---

### 1.7 Mechanism Planning

The mechanism planner converts the concept card and graph retrieval package into a mechanism-oriented representation.

The mechanism plan records:

- core mechanism;
- necessary conditions;
- input-output relations;
- causal direction;
- likely misconceptions;
- subject-specific constraints;
- elements that must be preserved in the story.

Subject-specific planning differs across domains:

| Subject | Mechanism Focus |
|---|---|
| Biology | Life processes, environmental conditions, feedback, inheritance, ecological relations |
| Chemistry | Particle rearrangement, conservation, reaction states, macro-micro links |
| Physics | Variable relations, magnitude, direction, conservation, boundary conditions |
| Mathematics | Definitions, operations, constraints, premise-to-conclusion structure |

This stage answers:

```text
What conceptual structure must the story preserve?
```

---

### 1.8 Analogy Planning

The analogy planner maps conceptual roles to a narrative source domain.

Instead of asking a model to invent a story from scratch, the planner chooses:

- source domain;
- setting;
- entities;
- conflict;
- turning point;
- event chain;
- resolution state;
- alignment plan.

Recommended source domains are subject-aware:

| Subject | Candidate Source Domains |
|---|---|
| Biology | Gardens, workshops, ports, theaters, markets |
| Chemistry | Ledgers, warehouses, exchanges, foundries, city gates |
| Physics | Waterways, traffic systems, scales, fleets, slides |
| Mathematics | Rule games, maps, courts, puzzles, ordered cities |

This stage is intended to prevent decorative stories that have characters but no recoverable mechanism mapping.

---

### 1.9 Fable Writing and Alignment

The fable writer receives the concept card and structure plan and generates a Chinese fable.

The story body must:

- use `zh-CN` as the main language;
- avoid the target concept name and forbidden terms;
- express the mechanism through plot, conflict, and resolution;
- avoid textbook-style explanation;
- avoid merely moralizing the concept;
- support later recovery of the conceptual structure.

The system also records an alignment table connecting:

```text
concept role
mechanism element
story element
textual evidence
```

In M2NA notation:

```text
N = concealed narrative
A = mechanism-to-narrative alignment
```

---

### 1.10 Evaluation-Guided Revision

Generated stories are evaluated immediately.

Samples marked `revise` or `reject` can enter a revision loop:

| Failure Type | Repair Strategy |
|---|---|
| Hard leakage | Rewrite story body and remove concept names or aliases |
| Low mapping clarity | Repair analogy plan or alignment plan |
| Low faithfulness | Repair mechanism plan or expand graph context |
| Low pedagogical value | Strengthen causal chain and transfer cues |
| Low novelty | Change source domain while preserving the mechanism |
| Low readability | Rewrite surface narrative while preserving alignment |

The system keeps previous versions:

```text
draft_story.v1.txt
six_dim_eval.v1.json
draft_story.v2.txt
six_dim_eval.v2.json
```

---

### 1.11 Generation Algorithm

```text
Algorithm: Graph-Grounded Concept-to-Fable Generation

Input:
  normalized graph G
  concept node c
  language l

Output:
  fable N
  alignment A
  evaluation record E

1. Build concept card C_c from c and graph properties.
2. Construct forbidden terms T_c from names, aliases, and high-leakage terms.
3. Retrieve graph package R_c with dual-level GraphRAG.
4. Infer mechanism plan M_c from (C_c, R_c).
5. Construct analogy plan P_c from (C_c, M_c).
6. Generate fable N under lexical concealment constraints.
7. Extract or generate alignment A between M_c and N.
8. Evaluate (C_c, R_c, M_c, P_c, N, A).
9. If status is revise or reject:
     repair the failed stage and regenerate N.
10. Return N, A, E.
```

---

### 1.12 Contribution as Dataset, Generator, and Benchmark

ConceptFableBench is intended to follow a benchmark-oriented contribution style in which the contribution is not a single model but a full task resource:

1. **Dataset**: curriculum concept instances with graph context, concept cards, forbidden terms, generated fables, alignments, and evaluation records.
2. **Generator**: a reproducible graph-grounded pipeline that turns concept evidence into concealed educational narratives.
3. **Benchmark**: automatic, LLM-judge, structural, stress-test, and human evaluation protocols.

This organization makes the resource useful even when the generator changes. Future systems can use the same concept cards and graph contexts, produce new fables and alignments, and evaluate them under the same benchmark metrics.

---

## 2. Experimental Design

### 2.1 Research Questions

The experiments are designed to answer five questions:

1. Does graph-grounded mechanism planning improve conceptual faithfulness over direct prompting?
2. Does explicit analogy planning improve mapping clarity and pedagogical usefulness?
3. Can a system maintain high lexical concealment without sacrificing teaching value?
4. Do structural M2NA metrics capture failures that six-dimensional story scoring misses?
5. Does evaluation-guided revision increase the proportion of acceptable fables?

---

### 2.2 Evaluation Sets

We use three evaluation scales:

| Set | Size | Purpose |
|---|---:|---|
| Pilot Set | 50 concepts per subject, 200 total | Prompt debugging, failure taxonomy, metric calibration |
| Main Evaluation Set | 200 concepts per subject, 800 total | Main method comparison |
| Full Generation Set | 6,574 concepts | Coverage, scalability, cost, failure-rate analysis |

The main evaluation set is stratified by:

- subject;
- priority level;
- concept type;
- graph context richness.

Repair examples are excluded from the main set unless they are enriched and pass text-quality checks.

---

### 2.3 Systems and Ablations

We compare the full method against direct prompting and component ablations.

All systems use the same generator model, language, decoding settings, and target story length unless otherwise specified.

| ID | System | Description |
|---|---|---|
| B1 | Direct Prompt | Provide only the concept name and definition; ask the model to write a fable |
| B2 | Card Only | Use the cleaned concept card and forbidden terms, without graph retrieval |
| B3 | One-Hop GraphRAG | Use a one-hop concept subgraph without dual-level topic summaries |
| B4 | Dual-Level GraphRAG | Use dual-level retrieval, but no explicit mechanism planner |
| B5 | Mechanism Only | Use a mechanism plan, but no explicit analogy/source-domain planning |
| B6 | Full Graph-M2NA | Use concept card, dual-level GraphRAG, mechanism plan, analogy plan, alignment, and revision |
| B7 | Full w/o Forbidden Terms | Remove lexical concealment constraints from the full system |
| B8 | Full w/o Revision | Disable evaluation-guided rewriting |

Each component has a measurable target:

| Component | Expected Benefit | Primary Metrics |
|---|---|---|
| GraphRAG | Better grounding | Node coverage, edge coverage, faithfulness |
| Mechanism Plan | Better conceptual structure | Direction accuracy, faithfulness |
| Analogy Plan | Better story-concept mapping | Mapping clarity, pedagogical value |
| Forbidden Terms | Less leakage | Exact leakage, soft leakage, implicitness |
| Revision | Higher final quality | Accept rate, weighted score |

---

### 2.4 Automatic Six-Dimensional Evaluation

Each generated fable is evaluated on six dimensions using a 1--5 Likert scale:

| Dimension | Question |
|---|---|
| Faithfulness | Does the fable accurately express the target concept? |
| Implicitness | Does the fable avoid directly revealing the concept name or terminology? |
| Mapping Clarity | Can story elements be mapped back to conceptual mechanisms? |
| Readability | Is the story natural, coherent, and easy to read? |
| Pedagogical Value | Does the story help readers understand the concept? |
| Novelty | Does the story avoid template-like or cliched patterns? |

The weighted score is:

```text
S =
0.25 * Faithfulness
+ 0.15 * Implicitness
+ 0.20 * Mapping Clarity
+ 0.10 * Readability
+ 0.20 * Pedagogical Value
+ 0.10 * Novelty
```

Decision rules:

| Status | Rule |
|---|---|
| `accept` | Faithfulness, implicitness, mapping clarity, and pedagogical value >= 4; readability and novelty >= 3; no hard failure |
| `revise` | No hard failure, but not enough for accept |
| `reject` | Faithfulness <= 2, mapping clarity <= 2, hard leakage, concept contradiction, or unmapped core mechanism |

When multiple LLM judges are used:

- scores are aggregated by median per dimension;
- hard flags are aggregated by majority vote;
- rationales and revision suggestions are merged.

---

### 2.5 Structural M2NA Metrics

Six-dimensional scoring captures human-facing story quality, but it is insufficient for verifying mechanism preservation.

We therefore add structural metrics over the generated alignment:

| Metric | Meaning |
|---|---|
| Exact concept leakage | Whether the story body contains the concept name or aliases |
| Soft term leakage | Whether the story contains high-leakage terminology |
| Node coverage | Proportion of mechanism nodes aligned to story evidence |
| Edge coverage | Proportion of mechanism edges aligned to story evidence |
| Alignment precision | Proportion of alignments with valid IDs and evidence that appears in the narrative |
| Hallucination rate | Proportion of alignments with invalid IDs or unsupported evidence |
| Direction accuracy | Whether narrative source and target roles preserve the direction of conceptual relations |
| Template hit rate | Rate of common formulaic story patterns |
| Narrative length | Character count or token length of the story |

These metrics allow the benchmark to distinguish a fluent story from a structurally faithful analogy.

---

### 2.6 Human Evaluation

Human evaluation is conducted on a stratified subset of the main evaluation set.

Recommended setup:

```text
40 concepts per subject
4 subjects
3 systems per concept:
  - Direct Prompt
  - One-Hop GraphRAG
  - Full Graph-M2NA
at least 3 annotators per story
```

The protocol has two stages.

#### Stage 1: Story-Only Evaluation

Annotators see only the fable body and rate:

- implicitness;
- readability;
- novelty.

This avoids contaminating implicitness judgments with the target concept name.

#### Stage 2: Concept-Aware Evaluation

Annotators then see:

- target concept;
- definition;
- mechanism graph;
- alignment table.

They rate:

- faithfulness;
- mapping clarity;
- pedagogical usefulness.

#### Learning Questions

We also include two lightweight learning questions:

1. What mechanism does the story seem to describe?
2. After the concept is revealed, which story elements correspond to which conceptual elements?

Reported human metrics:

- mean human scores;
- inter-annotator agreement;
- concept-guessing accuracy;
- alignment-recovery accuracy;
- Spearman correlation between human scores and automatic judge scores.

---

### 2.7 Stress Tests

To test whether the evaluation benchmark detects known failures, we construct adversarial variants of clean examples.

| Stress Type | Construction | Expected Detection |
|---|---|---|
| Surface Distractor | Preserve topical similarity but remove structural mapping | Mapping failure |
| Relation Corruption | Reverse a mechanism edge while keeping surface evidence | Direction error |
| Mechanism Omission | Remove a key mechanism node and relation evidence | Low coverage |

Reported metrics:

- detection rate for each stress type;
- false-positive rate on clean samples.

---

### 2.8 Main Results to Report

The main results table should compare all systems on six-dimensional quality, structural metrics, and accept rate.

Recommended table columns:

```text
Method
Faithfulness
Implicitness
Mapping Clarity
Readability
Pedagogical Value
Novelty
Weighted Overall
Accept %
Hard Leakage %
Node Coverage
Edge Coverage
Direction Accuracy
```

Subject-level analysis should report results for:

- biology;
- chemistry;
- mathematics;
- physics.

Expected trends:

| Subject | Expected Challenge |
|---|---|
| Biology | Process and system concepts may benefit strongly from analogy |
| Chemistry | Conservation and macro-micro mapping may expose hallucination errors |
| Physics | Direction, magnitude, and variable relations require careful planning |
| Mathematics | Formal constraints may be lost if the story becomes purely moral |

---

### 2.9 Full-Scale Generation Study

After the main comparison, the full method is run on all **6,574 Concept nodes**.

The goal is not to manually judge every story, but to measure dataset-scale feasibility.

Reported metrics:

- generation success rate;
- evaluation success rate;
- average weighted score;
- accept / revise / reject ratio;
- hard leakage rate;
- alignment failure rate;
- average token cost;
- average latency;
- subject-level failure distribution.

This full-scale run forms the first release of ConceptFableBench.

---

### 2.10 Case Studies and Failure Analysis

The paper should include three qualitative cases:

1. **Successful fable**: clear mechanism preservation and strong concealment.
2. **Fluent but weak fable**: readable story but poor structural mapping.
3. **Revised fable**: a story that improves after leakage removal or mapping repair.

Failure categories:

- direct concept leakage;
- soft-term leakage;
- reversed causality;
- missing mechanism;
- unsupported mapping evidence;
- template story;
- misleading pedagogical analogy;
- subject-specific misconception.

---

### 2.11 Statistical Testing

For paired method comparisons, each concept is treated as a unit.

Recommended tests:

- paired bootstrap resampling;
- Wilcoxon signed-rank test;
- effect size reporting where space permits.

Main comparisons:

- Full Graph-M2NA vs Direct Prompt;
- Full Graph-M2NA vs Card Only;
- Full Graph-M2NA vs One-Hop GraphRAG;
- Full Graph-M2NA vs Full w/o Revision.

Primary endpoints:

- weighted score;
- mapping clarity;
- pedagogical usefulness;
- node coverage;
- edge coverage;
- accept rate.

---

### 2.12 Limitations and Ethics

The benchmark currently focuses on Chinese fables generated from K--12 Concept nodes. Non-Concept nodes are used as graph context but are not story-generation targets.

Some concepts are definitional or highly formal, especially in mathematics, and may require shorter or more conservative narrative forms.

Automatic LLM-as-judge evaluation must be calibrated against human annotations and should not be treated as a replacement for expert review.

The system is intended to assist educational content creation, not to replace teachers or textbooks. Generated stories may simplify or distort scientific concepts, so accepted outputs should still be reviewed before classroom use.

The benchmark explicitly tracks:

- leakage;
- misconception;
- misleading analogy;
- mapping failure;
- unsupported evidence.

This reduces the chance of presenting fluent but conceptually incorrect narratives as learning material.

---

## References to Emulate

The writing and experimental design are intended to emulate the structure of the following works:

- arXiv:2410.16803  
  <https://arxiv.org/abs/2410.16803>

- arXiv:1808.10113  
  <https://arxiv.org/abs/1808.10113>

- arXiv:1811.05701  
  <https://arxiv.org/abs/1811.05701>

- arXiv:2504.20605  
  <https://arxiv.org/abs/2504.20605>

In particular, this draft borrows the high-level organization of:

```text
formal task definition
dataset construction
generation pipeline
baseline and ablation design
automatic metrics
human evaluation
stress tests
full-scale benchmark release
```

