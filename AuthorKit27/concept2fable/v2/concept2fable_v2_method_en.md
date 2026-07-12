# Concept2Fable v2 Method Section (English Draft)

## 3. Method

### 3.1 Problem Formulation and Overview

Directly prompting a language model with a curriculum concept often produces a fluent story with incomplete educational content. The generated story may mention related objects while omitting the conditions, processes, or outcomes that define the concept. It may also preserve topical similarity while reversing a causal relation. We therefore separate knowledge construction, analogical planning, and narrative realization.

Given a normalized K--12 knowledge graph $\mathcal{G}=(\mathcal{V},\mathcal{E})$, we select a target node $c\in\mathcal{V}$ whose label is `Concept`. Concept2Fable first constructs an evidence-grounded mechanism graph $M_c$ for $c$. It then uses an LLM-guided Copycat-inspired mapper to convert $M_c$ into a narrative mapping plan $A_c$, and finally realizes $A_c$ as an educational fable $y_c$.

The complete pipeline is:

\begin{equation}
 c \rightarrow S_c \rightarrow R_c \rightarrow M_c \rightarrow A_c \rightarrow y_c,
 \label{eq:pipeline}
\end{equation}

where $S_c$ is a minimal concept seed, $R_c$ is a bounded GraphRAG retrieval package, $M_c$ is a validated concept mechanism graph, and $A_c$ is a frozen analogy mapping plan. In contrast to direct concept-to-text generation, the narrative model receives a structured explanation of what must be preserved before it writes the fable.

### 3.2 Concept Node Initialization

We begin with Concept nodes rather than preconstructed concept cards. For each target node $c$, we build a seed

\begin{equation}
 S_c = (i_c, s_c, n_c, a_c, d_c, \tau_c, F_c),
 \label{eq:seed}
\end{equation}

where $i_c$ is the stable concept identifier, $s_c$ is the subject, $n_c$ is the canonical name, $a_c$ is the alias set, $d_c$ is the definition, $\tau_c$ is the concept type, and $F_c$ is the set of forbidden terms. The forbidden set is derived from the canonical name and aliases and is used to detect direct lexical leakage in the story body.

The seed is deliberately limited to target identification and basic lexical constraints. It does not store graph context, mechanism fields, story settings, or generation-quality scores. Retrieval evidence and mechanism information are created as separate artifacts. This separation allows the same Concept node to be evaluated under different retrieval or mapping configurations without rebuilding a mixed-purpose concept card.

### 3.3 Evidence-Grounded Concept Mechanism Graph

#### Controlled adaptive retrieval

The local neighborhood of a target node is not necessarily its explanatory mechanism. It may contain direct curriculum relations, broad topical associations, and instructional metadata. Expanding all neighboring nodes can therefore increase noise together with recall. Inspired by adaptive retrieval designs that distinguish useful evidence from partially relevant context (Xu et al. 2025), Concept2Fable uses a bounded adaptive two-hop retriever.

At the first hop, the retriever ranks target-centered edges using five core relations:

```text
prerequisites_for, is_a, verifies, leads_to, relates_to
```

Let $E_1(c)$ denote the ranked first-hop edges. We define a direct sufficiency function

\begin{equation}
 q(c,E_1) = \mathbb{I}[E_1\text{ provides an auditable mechanism structure}],
 \label{eq:sufficiency}
\end{equation}

where the decision depends on the target concept type, the number and diversity of valid relations, and whether the evidence can support a valid mechanism record. If $q(c,E_1)=1$, retrieval terminates at the first hop. Otherwise, the retriever expands only high-value first-hop nodes. The second hop prioritizes `prerequisites_for`, `is_a`, `verifies`, and `leads_to`, and retains only paths that contribute to an explanation of the target concept.

The default retrieval budget is eight paths, at most two hops per path, and twenty retained edges. For each target, the resulting package is

\begin{equation}
 R_c=(V_R,E_R,\Pi_R,\sigma_c),
 \label{eq:retrieval}
\end{equation}

where $V_R$ and $E_R$ are the retrieved nodes and edges, $\Pi_R$ is the selected path set, and $\sigma_c$ records the retrieval decision, including whether the second hop was triggered and why. If no core direct edge is available, the implementation permits a bounded curriculum bridge as a retrieval fallback. This fallback only produces evidence for the next stage; it does not convert a definition into a mechanism.

#### Mechanism extraction and validation

Given $S_c$ and $R_c$, the current implementation uses DeepSeek Chat to construct a typed mechanism graph

\begin{equation}
 M_c=(V_M,E_M,\epsilon_M,P_M),
 \label{eq:mechanism}
\end{equation}

where $V_M$ contains typed mechanism nodes, $E_M$ contains typed mechanism edges, $\epsilon_M$ maps each node or edge to evidence in $R_c$, and $P_M$ specifies the nodes and edges that must be preserved during mapping and generation.

The allowed node types are `entity`, `condition`, `process`, `state`, `outcome`, `rule`, and `evidence`. The allowed edge types are `requires`, `enables`, `transforms`, `causes`, `produces`, `constrains`, `is_a`, `part_of`, `relates_to`, and `verifies`. Each mechanism element must cite one of the following evidence forms:

```text
kg-node:<node-id>:<property>
kg-edge:<source-edge-id>
```

The validator checks identifier uniqueness, edge endpoints, relation enumerations, evidence resolvability, graph connectivity, and the validity of $P_M$. Process-like concepts, including processes, laws, mechanisms, methods, and theorems, must contain at least two nodes and one edge. Definition-like concepts may remain single-node graphs; the validator does not impose a causal chain where the source evidence does not support one. Invalid extraction is placed in a failure queue rather than repaired by copying the seed definition into a mechanism graph. Only records that pass validation and the latest human review decision are eligible for official story generation.

### 3.4 LLM-guided Copycat-inspired Mapping

Once $M_c$ has been approved, Concept2Fable does not ask the Generator to invent a story directly. Instead, an LLM-guided mapper produces a frozen mapping plan $A_c$. The mapper searches for a familiar source domain whose relational structure can carry the target mechanism. The mapping is defined over relations rather than word substitutions:

\begin{equation}
 A_c=(f_V,f_E,D,K,T),
 \label{eq:mapping}
\end{equation}

where $f_V:V_M\rightarrow V_S$ maps mechanism nodes to story carriers, $f_E:E_M\rightarrow E_S$ maps mechanism edges to story relations, $D$ contains direction-preservation constraints, $K$ contains narrative components, and $T$ contains lexical and generation constraints. A typical correspondence maps an entity to a character or object, a condition to an environmental constraint, a process to an event sequence, a state to a narrative state, and an outcome to a consequence. The direction of a causal edge constrains the order and dependency of the corresponding story events.

The mapper proposes source domains and candidate correspondences under the hard constraints $P_M$ and $F_c$. It then selects a plan using three criteria: preservation of required nodes and edges, narratability of the event chain, and suitability for explaining the target mechanism. The final plan records the source domain, node mappings, edge mappings, event chain, conflict, turning point, resolution state, direction flags, and input hashes.

For example, a mechanism for seed germination can state that suitable external conditions and the internal viability of the seed enable the germination process. A cooking domain can represent the external conditions with heat, water, and a covered pot, and the internal condition with the quality of the rice. The important correspondence is not the surface similarity between seeds and rice; it is the preservation of the two `enables` relations and their direction.

The term Copycat-inspired refers to the use of flexible relational mapping and controlled conceptual variation. It does not claim to reproduce the complete classical Copycat cognitive architecture. Surface carriers may change across candidates, but the approved mechanism elements and their required directions cannot be silently removed or reversed.

### 3.5 Fable Realization and Alignment-guided Revision

Given the frozen plan $A_c$, the Generator produces a Chinese educational fable $y_c$ under the lexical constraints in $F_c$. The fable should express the mechanism through characters, conditions, actions, and consequences rather than through a direct textbook explanation.

The generated story is then processed by three agents. The Aligner constructs a reverse alignment $L_c$ from mechanism nodes and edges to explicit story evidence and checks relation direction. The Judge evaluates conceptual faithfulness, mapping clarity, causal coherence, readability, implicitness, and pedagogical value, while flagging contradiction, missing mechanism elements, and terminology leakage. The Reviser receives the localized failure diagnosis and modifies the story accordingly. Mechanism omissions are repaired by adding the corresponding event, reversed relations by changing event order, leakage by rewriting the affected expression, and surface fluency problems by local editing.

The final output is

\begin{equation}
 O_c=(y_c,L_c,Q_c),
 \label{eq:output}
\end{equation}

where $Q_c$ is the generation and evaluation trace. All official candidates use the same Generator, Aligner, Judge, Reviser, candidate budget, token budget, and revision limit. Any Planner, Generator, Aligner, Judge, or Reviser fallback is marked `invalid_for_official_eval` and excluded from the official aggregate. This design follows the plan-then-realize principle established for automatic storytelling (Yao et al. 2019), while replacing a generic storyline with an evidence-grounded concept mechanism and an explicit analogical mapping plan.
