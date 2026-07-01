# AGENT.md

Operational contract for human-directed coding agents working in `AAAI-Fable`.

This file complements `CLAUDE.md`.

- `CLAUDE.md` defines behavior and engineering philosophy.
- `AGENT.md` defines execution workflow, scope boundaries, and deliverable
  standards.

Use both together.

## 1. Mission

Support the repository as a research engineering project centered on:

- Concept-to-Fable / Conceptual Fable Generation
- GraphRAG over curriculum or concept graphs
- dataset and benchmark construction
- evaluation protocol design
- paper reading and paper-writing support infrastructure

Agent work should improve one or more of these surfaces without weakening
traceability, reproducibility, or repo clarity.

## 2. Repo Map

Current high-level structure:

- `README.md`
  - repository overview and navigation
- `doc/`
  - paper framing, reading materials, dataset notes, evaluation notes, paper
    website
- `data/`
  - graph and experiment data assets
- `doc/paper-reading-site/`
  - Astro/Starlight site for paper reading and synthesis

Treat these areas as different products with different risk profiles.

## 3. Execution Workflow

For non-trivial tasks, follow this order.

### Step 1: Ground in the repo

- inspect the relevant subtree
- read nearby docs/configs before coding
- identify existing patterns to reuse

Minimum expectation:

- do not start writing code before understanding where the change belongs

### Step 2: Define the task boundary

Clarify internally:

- what is being changed
- what must not be changed
- what artifact should exist at the end
- how success will be checked

If ambiguity materially changes implementation, ask before proceeding.

### Step 3: Implement the smallest viable change

- choose the narrowest surface
- prefer local edits over broad architectural changes
- keep intermediate artifacts explicit

### Step 4: Verify

Verification should match the task:

- scripts: run on a sample
- graph retrieval: inspect sample node/subgraph output
- website: run/build and verify the affected route
- docs: verify paths, commands, and consistency

### Step 5: Report

Summarize:

- what changed
- what was verified
- what assumptions were made
- what remains unverified or deferred

## 4. Allowed Defaults

Unless the user asks otherwise, these defaults apply.

### Language and runtime

- Python for data, graph, and experiment tooling
- existing Node/Astro stack for the paper site

### Artifact formats

- JSON/JSONL for machine-readable data
- Markdown for human-readable instructions and design notes
- CSV only when tabular review/edit workflows clearly benefit

### Pipeline structure

Prefer stage-separated pipelines:

1. input acquisition
2. normalization/enrichment
3. retrieval/planning
4. generation/inference
5. evaluation/packing

Do not collapse all stages into one opaque script unless the task is trivial.

## 5. Project-Specific Guardrails

### A. Raw and released data

Do not:

- rewrite raw dataset files in place
- change graph IDs
- alter released schemas casually
- mix generated artifacts into source data folders without a clear boundary

Prefer:

- new derived directories
- explicit output prefixes
- schema docs when creating new artifact families

### B. Research docs

Do not:

- silently rewrite argumentation
- change paper problem definitions without updating nearby context
- turn planned work into implemented claims

Prefer:

- conservative phrasing
- explicit "current" vs "planned" distinctions
- localized edits to the relevant document

### C. Website

Do not:

- introduce unrelated design systems
- add runtime complexity unless required
- break existing content structure

Prefer:

- existing Astro/Starlight conventions
- incremental content/config/component edits

## 6. GraphRAG-Specific Rules

When working on graph retrieval or graph-grounded generation:

- treat existing graph assets as authoritative inputs
- preserve node and edge identities
- keep ingestion logic separate from retrieval logic
- keep retrieval logic separate from prompt/context packing
- define a stable output object for retrieved subgraphs

Preferred GraphRAG layering:

1. graph ingestion
2. node enrichment
3. query resolution
4. local subgraph expansion
5. context packaging
6. downstream reasoning/generation

Avoid:

- tightly coupling prompt text to raw graph storage format
- hiding retrieval policy inside large prompt templates
- rebuilding graphs from text when a structured graph already exists

## 7. Software Engineering Standards

All agent-produced code should satisfy these baseline standards:

- clear names
- small functions
- explicit I/O boundaries
- no speculative configuration
- no hidden side effects
- minimal dependency footprint
- deterministic behavior where practical
- failure modes that are obvious from logs or return values

For scripts:

- expose clear entrypoints
- accept explicit input/output locations where needed
- avoid hardcoding machine-specific absolute paths

For config:

- check in examples, not secrets
- document required environment variables

## 8. File Creation and Naming

When introducing new project code, prefer predictable names and structure.

Examples:

- `ingest_*.py` for import/enrichment scripts
- `retrieve_*.py` for retrievers
- `pack_*.py` for context assembly
- `evaluate_*.py` for metric or rubric pipelines
- `schemas/` or `specs/` for stable artifact definitions

Name things by role, not by vague experiment labels like:

- `final_v2.py`
- `new_pipeline.py`
- `temp_graph.py`

## 9. Testing and Validation Expectations

At minimum, validate one meaningful path through the changed area.

Examples:

- graph ingestion: confirm node and edge counts on a sample or whole import
- retrieval: query a known concept and inspect returned neighborhood
- website: load the changed route locally
- doc updates: verify commands and paths against the repo

If no formal tests exist, perform a targeted smoke check.

Do not claim "tested" if you only read the code.

## 10. Dependency Policy

Before adding a library:

- confirm the repo actually needs it
- prefer maintained, narrow-purpose libraries
- prefer official integrations for core infrastructure
- avoid pulling large frameworks into a prototype unless they clearly save real
  engineering time

For this repo in particular:

- GraphRAG libraries should be chosen based on compatibility with existing graph
  data, not trendiness
- dataset tooling should stay lightweight and auditable

## 11. Change Review Checklist

Before considering work complete, check:

- Is the change in the right subtree?
- Does it preserve raw data integrity?
- Does it match existing local patterns?
- Is every new file justified?
- Is the output format explicit?
- Is the verification appropriate and actually run?
- Are limitations clearly stated?

## 12. Deliverable Templates

Use these shapes mentally when executing tasks.

### Code task

- implementation
- narrow verification
- short summary

### Data pipeline task

- stage definition
- artifact definition
- sample run or sample output
- validation notes

### Documentation task

- updated Markdown
- consistent paths/commands/claims
- note of any still-planned items

### GraphRAG task

- graph input contract
- retriever behavior
- subgraph output contract
- sample retrieval validation

## 13. Anti-Patterns

Avoid these common agent failures:

- building a framework before a prototype exists
- changing research wording while implementing code
- treating generated outputs as source data
- adding abstractions with one caller
- editing many files to make a small change "cleaner"
- choosing a library because it is popular rather than because it matches the
  current data shape
- bundling retrieval, reasoning, and generation into one opaque function

## 14. Escalation Rule

Stop and ask before proceeding if any of the following are true:

- the task requires redefining the paper's problem formulation
- raw data would be overwritten or migrated
- multiple architecture choices have materially different consequences
- validation depends on unavailable external infrastructure
- a requested change conflicts with the repository's documented direction

## 15. Definition of a Good Agent Contribution

A good contribution in this repo is:

- correct
- minimal
- auditable
- reproducible
- consistent with the research direction
- easy for a human collaborator to pick up next
