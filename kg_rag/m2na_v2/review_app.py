from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from kg_rag.concepts.jsonl import read_jsonl
from kg_rag.m2na_v2.reviews import append_review_decisions, latest_reviews, pipeline_status


def serve_review_app(*, seeds_path: Path, output_root: Path, host: str, port: int) -> ThreadingHTTPServer:
    state = ReviewAppState(seeds_path=seeds_path, output_root=output_root)
    handler = _handler_for(state)
    return ThreadingHTTPServer((host, port), handler)


class ReviewAppState:
    def __init__(self, *, seeds_path: Path, output_root: Path) -> None:
        self.seeds_path = seeds_path
        self.output_root = output_root

    def payload(self) -> dict[str, Any]:
        seeds = {str(item["concept_id"]): item for item in read_jsonl(self.seeds_path)}
        records = {
            str(item["concept_id"]): item
            for item in read_jsonl(self.output_root / "mechanisms.raw.jsonl")
        }
        validations = {
            str(item["concept_id"]): item
            for item in read_jsonl(self.output_root / "mechanism_validation.jsonl")
        }
        reviews = latest_reviews(self.output_root / "mechanism_reviews.jsonl")
        rows = []
        for concept_id, seed in seeds.items():
            retrieval_path = self.output_root / "retrieval" / f"{concept_id}.json"
            retrieval = _read_json(retrieval_path) if retrieval_path.exists() else {}
            record = records.get(concept_id, {})
            graph = record.get("mechanism_graph", {}) if isinstance(record, dict) else {}
            rows.append(
                {
                    "seed": seed,
                    "retrieval": retrieval,
                    "mechanism_graph": graph,
                    "generation_constraints": record.get("generation_constraints", {}),
                    "validation": validations.get(
                        concept_id,
                        {"concept_id": concept_id, "status": "missing", "errors": ["missing mechanism record"]},
                    ),
                    "review": reviews.get(concept_id, {}),
                }
            )
        return {
            "status": pipeline_status(seeds_path=self.seeds_path, output_root=self.output_root),
            "rows": sorted(rows, key=lambda row: (row["seed"]["subject"], row["seed"]["canonical_name"])),
        }

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = append_review_decisions(
            decisions=[payload],
            seeds_path=self.seeds_path,
            output_root=self.output_root,
        )
        return {**result, "status": pipeline_status(seeds_path=self.seeds_path, output_root=self.output_root)}


def _handler_for(state: ReviewAppState) -> type[BaseHTTPRequestHandler]:
    class ReviewHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/":
                self._send_html(_HTML)
                return
            if path == "/api/review-data":
                self._send_json(state.payload())
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/api/reviews":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(body, dict):
                    raise ValueError("Request body must be an object.")
                self._send_json(state.save(body))
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            except Exception as exc:  # pragma: no cover - defensive API boundary
                self._send_json({"error": f"{type(exc).__name__}: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_html(self, text: str) -> None:
            payload = text.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_json(self, value: Any, *, status: HTTPStatus = HTTPStatus.OK) -> None:
            payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return ReviewHandler


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    return value if isinstance(value, dict) else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the local M2NA V2 mechanism review app.")
    parser.add_argument("--seeds", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    server = serve_review_app(
        seeds_path=args.seeds,
        output_root=args.output_root,
        host=args.host,
        port=args.port,
    )
    print(f"M2NA V2 review app: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>M2NA V2 机制审核</title>
  <style>
    :root { --ink:#182027; --muted:#66727c; --paper:#f4f6f7; --panel:#fff; --line:#d9dfe3; --teal:#007c77; --blue:#2d65a7; --red:#b54746; --amber:#a76400; --green:#18714b; }
    * { box-sizing:border-box; } body { margin:0; background:var(--paper); color:var(--ink); font:14px/1.5 "Segoe UI","Microsoft YaHei",sans-serif; }
    button,input,select,textarea { font:inherit; } button { cursor:pointer; }
    header { height:64px; display:flex; align-items:center; justify-content:space-between; padding:0 24px; background:#142c35; color:#fff; }
    header h1 { font-size:18px; margin:0; font-weight:650; } .sub { color:#bfd1d5; font-size:12px; }
    .layout { display:grid; grid-template-columns:340px minmax(0,1fr); height:calc(100vh - 64px); }
    aside { border-right:1px solid var(--line); background:#fff; overflow:auto; padding:16px; }
    main { min-width:0; overflow:auto; padding:24px; }
    .filters { display:grid; gap:10px; } label { color:var(--muted); font-size:12px; font-weight:600; } input,select,textarea { width:100%; border:1px solid var(--line); background:#fff; border-radius:5px; padding:8px 10px; color:var(--ink); }
    .stats { display:grid; grid-template-columns:repeat(3,1fr); gap:6px; margin:16px 0; } .stat { border:1px solid var(--line); padding:8px; border-radius:5px; } .stat b { display:block; font-size:18px; }
    .list { display:grid; gap:6px; } .item { text-align:left; padding:10px; border:1px solid var(--line); border-radius:5px; background:#fff; } .item.active { border-color:var(--teal); box-shadow:inset 3px 0 var(--teal); } .item:hover { background:#f7fbfb; } .item-title { display:flex; justify-content:space-between; gap:8px; font-weight:650; } .item-meta { color:var(--muted); font-size:12px; margin-top:2px; }
    .badge { display:inline-flex; align-items:center; padding:1px 7px; border-radius:999px; font-size:11px; font-weight:650; white-space:nowrap; } .pending { background:#fff0d4; color:var(--amber); } .approved { background:#dff4e8; color:var(--green); } .rejected { background:#fde5e4; color:var(--red); } .invalid { background:#f1e3ef; color:#8a397b; }
    .empty { max-width:700px; margin:120px auto; text-align:center; color:var(--muted); }
    .title-row { display:flex; align-items:start; justify-content:space-between; gap:16px; margin-bottom:20px; } h2 { margin:0; font-size:24px; } .title-meta { color:var(--muted); margin-top:4px; }
    .grid { display:grid; grid-template-columns:minmax(300px,1fr) minmax(380px,1.25fr); gap:16px; } .section { background:var(--panel); border:1px solid var(--line); border-radius:6px; padding:16px; } .section h3 { margin:0 0 12px; font-size:14px; }
    .definition { white-space:pre-wrap; color:#26333a; } .kv { display:grid; grid-template-columns:120px 1fr; gap:7px 10px; margin:0; } .kv dt { color:var(--muted); } .kv dd { margin:0; word-break:break-word; }
    .graph { display:grid; gap:8px; } .node { border-left:4px solid var(--blue); background:#f5f8fb; padding:9px 10px; border-radius:3px; } .node-head { display:flex; justify-content:space-between; gap:10px; font-weight:650; } .type { color:var(--blue); font-size:12px; } .refs { margin-top:5px; color:var(--muted); font-size:12px; word-break:break-all; }
    .edge { display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:8px; padding:8px 0; border-bottom:1px solid #edf0f1; } .edge:last-child { border-bottom:none; } .edge-rel { color:var(--teal); font-weight:700; font-size:12px; }
    .path { border:1px solid #d6e2e9; background:#f8fbfd; padding:9px; border-radius:4px; margin:7px 0; } .path small { color:var(--muted); }
    .review { position:sticky; bottom:0; margin-top:16px; background:#fff; border:1px solid var(--line); border-radius:6px; padding:16px; box-shadow:0 4px 16px rgba(20,44,53,.08); } .review-grid { display:grid; grid-template-columns:200px 1fr; gap:12px; } .actions { display:flex; justify-content:flex-end; gap:8px; margin-top:12px; } .approve-btn { color:#fff; background:var(--green); border:1px solid var(--green); border-radius:5px; padding:8px 14px; } .reject-btn { color:#fff; background:var(--red); border:1px solid var(--red); border-radius:5px; padding:8px 14px; } .secondary { color:var(--ink); background:#fff; border:1px solid var(--line); border-radius:5px; padding:8px 12px; }
    .notice { margin-top:10px; color:var(--muted); font-size:12px; } .error { color:var(--red); } .success { color:var(--green); }
    @media (max-width:900px) { .layout { grid-template-columns:1fr; height:auto; } aside { border-right:0; border-bottom:1px solid var(--line); max-height:42vh; } .grid { grid-template-columns:1fr; } main { overflow:visible; } .review { position:static; } }
  </style>
</head>
<body>
<header><div><h1>M2NA V2 机制审核</h1><div class="sub">证据驱动机制图 · 审核决定追加保存</div></div><div id="statusText" class="sub">加载中</div></header>
<div class="layout"><aside>
  <div class="filters">
    <div><label>搜索概念</label><input id="query" placeholder="名称、ID 或定义"></div>
    <div><label>学科</label><select id="subject"><option value="">全部学科</option></select></div>
    <div><label>审核状态</label><select id="reviewState"><option value="pending">待审核</option><option value="">全部</option><option value="approve">已批准</option><option value="reject">已拒绝</option><option value="invalid">规则无效</option></select></div>
  </div>
  <div class="stats" id="stats"></div><div class="list" id="list"></div>
</aside><main id="detail"><div class="empty">正在加载审核数据…</div></main></div>
<script>
let state={rows:[],status:{},selected:null};
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function decision(row){ return row.review?.decision || (row.validation?.status!=='valid'?'invalid':'pending'); }
function badge(row){ const d=decision(row), label={pending:'待审核',approve:'已批准',reject:'已拒绝',invalid:'规则无效'}[d]; return `<span class="badge ${d==='approve'?'approved':d==='reject'?'rejected':d==='invalid'?'invalid':'pending'}">${label}</span>`; }
function filtered(){ const q=$('query').value.trim().toLowerCase(), subj=$('subject').value, status=$('reviewState').value; return state.rows.filter(r=>{const s=r.seed; const hay=`${s.canonical_name} ${s.concept_id} ${s.definition}`.toLowerCase(); return (!q||hay.includes(q))&&(!subj||s.subject===subj)&&(!status||decision(r)===status);});}
function renderList(){ const rows=filtered(); $('list').innerHTML=rows.map(r=>`<button class="item ${state.selected===r.seed.concept_id?'active':''}" data-id="${esc(r.seed.concept_id)}"><div class="item-title"><span>${esc(r.seed.canonical_name)}</span>${badge(r)}</div><div class="item-meta">${esc(r.seed.subject)} · ${esc(r.seed.concept_type)} · ${esc(r.seed.concept_id)}</div></button>`).join('')||'<div class="empty">没有匹配概念</div>'; document.querySelectorAll('.item').forEach(el=>el.onclick=()=>{state.selected=el.dataset.id; renderList();renderDetail();});}
function refs(list){return (list||[]).map(esc).join('<br>');}
function nodeMap(row){return Object.fromEntries((row.mechanism_graph.nodes||[]).map(n=>[n.id,n]));}
function renderDetail(){ const row=state.rows.find(r=>r.seed.concept_id===state.selected); if(!row){$('detail').innerHTML='<div class="empty">从左侧选择一个概念开始审核。</div>';return;} const s=row.seed,g=row.mechanism_graph||{},r=row.retrieval||{},v=row.validation||{},rev=row.review||{},nodes=nodeMap(row), paths=r.selected_paths||[]; const direct=r.retrieval_decision||{};
 $('detail').innerHTML=`<div class="title-row"><div><h2>${esc(s.canonical_name)} ${badge(row)}</h2><div class="title-meta">${esc(s.concept_id)} · ${esc(s.subject)} · ${esc(s.concept_type)}</div></div><div class="title-meta">验证：${esc(v.status||'missing')}</div></div>
 <div class="grid">
   <section class="section"><h3>ConceptSeed</h3><dl class="kv"><dt>别名</dt><dd>${esc((s.aliases||[]).join('、')||'无')}</dd><dt>禁用词</dt><dd>${esc((s.forbidden_terms||[]).join('、'))}</dd><dt>定义</dt><dd class="definition">${esc(s.definition)}</dd></dl></section>
   <section class="section"><h3>检索决策</h3><dl class="kv"><dt>模式</dt><dd>${esc(r.retrieval_stats?.retrieval_mode||'missing')}</dd><dt>直接边</dt><dd>${esc(direct.direct_edge_count??0)}</dd><dt>两跳扩展</dt><dd>${direct.expanded_to_two_hop?'是':'否'} ${esc(direct.expansion_mode||'')}</dd><dt>判断理由</dt><dd>${esc((direct.direct_structure_reasons||[]).join('；'))}</dd><dt>路径数</dt><dd>${esc((r.selected_paths||[]).length)}</dd></dl>
   ${paths.map(p=>`<div class="path"><b>${esc(p.path_kind)}</b> · ${esc((p.node_names||[]).join(' → '))}<br><small>${p.lexical_anchor?`定义锚点：${esc(p.lexical_anchor)} · `:''}score ${esc(p.score)}</small></div>`).join('')||'<div class="notice">未触发两跳路径扩展。</div>'}</section>
   <section class="section"><h3>机制节点</h3><div class="graph">${(g.nodes||[]).map(n=>`<div class="node"><div class="node-head"><span>${esc(n.id)} · ${esc(n.text)}</span><span class="type">${esc(n.type)}</span></div><div class="refs">${refs(n.evidence_refs)}</div></div>`).join('')||'<div class="notice">没有机制节点。</div>'}</div></section>
   <section class="section"><h3>机制边</h3>${(g.edges||[]).map(e=>`<div class="edge"><span>${esc(nodes[e.source]?.text||e.source)}</span><span class="edge-rel">${esc(e.relation)} →</span><span>${esc(nodes[e.target]?.text||e.target)}</span><div class="refs" style="grid-column:1/-1">${refs(e.evidence_refs)}</div></div>`).join('')||'<div class="notice">没有机制边。</div>'}</section>
   <section class="section"><h3>规则验证</h3>${v.status==='valid'?'<div class="success">规则验证已通过。</div>':`<div class="error">${esc((v.errors||[]).join('；'))}</div>`}<div class="notice">章节桥接边只提供课程上下文，不能作为机制证据。审核时请关注节点与边的证据引用是否足以支持机制表述。</div></section>
   <section class="section"><h3>生成约束</h3><dl class="kv"><dt>保留节点</dt><dd>${esc((row.generation_constraints?.must_preserve_node_ids||[]).join('、'))}</dd><dt>保留边</dt><dd>${esc((row.generation_constraints?.must_preserve_edge_ids||[]).join('、'))}</dd></dl></section>
 </div>
 <section class="review"><h3>审核决定</h3><div class="review-grid"><div><label>审核人</label><input id="reviewer" value="${esc(rev.reviewer||localStorage.reviewer||'')}" placeholder="必填"></div><div><label>审核意见</label><textarea id="notes" rows="3" placeholder="说明保留、修改或拒绝的原因">${esc(rev.notes||'')}</textarea></div></div><div class="actions"><button class="secondary" id="skip">下一条待审核</button><button class="reject-btn" id="reject">拒绝</button><button class="approve-btn" id="approve">批准</button></div><div class="notice" id="notice">${rev.reviewed_at_utc?`上次审核：${esc(rev.reviewed_at_utc)}`:'审核决定会追加保存，并实时更新 approved records。'}</div></section>`;
 $('approve').onclick=()=>save('approve'); $('reject').onclick=()=>save('reject'); $('skip').onclick=nextPending;
}
async function save(decisionValue){ const row=state.rows.find(r=>r.seed.concept_id===state.selected), reviewer=$('reviewer').value.trim(), notes=$('notes').value.trim(), notice=$('notice'); if(!reviewer){notice.textContent='请填写审核人。';notice.className='notice error';return;} localStorage.reviewer=reviewer; notice.textContent='保存中…'; try {let res=await fetch('/api/reviews',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({concept_id:row.seed.concept_id,decision:decisionValue,reviewer,notes})}),data=await res.json();if(!res.ok)throw new Error(data.error||'保存失败');await load();state.selected=row.seed.concept_id;renderList();renderDetail();$('notice').textContent=`已保存：${decisionValue==='approve'?'批准':'拒绝'}。approved 数量：${data.approved_count}`;$('notice').className='notice success';}catch(err){notice.textContent=err.message;notice.className='notice error';}}
function nextPending(){ const rows=filtered().filter(r=>decision(r)==='pending'), i=rows.findIndex(r=>r.seed.concept_id===state.selected); const next=rows[i+1]||rows[0];if(next){state.selected=next.seed.concept_id;renderList();renderDetail();}}
function renderStats(){const s=state.status;$('stats').innerHTML=`<div class="stat"><b>${s.pending_review_count||0}</b>待审</div><div class="stat"><b>${s.review_approve_count||0}</b>批准</div><div class="stat"><b>${s.rejected_count||0}</b>拒绝</div>`;$('statusText').textContent=`${s.valid_count||0}/${s.mechanism_count||0} 机制有效 · ${s.approved_count||0} 已进入实验`; }
async function load(){const res=await fetch('/api/review-data'),data=await res.json();state.rows=data.rows;state.status=data.status;const subjects=[...new Set(state.rows.map(r=>r.seed.subject))].sort();$('subject').innerHTML='<option value="">全部学科</option>'+subjects.map(s=>`<option value="${esc(s)}">${esc(s)}</option>`).join('');renderStats();if(!state.selected||!state.rows.some(r=>r.seed.concept_id===state.selected)){state.selected=filtered()[0]?.seed.concept_id||state.rows[0]?.seed.concept_id;}renderList();renderDetail();}
['query','subject','reviewState'].forEach(id=>$(id).addEventListener('input',()=>{if(!filtered().some(r=>r.seed.concept_id===state.selected))state.selected=filtered()[0]?.seed.concept_id||null;renderList();renderDetail();}));
load().catch(err=>$('detail').innerHTML=`<div class="empty error">${esc(err.message)}</div>`);
</script></body></html>"""
