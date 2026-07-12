#!/usr/bin/env node
/**
 * Build compact browser data for the K12-KGraph visualization.
 *
 * Source:
 *   ../../derived/kg_rag/k12_kgraph_normalized.json
 *
 * Output:
 *   ./graphdata.js
 */

import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SOURCE = resolve(HERE, '..', '..', 'derived', 'kg_rag', 'k12_kgraph_normalized.json');
const OUT = resolve(HERE, 'graphdata.js');

const graph = JSON.parse(readFileSync(SOURCE, 'utf8'));

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
const EDGE_TYPES = [
  'appears_in',
  'is_part_of',
  'leads_to',
  'prerequisites_for',
  'is_a',
  'relates_to',
  'tests_concept',
  'tests_skill',
  'verifies',
];

const TYPE_OFFSET = {
  Book: -320,
  Chapter: -210,
  Section: -110,
  Concept: 35,
  Skill: 165,
  Experiment: 295,
  Exercise: 410,
};

const TYPE_WEIGHT = {
  Book: 2.2,
  Chapter: 1.85,
  Section: 1.55,
  Concept: 1.15,
  Skill: 1.12,
  Experiment: 0.98,
  Exercise: 0.82,
};

const IMPORTANCE_WEIGHT = {
  '掌握': 1.55,
  '重要': 1.32,
  '理解': 1.22,
  '了解': 1.08,
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

function shortText(value, max = 260) {
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

const indexById = new Map(graph.nodes.map((node, index) => [node.id, index]));
const degree = new Array(graph.nodes.length).fill(0);
const inDegree = new Array(graph.nodes.length).fill(0);
const outDegree = new Array(graph.nodes.length).fill(0);

for (const edge of graph.edges) {
  const source = indexById.get(edge.source);
  const target = indexById.get(edge.target);
  if (source === undefined || target === undefined) continue;
  degree[source]++;
  degree[target]++;
  outDegree[source]++;
  inDegree[target]++;
}

const typeIndex = new Map(NODE_TYPES.map((type, index) => [type, index]));
const edgeTypeIndex = new Map(EDGE_TYPES.map((type, index) => [type, index]));
const subjectIndex = new Map(SUBJECTS.map((subject, index) => [subject, index]));

const widthBySubject = 660;
const height = 2300;
const maxOrder = Math.max(...BOOK_ORDER.values());

const nodes = graph.nodes.map((node, index) => {
  const parsed = parseId(node.id);
  const subjectSlot = subjectIndex.has(parsed.subject) ? subjectIndex.get(parsed.subject) : SUBJECTS.length;
  const typeSlot = typeIndex.has(node.label) ? typeIndex.get(node.label) : NODE_TYPES.length;
  const h1 = hash01(node.id);
  const h2 = hash01(`${node.id}:z`);
  const h3 = hash01(`${node.id}:spread`);
  const props = node.properties ?? {};
  const order = parsed.order;
  const y = (order / maxOrder) * height + (h1 - 0.5) * 95;
  const xBase = (subjectSlot - (SUBJECTS.length - 1) / 2) * widthBySubject;
  const typeOffset = TYPE_OFFSET[node.label] ?? 0;
  const stageJitter = parsed.stage === 'primary' ? -70 : parsed.stage === 'highschool' ? 80 : 0;
  const x = xBase + typeOffset + stageJitter + (h2 - 0.5) * 150;
  const z = (h3 - 0.5) * 620 + (typeSlot - 3) * 35;
  const importance = props.importance ?? '';
  const radiusWeight = (TYPE_WEIGHT[node.label] ?? 1) *
    (IMPORTANCE_WEIGHT[importance] ?? 1) *
    (1 + Math.log1p(degree[index]) / 5);

  return {
    id: node.id,
    x: round(x),
    y: round(y),
    z: round(z),
    g: subjectSlot,
    ty: typeSlot,
    st: parsed.stage,
    bk: parsed.bookKey,
    bo: order,
    n: node.name,
    lab: node.label,
    imp: importance,
    def: shortText(props.definition || props.description || props.stem || props.process || ''),
    deg: degree[index],
    in: inDegree[index],
    out: outDegree[index],
    r: round(radiusWeight, 3),
  };
});

const edges = [];
let dropped = 0;
for (const edge of graph.edges) {
  const source = indexById.get(edge.source);
  const target = indexById.get(edge.target);
  const type = edgeTypeIndex.get(edge.type);
  if (source === undefined || target === undefined || type === undefined) {
    dropped++;
    continue;
  }
  edges.push([source, target, type]);
}

const out = {
  generatedAt: new Date().toISOString(),
  source: 'K12-KGraph normalized',
  meta: graph.meta,
  subjects: SUBJECTS,
  subjectNames: SUBJECT_NAMES,
  subjectColors: SUBJECTS.map((subject) => SUBJECT_COLORS[subject]),
  nodeTypes: NODE_TYPES,
  edgeTypes: EDGE_TYPES,
  height,
  maxOrder,
  nodes,
  edges,
};

writeFileSync(OUT, `window.K12_GRAPH = ${JSON.stringify(out)};\n`, 'utf8');

console.log(`Wrote ${OUT}`);
console.log(`${nodes.length} nodes, ${edges.length} edges, ${dropped} dropped`);
