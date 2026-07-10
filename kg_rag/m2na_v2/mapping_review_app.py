from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from kg_rag.concepts.jsonl import read_jsonl
from kg_rag.io import read_json
from kg_rag.m2na_v2.mapping_reviews import append_mapping_review, latest_mapping_reviews, mapping_review_status


class MappingReviewState:
    def __init__(self, *, mapping_root: Path, seeds_path: Path) -> None:
        self.mapping_root = mapping_root
        self.seeds_path = seeds_path

    def payload(self) -> dict[str, Any]:
        seeds = {str(row["concept_id"]): row for row in read_jsonl(self.seeds_path)}
        index = read_jsonl(self.mapping_root / "mapping_plan_index.jsonl")
        reviews = latest_mapping_reviews(self.mapping_root / "mapping_reviews.jsonl")
        pairs: dict[tuple[str, str], dict[str, Any]] = {}
        for row in index:
            concept_id = str(row["concept_id"])
            candidate_id = str(row["candidate_id"])
            strategy = str(row["strategy"])
            pair = pairs.setdefault(
                (concept_id, candidate_id),
                {
                    "seed": seeds.get(concept_id, {}),
                    "concept_id": concept_id,
                    "candidate_id": candidate_id,
                    "plans": {},
                    "reviews": {},
                },
            )
            plan_path = Path(str(row["path"]))
            pair["plans"][strategy] = read_json(plan_path)
            pair["reviews"][strategy] = reviews.get((concept_id, candidate_id, strategy), {})
        return {
            "status": mapping_review_status(mapping_root=self.mapping_root),
            "pairs": sorted(
                pairs.values(),
                key=lambda item: (
                    str(item["seed"].get("subject") or ""),
                    str(item["seed"].get("canonical_name") or ""),
                    item["candidate_id"],
                ),
            ),
        }

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        return append_mapping_review(mapping_root=self.mapping_root, **payload)


def serve_mapping_review_app(*, mapping_root: Path, seeds_path: Path, host: str, port: int) -> ThreadingHTTPServer:
    state = MappingReviewState(mapping_root=mapping_root, seeds_path=seeds_path)
    handler = _handler_for(state)
    return ThreadingHTTPServer((host, port), handler)


def _handler_for(state: MappingReviewState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/":
                self._send(_HTML.encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/api/data":
                self._send_json(state.payload())
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/api/review":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                value = json.loads(self.rfile.read(size).decode("utf-8"))
                if not isinstance(value, dict):
                    raise ValueError("request body must be an object")
                self._send_json(state.save(value))
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except Exception as exc:  # pragma: no cover
                self._send_json({"error": f"{type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            self._send(json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)

        def _send(self, payload: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the local M2NA V2 mapping-plan review app.")
    parser.add_argument("--mapping-root", type=Path, required=True)
    parser.add_argument("--seeds", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args(argv)
    server = serve_mapping_review_app(
        mapping_root=args.mapping_root,
        seeds_path=args.seeds,
        host=args.host,
        port=args.port,
    )
    print(f"M2NA V2 mapping review app: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


_HTML = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M2NA V2 映射审核</title>
<style>
:root{--ink:#182027;--muted:#65717a;--line:#d9e0e4;--paper:#f3f6f7;--panel:#fff;--nav:#142c35;--standard:#2e679c;--copy:#7a4d9a;--ok:#1b754e;--no:#b74746;--wait:#9b6500}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.5 "Segoe UI","Microsoft YaHei",sans-serif}button,input,select,textarea{font:inherit}button{cursor:pointer}header{height:64px;background:var(--nav);color:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 22px}h1{font-size:18px;margin:0}.sub{color:#c5d5d9;font-size:12px}.layout{display:grid;grid-template-columns:340px minmax(0,1fr);height:calc(100vh - 64px)}aside{background:#fff;padding:15px;overflow:auto;border-right:1px solid var(--line)}main{padding:22px;overflow:auto}.filters{display:grid;gap:9px}label{display:block;color:var(--muted);font-weight:650;font-size:12px;margin-bottom:3px}input,select,textarea{width:100%;padding:8px 9px;border:1px solid var(--line);border-radius:5px;background:#fff;color:var(--ink)}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:14px 0}.stat{border:1px solid var(--line);border-radius:5px;padding:7px}.stat b{display:block;font-size:17px}.list{display:grid;gap:6px}.item{text-align:left;border:1px solid var(--line);background:#fff;border-radius:5px;padding:9px}.item.active{border-color:#008078;box-shadow:inset 3px 0 #008078}.item:hover{background:#f8fbfc}.topline{display:flex;justify-content:space-between;gap:6px;font-weight:650}.meta{margin-top:2px;color:var(--muted);font-size:12px}.badge{padding:1px 7px;border-radius:999px;font-size:11px;white-space:nowrap}.pending{color:var(--wait);background:#fff0d5}.approve{color:var(--ok);background:#def4e7}.reject{color:var(--no);background:#fde4e3}.split{display:grid;grid-template-columns:1fr 1fr;gap:15px}.card{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:15px}.card h3{font-size:15px;margin:0 0 10px}.standard{border-top:4px solid var(--standard)}.copycat{border-top:4px solid var(--copy)}.heading{display:flex;justify-content:space-between;align-items:start;gap:12px;margin-bottom:17px}h2{margin:0;font-size:24px}.definition{color:#354149;margin-top:5px}.summary{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin:12px 0}.summary div{border:1px solid var(--line);border-radius:4px;padding:7px}.summary b{display:block}.field{margin:10px 0}.field strong{display:block;font-size:12px;color:var(--muted);margin-bottom:3px}.map{border-left:3px solid #cad8df;padding:7px 9px;margin:6px 0;background:#f7fafb}.map b{display:block}.edge{border-left-color:#8bc1ba}.review{margin-top:16px}.review-grid{display:grid;grid-template-columns:150px 1fr;gap:10px}.actions{display:flex;justify-content:flex-end;gap:8px;margin-top:10px}.approveBtn,.rejectBtn,.secondary{border-radius:5px;padding:8px 13px}.approveBtn{background:var(--ok);border:1px solid var(--ok);color:#fff}.rejectBtn{background:var(--no);border:1px solid var(--no);color:#fff}.secondary{background:#fff;border:1px solid var(--line)}.note{font-size:12px;color:var(--muted);margin-top:8px}.empty{text-align:center;color:var(--muted);margin:120px auto;max-width:650px}@media(max-width:1000px){.layout{grid-template-columns:1fr;height:auto}aside{max-height:40vh;border-right:0;border-bottom:1px solid var(--line)}main{overflow:visible}.split{grid-template-columns:1fr}}
</style></head><body><header><div><h1>M2NA V2 映射计划审核</h1><div class="sub">并排比较 Standard 与 Copycat-inspired 结构类比</div></div><div id="status" class="sub">加载中</div></header><div class="layout"><aside><div class="filters"><div><label>搜索</label><input id="q" placeholder="概念名、ID、故事域"></div><div><label>学科</label><select id="subject"><option value="">全部学科</option></select></div><div><label>审核状态</label><select id="state"><option value="pending">待审核</option><option value="">全部</option><option value="approve">已批准</option><option value="reject">已拒绝</option></select></div><div><label>策略</label><select id="strategy"><option value="">两种都显示</option><option value="standard">仅 Standard 待审</option><option value="copycat">仅 Copycat 待审</option></select></div></div><div id="stats" class="stats"></div><div id="list" class="list"></div></aside><main id="detail"><div class="empty">加载映射计划中…</div></main></div>
<script>
let app={pairs:[],status:{},selected:null};const $=x=>document.getElementById(x),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function d(pair,s){return pair.reviews?.[s]?.decision||'pending'}function badge(v){return `<span class="badge ${v}">${v==='approve'?'批准':v==='reject'?'拒绝':'待审'}</span>`}function ok(pair){const f=$('strategy').value;if(!f)return true;return d(pair,f)===$('state').value||(!$('state').value&&true)}function filtered(){let q=$('q').value.trim().toLowerCase(),sub=$('subject').value,st=$('state').value;return app.pairs.filter(p=>{let s=p.seed||{},domains=Object.values(p.plans||{}).map(x=>x.source_domain||'').join(' '),hay=`${s.canonical_name||''} ${p.concept_id} ${domains}`.toLowerCase();let statePass=!st||($('strategy').value?d(p,$('strategy').value)===st:Object.values(p.reviews||{}).some(x=>x.decision===st)||(st==='pending'&&['standard','copycat'].some(x=>d(p,x)==='pending')));return(!q||hay.includes(q))&&(!sub||s.subject===sub)&&statePass&&ok(p)})}
function list(){let rows=filtered();$('list').innerHTML=rows.map(p=>`<button class="item ${p.concept_id+'|'+p.candidate_id===app.selected?'active':''}" data-k="${esc(p.concept_id+'|'+p.candidate_id)}"><div class="topline"><span>${esc(p.seed.canonical_name)}</span><span>${badge(d(p,'standard'))}${badge(d(p,'copycat'))}</span></div><div class="meta">${esc(p.seed.subject)} · ${esc(p.candidate_id)} · S: ${esc(p.plans.standard?.source_domain||'')} · C: ${esc(p.plans.copycat?.source_domain||'')}</div></button>`).join('')||'<div class="empty">无匹配计划</div>';document.querySelectorAll('.item').forEach(x=>x.onclick=()=>{app.selected=x.dataset.k;list();detail()})}
function planCard(p,strategy){let plan=p.plans[strategy]||{}, rev=p.reviews[strategy]||{}, label=strategy==='standard'?'Standard':'Copycat-inspired';return `<section class="card ${strategy}"><h3>${label} ${badge(d(p,strategy))}</h3><div class="field"><strong>故事域</strong>${esc(plan.source_domain||'缺失')}</div><div class="field"><strong>冲突</strong>${esc(plan.conflict||'缺失')}</div><div class="field"><strong>事件链</strong>${(plan.event_chain||[]).map((x,i)=>`<div class="map">${i+1}. ${esc(x)}</div>`).join('')}</div><div class="field"><strong>节点映射</strong>${(plan.node_mappings||[]).map(x=>`<div class="map"><b>${esc(x.mechanism_node_id)} → ${esc(x.story_carrier)}</b><span class="meta">${esc(x.mapping_type||'')}</span></div>`).join('')}</div><div class="field"><strong>边映射</strong>${(plan.edge_mappings||[]).map(x=>`<div class="map edge"><b>${esc(x.mechanism_edge_id)} → ${esc(x.story_relation)}</b><span class="meta">方向保持：${x.direction_preserved?'是':'否'}</span></div>`).join('')}</div><div class="field"><strong>风险项</strong>${(plan.risk_notes||[]).map(x=>`<div class="note">• ${esc(x)}</div>`).join('')}</div><div class="review"><div class="review-grid"><div><label>审核人</label><input id="${strategy}Reviewer" value="${esc(rev.reviewer||localStorage.mappingReviewer||'')}"></div><div><label>意见</label><textarea id="${strategy}Notes" rows="2">${esc(rev.notes||'')}</textarea></div></div><div class="actions"><button class="rejectBtn" onclick="save('${strategy}','reject')">拒绝</button><button class="approveBtn" onclick="save('${strategy}','approve')">批准</button></div></div></section>`}
function detail(){let p=app.pairs.find(x=>x.concept_id+'|'+x.candidate_id===app.selected);if(!p){$('detail').innerHTML='<div class="empty">从左侧选择一组映射计划。</div>';return}let s=p.seed||{},a=p.plans.standard||{},c=p.plans.copycat||{};$('detail').innerHTML=`<div class="heading"><div><h2>${esc(s.canonical_name)} · ${esc(p.candidate_id)}</h2><div class="definition">${esc(s.definition||'')}</div></div><div class="meta">${esc(p.concept_id)} · ${esc(s.subject)} · ${esc(s.concept_type)}</div></div><div class="summary"><div><b>${a.node_mappings?.length||0}</b>Standard 节点映射</div><div><b>${a.edge_mappings?.length||0}</b>Standard 边映射</div><div><b>${c.node_mappings?.length||0}</b>Copycat 节点映射</div><div><b>${c.edge_mappings?.length||0}</b>Copycat 边映射</div></div><div class="split">${planCard(p,'standard')}${planCard(p,'copycat')}</div>`}
async function save(strategy,decision){let p=app.pairs.find(x=>x.concept_id+'|'+x.candidate_id===app.selected),reviewer=$(strategy+'Reviewer').value.trim(),notes=$(strategy+'Notes').value.trim();if(!reviewer){alert('请填写审核人');return}localStorage.mappingReviewer=reviewer;let res=await fetch('/api/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({concept_id:p.concept_id,candidate_id:p.candidate_id,strategy,decision,reviewer,notes})}),data=await res.json();if(!res.ok){alert(data.error||'保存失败');return}await load();app.selected=p.concept_id+'|'+p.candidate_id;list();detail()}
function stats(){let s=app.status;$('stats').innerHTML=`<div class="stat"><b>${s.pending_count||0}</b>待审计划</div><div class="stat"><b>${s.approved_count||0}</b>批准</div><div class="stat"><b>${s.rejected_count||0}</b>拒绝</div>`;$('status').textContent=`${s.plan_count||0} 个映射计划 · ${s.pending_count||0} 个待审`}
async function load(){let r=await fetch('/api/data'),x=await r.json();app.pairs=x.pairs;app.status=x.status;let subs=[...new Set(app.pairs.map(p=>p.seed.subject))].sort();$('subject').innerHTML='<option value="">全部学科</option>'+subs.map(s=>`<option value="${esc(s)}">${esc(s)}</option>`).join('');stats();if(!app.selected||!app.pairs.some(p=>p.concept_id+'|'+p.candidate_id===app.selected))app.selected=filtered()[0]?.concept_id+'|'+filtered()[0]?.candidate_id;list();detail()}
['q','subject','state','strategy'].forEach(x=>$(x).addEventListener('input',()=>{if(!filtered().some(p=>p.concept_id+'|'+p.candidate_id===app.selected)){let z=filtered()[0];app.selected=z?z.concept_id+'|'+z.candidate_id:null}list();detail()}));load().catch(e=>$('detail').innerHTML='<div class="empty">'+esc(e.message)+'</div>');
</script></body></html>"""
