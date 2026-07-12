#!/usr/bin/env node
/**
 * Build compact browser data for a concept-centric K12 knowledge graph.
 *
 * This visualization keeps all original K12-KGraph node/edge types so the
 * relation legend matches the dataset schema exactly. Concept nodes are the
 * primary visual layer; books, chapters, sections, skills, experiments, and
 * exercises remain as context nodes for location, assessment, and evidence
 * relations.
 */

import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SOURCE = resolve(HERE, '..', '..', 'derived', 'kg_rag', 'k12_kgraph_normalized.json');
const OUT = resolve(HERE, 'graphdata.js');

const raw = JSON.parse(readFileSync(SOURCE, 'utf8'));

const SUBJECTS = ['math', 'physics', 'chemistry', 'biology'];
const SUBJECT_NAMES = {
  math: '数学',
  physics: '物理',
  chemistry: '化学',
  biology: '生物学',
};
const SUBJECT_COLORS = {
  math: '#2563EB',
  physics: '#E11D48',
  chemistry: '#D97706',
  biology: '#059669',
};

const NODE_TYPES = ['Book', 'Chapter', 'Section', 'Concept', 'Skill', 'Experiment', 'Exercise'];
const NODE_NAMES = {
  Book: '教材',
  Chapter: '章/单元',
  Section: '小节',
  Concept: '概念',
  Skill: '技能',
  Experiment: '实验',
  Exercise: '练习',
};

const EDGE_TYPES = [
  'is_a',
  'prerequisites_for',
  'leads_to',
  'verifies',
  'relates_to',
  'tests_concept',
  'tests_skill',
  'appears_in',
  'is_part_of',
];
const EDGE_NAMES = {
  is_a: '层次 / 分类',
  prerequisites_for: '先修',
  leads_to: '因果 / 导向',
  verifies: '验证',
  relates_to: '相关',
  tests_concept: '测试概念',
  tests_skill: '测试技能',
  appears_in: '出现位置',
  is_part_of: '组成部分',
};
const DEFAULT_EDGE_TYPES = [
  'is_a',
  'prerequisites_for',
  'leads_to',
  'verifies',
  'relates_to',
];

const IMPORTANCE_WEIGHT = {
  '掌握': 1.6,
  '重要': 1.36,
  '理解': 1.2,
  '了解': 1.06,
};

const TYPE_WEIGHT = {
  Book: 1.4,
  Chapter: 1.3,
  Section: 1.16,
  Concept: 1.55,
  Skill: 1.18,
  Experiment: 1.08,
  Exercise: 0.88,
};

const TYPE_OFFSET = {
  Book: -390,
  Chapter: -270,
  Section: -155,
  Concept: 0,
  Skill: 170,
  Experiment: 305,
  Exercise: 430,
};

const BOOK_ORDER = new Map([
  ['1a_rjb', 0], ['1b_rjb', 1], ['2a_rjb', 2], ['2b_rjb', 3],
  ['3a_rjb', 4], ['3b_rjb', 5], ['4a_rjb', 6], ['4b_rjb', 7],
  ['5a_rjb', 8], ['5b_rjb', 9], ['6a_rjb', 10], ['6b_rjb', 11],
  ['7a_rjb', 12], ['7b_rjb', 13], ['8a_rjb', 14], ['8b_rjb', 15],
  ['9_rjb', 16], ['9a_rjb', 16], ['9b_rjb', 17],
  ['bx1_rjb', 18], ['bx2_rjb', 19], ['bx3_rjb', 20],
  ['xzxbx1_rjb', 21], ['xzxbx2_rjb', 22], ['xzxbx3_rjb', 23],
]);

function hash01(value) {
  let h = 2166136261;
  for (let i = 0; i < value.length; i++) {
    h ^= value.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967295;
}

function round(value, places = 1) {
  return Number(value.toFixed(places));
}

function shortText(value, max = 320) {
  if (!value) return '';
  const text = String(value).replace(/\s+/g, ' ').trim();
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function parseId(id) {
  const parts = id.split('_');
  const subject = SUBJECTS.includes(parts[0]) ? parts[0] : 'unknown';
  let bookKey = 'unknown';
  if (/^[1-9][ab]?$/.test(parts[1] ?? '')) {
    bookKey = `${parts[1]}_${parts[2] ?? 'rjb'}`;
  } else if (/^(bx\d|xzxbx\d)$/.test(parts[1] ?? '')) {
    bookKey = `${parts[1]}_${parts[2] ?? 'rjb'}`;
  }
  const order = BOOK_ORDER.has(bookKey) ? BOOK_ORDER.get(bookKey) : 16;
  const stage = order <= 11 ? 'primary' : order <= 17 ? 'middle' : 'highschool';
  return { subject, bookKey, order, stage };
}

const nodeIndexById = new Map(raw.nodes.map((node, index) => [node.id, index]));
const edgeTypeIndex = new Map(EDGE_TYPES.map((type, index) => [type, index]));
const nodeTypeIndex = new Map(NODE_TYPES.map((type, index) => [type, index]));
const subjectIndex = new Map(SUBJECTS.map((subject, index) => [subject, index]));
const degree = new Array(raw.nodes.length).fill(0);
const inDegree = new Array(raw.nodes.length).fill(0);
const outDegree = new Array(raw.nodes.length).fill(0);
const typeDegree = Array.from({ length: raw.nodes.length }, () => new Array(EDGE_TYPES.length).fill(0));
const edgeCounts = Object.fromEntries(EDGE_TYPES.map((type) => [type, 0]));
const edges = [];

for (const edge of raw.edges) {
  const source = nodeIndexById.get(edge.source);
  const target = nodeIndexById.get(edge.target);
  const type = edgeTypeIndex.get(edge.type);
  if (source === undefined || target === undefined || type === undefined) continue;
  edges.push([source, target, type]);
  degree[source]++;
  degree[target]++;
  outDegree[source]++;
  inDegree[target]++;
  typeDegree[source][type]++;
  typeDegree[target][type]++;
  edgeCounts[edge.type]++;
}

const widthBySubject = 720;
const height = 2300;
const maxOrder = Math.max(...BOOK_ORDER.values());

const nodes = raw.nodes.map((node, index) => {
  const parsed = parseId(node.id);
  const props = node.properties ?? {};
  const group = subjectIndex.has(parsed.subject) ? subjectIndex.get(parsed.subject) : SUBJECTS.length;
  const typeSlot = nodeTypeIndex.has(node.label) ? nodeTypeIndex.get(node.label) : NODE_TYPES.length;
  const h1 = hash01(node.id);
  const h2 = hash01(`${node.id}:z`);
  const h3 = hash01(`${node.id}:x`);
  const subjectX = (group - (SUBJECTS.length - 1) / 2) * widthBySubject;
  const typeOffset = TYPE_OFFSET[node.label] ?? 0;
  const stageOffset = parsed.stage === 'primary' ? -80 : parsed.stage === 'highschool' ? 80 : 0;
  const x = subjectX + typeOffset + stageOffset + (h3 - 0.5) * 170;
  const y = (parsed.order / maxOrder) * height + (h1 - 0.5) * 120;
  const z = (h2 - 0.5) * 760 + (typeSlot - 3) * 40;
  const importance = props.importance ?? '';
  const radiusWeight = (TYPE_WEIGHT[node.label] ?? 1) *
    (IMPORTANCE_WEIGHT[importance] ?? 1) *
    (1 + Math.log1p(degree[index]) / 5);

  return {
    id: node.id,
    n: node.name,
    lab: node.label,
    ty: typeSlot,
    x: round(x),
    y: round(y),
    z: round(z),
    g: group,
    st: parsed.stage,
    bk: parsed.bookKey,
    bo: parsed.order,
    imp: importance,
    def: shortText(props.definition || props.description || props.stem || props.process || props.analysis || ''),
    alias: Array.isArray(props.aliases) ? props.aliases.slice(0, 6) : [],
    examples: Array.isArray(props.examples) ? props.examples.slice(0, 6) : [],
    formula: shortText(props.formula || '', 160),
    unit: props.unit || '',
    answer: shortText(props.answer || '', 160),
    deg: degree[index],
    in: inDegree[index],
    out: outDegree[index],
    td: typeDegree[index],
    r: round(radiusWeight, 3),
  };
});

const out = {
  generatedAt: new Date().toISOString(),
  source: 'K12-KGraph normalized concept-centric schema graph',
  subjects: SUBJECTS,
  subjectNames: SUBJECT_NAMES,
  subjectColors: SUBJECTS.map((subject) => SUBJECT_COLORS[subject]),
  nodeTypes: NODE_TYPES,
  nodeNames: NODE_NAMES,
  edgeTypes: EDGE_TYPES,
  edgeNames: EDGE_NAMES,
  defaultEdgeTypes: DEFAULT_EDGE_TYPES,
  edgeCounts,
  height,
  maxOrder,
  nodes,
  edges,
  counts: {
    nodes: nodes.length,
    concepts: raw.meta.node_labels.Concept,
    edges: edges.length,
  },
};

writeFileSync(OUT, `window.CONCEPT_GRAPH = ${JSON.stringify(out)};\n`, 'utf8');

console.log(`Wrote ${OUT}`);
console.log(`${nodes.length} nodes, ${edges.length} edges, ${raw.meta.node_labels.Concept} concepts`);
