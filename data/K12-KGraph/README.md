# K12-KGraph

This repository contains the dataset release for the paper **"K12-KGraph: A Curriculum-Aligned Knowledge Graph for Benchmarking and Training Educational LLMs"**.

## Overview

K12-KGraph is a curriculum-aligned knowledge graph built from official People's Education Press (PEP) K-12 textbooks. It focuses on **curriculum cognition**, namely the structured understanding of how school knowledge is organized, connected, and sequenced.

The current release covers **mathematics, physics, chemistry, and biology** across **primary, middle, and high school**, and includes three resources derived from the same graph:

- **K12-KGraph**: the core knowledge graph
- **K12-Bench**: a graph-derived benchmark for evaluating curriculum understanding
- **K12-Train**: a KG-grounded instruction-tuning dataset
- **SFT-Baselines**: 2,300-sample evaluation subsets from 8 public instruction-tuning datasets for comparison with KG-grounded training

At the schema level, K12-KGraph contains **7 node types** (`Concept`, `Skill`, `Experiment`, `Exercise`, `Section`, `Chapter`, `Book`) and **9 relation types** (`is_a`, `prerequisites_for`, `relates_to`, `verifies`, `tests_concept`, `tests_skill`, `appears_in`, `is_part_of`, `leads_to`).

Current release summary:

- **K12-KGraph**: 10,685 nodes and 23,278 edges
- **K12-Bench**: 23,640 multi-select questions
- **K12-Train**: 2,267 question-answer pairs
- **SFT-Baselines**: 8 baseline subsets with 2,300 question-answer pairs each

## Repository Structure

```text
K12-KGraph/
|-- README.md
|-- K12-KGraph/
|   |-- global_KG/
|   |   |-- nodes.json
|   |   `-- edges.json
|   |-- subject_specific_KG/
|   |   |-- biology.json
|   |   |-- chemistry.json
|   |   |-- math.json
|   |   `-- physics.json
|   `-- afterclass_exercises/
|       `-- *.json
|-- K12-Bench/
|   |-- ground_subtask1.jsonl
|   |-- ground_subtask2.jsonl
|   |-- prereq_subtask1.jsonl
|   |-- prereq_subtask2.jsonl
|   |-- neighbor.jsonl
|   |-- evidence_subtask1.jsonl
|   |-- evidence_subtask2.jsonl
|   |-- locate_subtask1.jsonl
|   `-- locate_subtask2.jsonl
|-- SFT-Baselines/
|   |-- dataflow_2300/
|   |   `-- train.jsonl
|   |-- infinity_2300/
|   |   `-- train.jsonl
|   |-- lmsys_2300/
|   |   `-- train.jsonl
|   |-- openhermes_2300/
|   |   `-- train.jsonl
|   |-- smoltalk_2300/
|   |   `-- train.jsonl
|   |-- tulu3_2300/
|   |   `-- train.jsonl
|   |-- ultrachat_2300/
|   |   `-- train.jsonl
|   `-- wizardlm_2300/
|       `-- train.jsonl
`-- K12-Train/
    `-- train.jsonl
```

## Detailed Description

### 1. `K12-KGraph/`

This directory contains the core graph data.

- `global_KG/` stores the merged global graph as separate node and edge files.
- `subject_specific_KG/` stores subject-level graph files with richer node properties.
- `afterclass_exercises/` stores structured textbook exercise collections linked to relevant concepts and skills.

In general, the graph organizes curriculum content around concepts, skills, experiments, exercises, and textbook structure, while also encoding taxonomic, prerequisite, verification, assessment, and location relations.

### 2. `K12-Bench/`

This directory contains the benchmark for evaluating structural curriculum understanding. All files are in **JSONL** format, with one multi-select question per line.

K12-Bench includes five task families:

- **Ground**: linking exercises with the concepts or skills they assess
- **Prereq**: modeling prerequisite dependencies and direct successors
- **Neighbor**: identifying directly related concepts in the local graph neighborhood
- **Evidence**: connecting experiments with the concepts they verify
- **Locate**: locating where knowledge appears in the curriculum and how chapters are sequenced

### 3. `K12-Train/`

This directory contains the training set in **JSONL** format. Each line is one question-answer pair synthesized from graph node attributes or edge semantics.

K12-Train is designed for supervised fine-tuning of educational LLMs. The data is grounded in the curriculum structure captured by K12-KGraph rather than collected as a general-purpose instruction corpus.

### 4. `SFT-Baselines/`

This directory contains matched-budget comparison subsets from **8 public instruction-tuning corpora**. Each subdirectory provides a `train.jsonl` file with **2,300 sampled question-answer pairs**, following the protocol used in the paper: every baseline is uniformly down-sampled to approximately match the size of **K12-Train** (2,267 pairs).

These subsets are intended only as **reference training baselines** for the controlled SFT experiments in the paper. They are not derived from K12-KGraph, and they do not target curriculum cognition specifically.

Included baseline subsets:

- `dataflow_2300/`: subset from [**DataFlow-10K-Instruct**](https://huggingface.co/datasets/OpenDCAI/dataflow-instruct-10k), a multi-domain instruction dataset generated and filtered through the DataFlow framework, combining math, code, and general natural-language instruction data.
- `infinity_2300/`: subset from [**Infinity-Instruct**](https://huggingface.co/datasets/BAAI/Infinity-Instruct), a large-scale instruction dataset built through instruction selection and instruction evolution, including a foundational mixture of open-source instructions and a chat-oriented subset for real conversation scenarios.
- `lmsys_2300/`: subset from [**LMSYS Chat 1M**](https://huggingface.co/datasets/lmsys/lmsys-chat-1m), a large-scale real-world conversation dataset collected from the Vicuna demo and Chatbot Arena, containing chats between users and a wide range of frontier LLMs.
- `openhermes_2300/`: subset from [**OpenHermes-2.5**](https://huggingface.co/datasets/teknium/OpenHermes-2.5), a large-scale compilation of about 1M primarily synthetic instruction and chat samples, curated from many open-source and custom synthetic sources spanning general dialogue, coding, mathematics, science, medical, and reasoning data.
- `smoltalk_2300/`: subset from [**SmolTalk**](https://huggingface.co/datasets/HuggingFaceTB/smoltalk), a 1M-sample synthetic supervised fine-tuning dataset used for the SmolLM2-Instruct family, covering diverse tasks including text editing, rewriting, summarization, and reasoning.
- `tulu3_2300/`: subset from [**Tulu-3-SFT**](https://huggingface.co/datasets/allenai/tulu-3-sft-mixture), a large mixed instruction-tuning corpus combining math, coding, safety, multilingual, table, scientific, and open-ended assistant data from many constituent datasets.
- `ultrachat_2300/`: subset from [**UltraChat**](https://huggingface.co/datasets/openbmb/UltraChat), a large-scale multi-round dialogue dataset covering questions about the world, writing and creative tasks, and assistance on existing materials such as rewriting, continuation, summarization, and inference.
- `wizardlm_2300/`: subset from [**WizardLM Evol-Instruct V2 196K**](https://huggingface.co/datasets/WizardLMTeam/WizardLM_evol_instruct_V2_196k), the optimized Evol-Instruct training data used for WizardLM, based on evolved instruction data derived from Alpaca and ShareGPT.

## Notes

- The graph, benchmark, and training data are designed to be used together: the graph is the source resource, the benchmark evaluates curriculum cognition, and the training set provides graph-grounded supervision.
- The release is aligned with the PEP curriculum and should be understood in that scope.

---
license: cc-by-nc-sa-4.0
---
