# CLAUDE.md

Project-level behavioral and engineering guidelines for coding agents working in `AAAI-Fable`.

This file is inspired by the simplicity and execution discipline of the
`andrej-karpathy-skills` project, but is adapted for this repository's actual
shape: a research engineering workspace that combines paper writing materials,
dataset assets, GraphRAG experiments, and a paper-reading website.

These rules are intended to reduce common agent failures:

- silently making wrong assumptions
- overengineering early research prototypes
- mutating data or docs without a clear reason
- performing broad edits that weaken experimental traceability
- treating a research repo like a generic app repo

Tradeoff: these guidelines bias toward rigor, reproducibility, and minimal
surface area over speed. For trivial edits, use judgment.

## 1. Think Before Changing Anything

Do not guess about repo intent when the structure or docs can answer it.

Before implementing:

- Read the relevant local docs first.
- State assumptions explicitly when the repo does not settle them.
- If there are multiple plausible interpretations, surface them instead of
  silently picking one.
- If the requested approach is heavier than necessary, propose the simpler path.
- If something is genuinely unclear, stop and ask.

For this repo specifically:

- Treat `README.md` and `doc/` as the primary source of truth for research
  intent.
- Treat `data/` as the source of truth for experiment inputs and released
  artifacts.
- Distinguish clearly between:
  - research direction
  - experiment infrastructure
  - website/documentation
  - model/data pipeline implementation

## 2. Simplicity First

Build the minimum thing that moves the project forward.

Do not:

- add speculative abstractions
- introduce services, queues, or frameworks before a local CLI/script version
  exists
- create configuration surfaces for hypothetical future use
- add data schemas that are broader than current experimental needs
- build a general "AI platform" when the repo needs a concrete prototype

Prefer:

- simple Python scripts for data and graph workflows
- JSON/JSONL artifacts with explicit fields
- thin wrappers around external libraries
- direct, readable code over clever indirection
- one clear path over multiple modes unless the repo already needs them

Heuristic:

- if 300 lines can be 80, rewrite it
- if an abstraction is used once, inline it unless it obviously reduces risk
- if a dependency only saves a few lines but adds operational burden, do not add
  it

## 3. Surgical Changes

Touch only what the task requires.

When editing:

- do not refactor unrelated files
- do not rename repo concepts casually
- do not rewrite research prose unless the task is about prose
- do not "clean up" docs, comments, formatting, or data that are orthogonal to
  the task
- match the local style of the touched area

If your change creates local cleanup work:

- remove imports, helpers, or config introduced by your change if they become
  unused
- do not remove pre-existing dead code or unused material unless explicitly
  asked

Every changed line should trace back to one of:

- the user's current request
- required integration glue
- required verification
- required documentation of the new behavior

## 4. Goal-Driven Execution

Translate requests into verifiable outcomes.

Examples:

- "Add GraphRAG support" becomes:
  - ingest graph data
  - retrieve a local concept subgraph
  - package retrieval context
  - verify the output shape on a known concept
- "Build a data pipeline" becomes:
  - define artifact schemas
  - implement stage boundaries
  - produce one end-to-end pilot run
  - verify outputs at each stage
- "Improve the paper site" becomes:
  - implement the page change
  - run the site locally
  - verify the affected route visually

For non-trivial work, think in:

1. step
2. expected artifact
3. verification check

Do not stop at "implemented". Stop at "verified".

## 5. Repo-Specific Priorities

This repository has three distinct surfaces. Treat them differently.

### A. `doc/` Research and writing assets

Includes:

- paper framing
- dataset design notes
- evaluation design
- literature survey
- paper-reading website

Rules:

- preserve authorial intent
- avoid bulk rewriting prose unless asked
- if updating terminology, do it consistently and only where necessary
- keep research claims traceable to source materials

### B. `data/` Released or source experiment assets

Includes:

- `data/K12-KGraph/`
- future GraphRAG or benchmark artifacts

Rules:

- do not mutate raw dataset files casually
- never overwrite released assets without explicit user intent
- generated outputs should go to a clearly separate location such as
  `interim/`, `processed/`, `derived/`, or another task-specific directory
- preserve schema stability once artifacts are consumed by scripts or docs
- document any new derived artifact format

### C. `doc/paper-reading-site/` Web app

Rules:

- follow the existing Astro/Starlight structure
- prefer local content/config changes over new framework layers
- keep UX clean and utilitarian
- run local verification for changed routes when feasible

## 6. Preferred Engineering Patterns for This Repo

Use these defaults unless the task clearly needs otherwise.

### For data and experiment code

- Python first
- CLI/script entrypoints first
- JSON/JSONL for artifacts
- explicit schema fields
- deterministic output ordering when practical
- clear separation between raw, derived, and evaluation artifacts

### For graph workflows

- preserve original node/edge IDs
- enrich existing graph data rather than duplicating it
- keep retrieval packaging separate from graph storage
- prefer "existing graph + retriever" over "rebuild the graph" when graph data
  already exists
- keep GraphRAG modular:
  - ingestion
  - enrichment
  - retrieval
  - context packing
  - downstream generation

### For website work

- preserve existing content collection patterns
- do not add unnecessary state management or client-side complexity
- prefer static-first behavior unless dynamic interaction is required

## 7. Reproducibility and Experiment Discipline

Research engineering is not complete without traceability.

When implementing pipelines or experiments:

- separate source data from derived outputs
- record input paths, model names, and key parameters
- prefer idempotent stages
- make reruns safe
- avoid hidden manual steps
- document required environment variables and external services

If a script produces artifacts, it should be clear:

- what it reads
- what it writes
- whether rerunning is safe
- how success is validated

## 8. Dependency and Integration Rules

Before adding a dependency:

- prefer the standard library or current repo stack if enough
- prefer a thin, well-scoped dependency over a large framework
- prefer official or well-maintained libraries for graph/database integration
- justify any dependency that introduces operational setup

For this repo:

- if GraphRAG is needed on top of `K12-KGraph`, prefer integrating a library
  around the existing graph rather than rebuilding the entire system from a
  heavyweight framework
- if a third-party library is used, keep project code independent from that
  library's internal layout where possible

## 9. Editing Data, Docs, and Research Claims

Be stricter than usual.

- Do not invent dataset statistics.
- Do not invent benchmark claims.
- Do not silently change terminology that affects the paper's problem
  formulation.
- Do not change evaluation dimensions without updating surrounding docs.
- Do not "normalize" Chinese/English terminology across the repo unless that is
  the task.

When updating claims:

- prefer citing the local source document
- keep wording conservative
- distinguish implemented behavior from planned behavior

## 10. Validation Standards

Validate according to the surface you changed.

### Code / scripts

- run the narrowest meaningful check
- for pipeline stages, validate output shape and a small sample
- for graph retrieval, test on at least one known concept/node

### Website

- run the dev/build command when practical
- verify the specific affected page or component

### Docs

- verify links, paths, and commands
- ensure changed instructions match actual repo layout

If you could not validate something, say so explicitly.

## 11. Communication Rules for Agents

When working in this repo:

- be direct
- name assumptions
- name constraints
- say what you verified
- say what you did not verify

Do not:

- overclaim completeness
- bury key tradeoffs
- present speculative architecture as if already implemented

## 12. Definition of Done

A task is done only when all of the following are true:

- the requested change is implemented or the requested artifact is produced
- the change is scoped and minimal
- relevant local docs or paths remain consistent
- the result is verified at an appropriate level
- any limitations or unverified parts are stated explicitly

## 13. Quick Start for Future Agents

Start here before non-trivial work:

1. Read `README.md`.
2. Inspect the relevant subtree:
   - `doc/` for research intent
   - `data/` for datasets and graph assets
   - `doc/paper-reading-site/` for the site
3. Find the smallest implementation surface that satisfies the request.
4. Prefer additive, reversible changes.
5. Verify only what matters, but do verify it.
