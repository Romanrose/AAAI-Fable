from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import urlparse

from kg_rag.concepts.jsonl import read_jsonl
from kg_rag.io import read_json
from kg_rag.story_pilot.pipeline import STRATEGIES
from kg_rag.story_pilot.reviews import append_story_review, latest_story_reviews, story_review_status
from kg_rag.story_pilot.selection import PILOT12_IDS


STRATEGY_LABELS = {
    "standard": "Standard",
    "copycat": "Deterministic Copycat",
    "llm_guided_copycat": "LLM-guided Copycat",
}


class StoryReviewState:
    def __init__(self, *, pilot_root: Path) -> None:
        self.pilot_root = pilot_root
        self._write_lock = Lock()

    def payload(self) -> dict[str, Any]:
        inputs = read_jsonl(self.pilot_root / "story_input_index.jsonl")
        input_by_concept: dict[str, dict[str, Any]] = {}
        for row in inputs:
            input_by_concept.setdefault(str(row["concept_id"]), row)
        reviews = latest_story_reviews(self.pilot_root / "story_reviews.jsonl")
        concepts: list[dict[str, Any]] = []
        for concept_id in PILOT12_IDS:
            source = input_by_concept[concept_id]
            seed = read_json(Path(source["seed_path"]))
            mechanism = read_json(Path(source["mechanism_record_path"]))
            candidates: list[dict[str, Any]] = []
            for strategy in STRATEGIES:
                for number in range(1, 4):
                    candidate_id = f"candidate_{number:03d}"
                    output_dir = self.pilot_root / "stories" / concept_id / strategy / candidate_id
                    candidates.append(
                        {
                            "strategy": strategy,
                            "strategy_label": STRATEGY_LABELS[strategy],
                            "candidate_id": candidate_id,
                            "story": _read_text(output_dir / "final_story.txt"),
                            "mapping_plan": _read_optional_json(output_dir / "frozen_mapping_plan.json"),
                            "alignment": _read_optional_json(output_dir / "final_alignment.json"),
                            "metrics": _read_optional_json(output_dir / "final_metrics.json"),
                            "judgment": _read_optional_json(output_dir / "final_judgment.json"),
                            "final_status": _read_optional_json(output_dir / "final_status.json"),
                            "initial_status": _read_optional_json(output_dir / "status.json"),
                            "review": reviews.get((concept_id, strategy, candidate_id), {}),
                        }
                    )
            concepts.append(
                {
                    "concept_id": concept_id,
                    "seed": seed,
                    "mechanism_graph": mechanism.get("mechanism_graph", {}),
                    "candidates": candidates,
                }
            )
        return {
            "status": story_review_status(pilot_root=self.pilot_root),
            "strategies": [
                {"id": strategy, "label": STRATEGY_LABELS[strategy]} for strategy in STRATEGIES
            ],
            "concepts": concepts,
        }

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._write_lock:
            return append_story_review(
                pilot_root=self.pilot_root,
                concept_id=str(payload.get("concept_id") or ""),
                strategy=str(payload.get("strategy") or ""),
                candidate_id=str(payload.get("candidate_id") or ""),
                decision=str(payload.get("decision") or ""),
                reviewer=str(payload.get("reviewer") or ""),
                notes=str(payload.get("notes") or ""),
                preferred=bool(payload.get("preferred", False)),
            )


def serve_story_review_app(*, pilot_root: Path, host: str, port: int) -> ThreadingHTTPServer:
    state = StoryReviewState(pilot_root=pilot_root)
    return ThreadingHTTPServer((host, port), _handler_for(state))


def _handler_for(state: StoryReviewState) -> type[BaseHTTPRequestHandler]:
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
                payload = json.loads(self.rfile.read(size).decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("Request body must be an object.")
                self._send_json(state.save(payload))
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except Exception as exc:  # pragma: no cover - defensive API boundary
                self._send_json(
                    {"error": f"{type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR
                )

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            self._send(
                json.dumps(value, ensure_ascii=False).encode("utf-8"),
                "application/json; charset=utf-8",
                status,
            )

        def _send(
            self, payload: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return Handler


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = read_json(path)
    return value if isinstance(value, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the Story Pilot final-story review app.")
    parser.add_argument("--pilot-root", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8768)
    args = parser.parse_args(argv)
    server = serve_story_review_app(
        pilot_root=args.pilot_root,
        host=args.host,
        port=args.port,
    )
    print(f"Story Pilot review app: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


_HTML = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>故事候选审批</title>
<style>
:root{--ink:#172126;--muted:#65727a;--line:#d7dfe3;--paper:#f3f6f7;--panel:#fff;--nav:#183039;--accent:#087f78;--blue:#2d6694;--violet:#76518d;--ok:#19734c;--no:#b04442;--warn:#966100;--soft:#edf2f4}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.55 "Segoe UI","Microsoft YaHei",sans-serif}button,input,select,textarea{font:inherit}button{cursor:pointer}header{min-height:64px;background:var(--nav);color:#fff;display:flex;align-items:center;justify-content:space-between;gap:18px;padding:12px 22px}h1{font-size:18px;margin:0;letter-spacing:0}.sub{color:#c9d7db;font-size:12px}.layout{display:grid;grid-template-columns:320px minmax(0,1fr);height:calc(100vh - 64px)}aside{background:#fff;border-right:1px solid var(--line);padding:14px;overflow:auto}main{padding:20px;overflow:auto}.filters{display:grid;gap:8px}.filter-row{display:grid;grid-template-columns:1fr 1fr;gap:8px}label{display:block;color:var(--muted);font-size:12px;font-weight:650;margin-bottom:3px}input,select,textarea{width:100%;border:1px solid var(--line);border-radius:5px;background:#fff;color:var(--ink);padding:8px 9px}textarea{resize:vertical}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:13px 0}.stat{border:1px solid var(--line);border-radius:5px;padding:7px;background:#fff}.stat b{display:block;font-size:17px}.list{display:grid;gap:6px}.concept{width:100%;text-align:left;border:1px solid var(--line);border-radius:5px;background:#fff;padding:9px}.concept:hover{background:#f8fafb}.concept.active{border-color:var(--accent);box-shadow:inset 3px 0 var(--accent)}.concept-title{display:flex;justify-content:space-between;gap:8px;font-weight:700}.meta{color:var(--muted);font-size:12px}.count{font-weight:600;white-space:nowrap}.heading{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;margin-bottom:12px}h2{font-size:23px;margin:0}.definition{max-width:920px;color:#344148;margin-top:4px}.strategy-tabs{display:flex;gap:0;margin:12px 0 16px}.strategy-tabs button{border:1px solid var(--line);background:#fff;padding:8px 14px}.strategy-tabs button:first-child{border-radius:5px 0 0 5px}.strategy-tabs button:last-child{border-radius:0 5px 5px 0}.strategy-tabs button+button{border-left:0}.strategy-tabs button.active{background:var(--nav);border-color:var(--nav);color:#fff}.mechanism{display:flex;gap:6px;overflow:auto;padding:9px 0 13px}.mechanism span{flex:0 0 auto;border-left:3px solid var(--accent);background:#fff;border-top:1px solid var(--line);border-right:1px solid var(--line);border-bottom:1px solid var(--line);padding:6px 9px}.candidates{display:grid;grid-template-columns:repeat(3,minmax(280px,1fr));gap:12px;align-items:start}.candidate{background:var(--panel);border:1px solid var(--line);border-radius:6px;overflow:hidden}.candidate.preferred{border-color:var(--ok);box-shadow:inset 0 4px var(--ok)}.candidate-head{padding:12px 13px;border-bottom:1px solid var(--line)}.candidate-title{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:15px;font-weight:700}.badges{display:flex;gap:5px;flex-wrap:wrap;margin-top:7px}.badge{border-radius:999px;padding:2px 7px;font-size:11px;white-space:nowrap}.accept,.approved{color:var(--ok);background:#def3e7}.revise,.pending{color:var(--warn);background:#fff0d3}.reject,.rejected{color:var(--no);background:#fde4e3}.source{color:#365d72;background:#e4f0f5}.preferred-badge{color:#fff;background:var(--ok)}.metrics{display:grid;grid-template-columns:repeat(3,1fr);border-bottom:1px solid var(--line)}.metric{padding:8px 5px;text-align:center;border-right:1px solid var(--line);font-size:11px;color:var(--muted)}.metric:last-child{border-right:0}.metric b{display:block;color:var(--ink);font-size:15px}.story{padding:13px;white-space:pre-wrap;min-height:420px;font-size:14px;line-height:1.8}.story.empty{color:var(--no)}details{border-top:1px solid var(--line)}summary{cursor:pointer;padding:9px 13px;font-weight:650;background:#f8fafb}.detail-body{padding:10px 13px;max-height:430px;overflow:auto}.mapping{border-left:3px solid #9eb8c4;padding:5px 8px;margin:5px 0;background:#f7fafb}.mapping.edge{border-left-color:#73aaa2}.mapping b{display:block}.score-grid{display:grid;grid-template-columns:1fr 1fr;gap:5px}.score{display:flex;justify-content:space-between;border-bottom:1px solid var(--line);padding:3px}.diagnosis{margin-top:8px;color:#39474e}.review{border-top:1px solid var(--line);padding:12px 13px}.review-grid{display:grid;gap:7px}.actions{display:grid;grid-template-columns:auto auto 1fr;gap:6px;margin-top:8px}.actions button{border-radius:5px;padding:7px 9px}.approve-btn{background:var(--ok);border:1px solid var(--ok);color:#fff}.reject-btn{background:#fff;border:1px solid var(--no);color:var(--no)}.preferred-btn{background:var(--nav);border:1px solid var(--nav);color:#fff}.notice{min-height:18px;margin-top:5px;color:var(--muted);font-size:12px}.empty-page{text-align:center;color:var(--muted);margin:120px auto}.ok-text{color:var(--ok)}.error-text{color:var(--no)}@media(max-width:1250px){.candidates{grid-template-columns:1fr}.story{min-height:0}.layout{grid-template-columns:280px minmax(0,1fr)}}@media(max-width:760px){header{align-items:flex-start}.layout{display:block;height:auto}aside{max-height:42vh;border-right:0;border-bottom:1px solid var(--line)}main{padding:14px}.heading{display:block}.candidates{grid-template-columns:1fr}.actions{grid-template-columns:1fr}.strategy-tabs{overflow:auto}.strategy-tabs button{white-space:nowrap}}
</style></head><body>
<header><div><h1>故事候选审批</h1><div class="sub">12 个概念 · 3 种映射策略 · 每种 3 个候选</div></div><div id="headerStatus" class="sub">加载中</div></header>
<div class="layout"><aside><div class="filters"><div><label>搜索</label><input id="query" placeholder="概念名或 ID"></div><div class="filter-row"><div><label>学科</label><select id="subject"><option value="">全部</option></select></div><div><label>审核</label><select id="reviewFilter"><option value="">全部</option><option value="pending">有待审</option><option value="approve">有批准</option><option value="reject">有拒绝</option></select></div></div><div><label>Judge</label><select id="judgeFilter"><option value="">全部</option><option value="accept">Accept</option><option value="revise">Revise</option><option value="reject">Reject</option></select></div></div><div id="stats" class="stats"></div><div id="list" class="list"></div></aside><main id="detail"><div class="empty-page">加载故事候选中</div></main></div>
<script>
let app={concepts:[],status:{},strategies:[],selected:null,strategy:'standard'};const $=id=>document.getElementById(id),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function candidates(c){return(c.candidates||[]).filter(x=>x.strategy===app.strategy)}function reviewState(x){return x.review?.decision||'pending'}function selectedConcept(){return app.concepts.find(x=>x.concept_id===app.selected)}
function filtered(){const q=$('query').value.trim().toLowerCase(),subject=$('subject').value,rf=$('reviewFilter').value,jf=$('judgeFilter').value;return app.concepts.filter(c=>{const pool=candidates(c),hay=`${c.seed.canonical_name||''} ${c.concept_id}`.toLowerCase();return(!q||hay.includes(q))&&(!subject||c.seed.subject===subject)&&(!rf||pool.some(x=>reviewState(x)===rf))&&(!jf||pool.some(x=>x.final_status?.judge_status===jf))})}
function badge(value,label){return`<span class="badge ${esc(value)}">${esc(label||value)}</span>`}function pct(x){return`${Math.round(Number(x||0)*100)}%`}function candidateCounts(c){const pool=candidates(c),reviewed=pool.filter(x=>reviewState(x)!=='pending').length,accepted=pool.filter(x=>x.final_status?.judge_status==='accept').length;return`${reviewed}/3 已审 · ${accepted}/3 A`}
function renderList(){const rows=filtered();$('list').innerHTML=rows.map(c=>`<button class="concept ${c.concept_id===app.selected?'active':''}" data-id="${esc(c.concept_id)}"><div class="concept-title"><span>${esc(c.seed.canonical_name)}</span><span class="count">${candidateCounts(c)}</span></div><div class="meta">${esc(c.seed.subject)} · ${esc(c.concept_id)}</div></button>`).join('')||'<div class="empty-page">无匹配概念</div>';document.querySelectorAll('.concept').forEach(x=>x.onclick=()=>{app.selected=x.dataset.id;renderList();renderDetail()})}
function renderStats(){const s=app.status;$('stats').innerHTML=`<div class="stat"><b>${s.pending_count||0}</b>待审</div><div class="stat"><b>${s.approved_count||0}</b>批准</div><div class="stat"><b>${s.preferred_count||0}</b>首选</div>`;$('headerStatus').textContent=`${s.reviewed_count||0}/${s.story_count||0} 已审 · ${s.rejected_count||0} 拒绝`}
function mechanismBand(c){const g=c.mechanism_graph||{},nodes=Object.fromEntries((g.nodes||[]).map(n=>[n.id,n]));return`<div class="mechanism">${(g.nodes||[]).map(n=>`<span><b>${esc(n.id)}</b> ${esc(n.text)} <small>${esc(n.type)}</small></span>`).join('')}${(g.edges||[]).map(e=>`<span><b>${esc(e.id)}</b> ${esc(nodes[e.source]?.text||e.source)} ${esc(e.relation)} ${esc(nodes[e.target]?.text||e.target)}</span>`).join('')}</div>`}
function mappingDetail(x){const p=x.mapping_plan||{},a=x.alignment||{};return`<details><summary>映射与对齐证据</summary><div class="detail-body"><b>故事域：${esc(p.source_domain||'')}</b><div class="meta">${esc(p.conflict||'')}</div>${(p.node_mappings||[]).map(m=>{const evidence=(a.node_alignments||[]).find(y=>y.mechanism_node_id===m.mechanism_node_id)?.story_evidence||'未找到';return`<div class="mapping"><b>${esc(m.mechanism_node_id)} → ${esc(m.story_carrier)}</b><span>${esc(evidence)}</span></div>`}).join('')}${(p.edge_mappings||[]).map(m=>{const evidence=(a.edge_alignments||[]).find(y=>y.mechanism_edge_id===m.mechanism_edge_id)?.story_evidence||'未找到';return`<div class="mapping edge"><b>${esc(m.mechanism_edge_id)} → ${esc(m.story_relation)}</b><span>${esc(evidence)}</span></div>`}).join('')}</div></details>`}
function judgeDetail(x){const j=x.judgment||{},scores=j.scores||{},diagnosis=j.mapping_diagnosis||{};return`<details><summary>Judge 诊断</summary><div class="detail-body"><div class="score-grid">${Object.entries(scores).map(([k,v])=>`<div class="score"><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join('')}</div><div class="diagnosis"><b>区分依据</b><br>${esc(diagnosis.distinguishing_reason||'')}</div><div class="diagnosis"><b>修订意见</b><br>${esc((j.revision_instructions||[]).join('；'))}</div></div></details>`}
function candidateCard(c,x){const f=x.final_status||{},m=x.metrics||{},r=x.review||{},preferred=r.decision==='approve'&&r.preferred,source=f.selected_source==='revision_001'?'修订稿':'初稿';return`<article class="candidate ${preferred?'preferred':''}"><div class="candidate-head"><div class="candidate-title"><span>${esc(x.candidate_id.replace('candidate_','候选 '))}</span><span>${badge(f.judge_status||'pending',String(f.judge_status||'pending').toUpperCase())}</span></div><div class="badges">${badge('source',source)}${badge(reviewState(x),reviewState(x)==='approve'?'已批准':reviewState(x)==='reject'?'已拒绝':'待审')}${preferred?badge('preferred-badge','首选'):''}</div></div><div class="metrics"><div class="metric"><b>${pct(m.node_coverage)}</b>节点</div><div class="metric"><b>${pct(m.edge_coverage)}</b>边</div><div class="metric"><b>${pct(m.direction_accuracy)}</b>方向</div></div><div class="story ${x.story?'':'empty'}">${esc(x.story||'最终故事缺失')}</div>${mappingDetail(x)}${judgeDetail(x)}<div class="review"><div class="review-grid"><div><label>审核人</label><input id="reviewer-${esc(x.candidate_id)}" value="${esc(r.reviewer||localStorage.storyReviewer||'')}"></div><div><label>意见</label><textarea id="notes-${esc(x.candidate_id)}" rows="2">${esc(r.notes||'')}</textarea></div></div><div class="actions"><button class="reject-btn" onclick="save('${esc(x.candidate_id)}','reject',false)">拒绝</button><button class="approve-btn" onclick="save('${esc(x.candidate_id)}','approve',false)">批准</button><button class="preferred-btn" onclick="save('${esc(x.candidate_id)}','approve',true)">批准并设为首选</button></div><div class="notice" id="notice-${esc(x.candidate_id)}">${r.reviewed_at_utc?`上次审核 ${esc(r.reviewed_at_utc)}`:''}</div></div></article>`}
function renderDetail(){const c=selectedConcept();if(!c){$('detail').innerHTML='<div class="empty-page">从左侧选择一个概念</div>';return}const tabs=app.strategies.map(s=>`<button class="${s.id===app.strategy?'active':''}" data-strategy="${esc(s.id)}">${esc(s.label)}</button>`).join('');$('detail').innerHTML=`<div class="heading"><div><h2>${esc(c.seed.canonical_name)}</h2><div class="definition">${esc(c.seed.definition||'')}</div></div><div class="meta">${esc(c.concept_id)} · ${esc(c.seed.subject)} · ${esc(c.seed.concept_type)}</div></div>${mechanismBand(c)}<div class="strategy-tabs">${tabs}</div><div class="candidates">${candidates(c).map(x=>candidateCard(c,x)).join('')}</div>`;document.querySelectorAll('[data-strategy]').forEach(x=>x.onclick=()=>{app.strategy=x.dataset.strategy;renderList();renderDetail()})}
async function save(candidateId,decision,preferred){const c=selectedConcept(),reviewer=$(`reviewer-${candidateId}`).value.trim(),notes=$(`notes-${candidateId}`).value.trim(),notice=$(`notice-${candidateId}`);if(!reviewer){notice.textContent='请填写审核人';notice.className='notice error-text';return}localStorage.storyReviewer=reviewer;notice.textContent='保存中';try{const res=await fetch('/api/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({concept_id:c.concept_id,strategy:app.strategy,candidate_id:candidateId,decision,preferred,reviewer,notes})}),data=await res.json();if(!res.ok)throw new Error(data.error||'保存失败');await load(true);app.selected=c.concept_id;renderList();renderDetail();const n=$(`notice-${candidateId}`);if(n){n.textContent=preferred?'已批准并设为首选':decision==='approve'?'已批准':'已拒绝';n.className='notice ok-text'}}catch(e){notice.textContent=e.message;notice.className='notice error-text'}}
async function load(preserve=false){const oldSubject=$('subject').value,res=await fetch('/api/data'),data=await res.json();if(!res.ok)throw new Error(data.error||'加载失败');app.concepts=data.concepts;app.status=data.status;app.strategies=data.strategies;$('subject').innerHTML='<option value="">全部</option>'+[...new Set(app.concepts.map(c=>c.seed.subject))].sort().map(s=>`<option value="${esc(s)}">${esc(s)}</option>`).join('');if(preserve)$('subject').value=oldSubject;renderStats();if(!app.selected||!app.concepts.some(c=>c.concept_id===app.selected))app.selected=filtered()[0]?.concept_id||app.concepts[0]?.concept_id||null;renderList();renderDetail()}
['query','subject','reviewFilter','judgeFilter'].forEach(id=>$(id).addEventListener('input',()=>{if(!filtered().some(c=>c.concept_id===app.selected))app.selected=filtered()[0]?.concept_id||null;renderList();renderDetail()}));load().catch(e=>$('detail').innerHTML=`<div class="empty-page error-text">${esc(e.message)}</div>`);
</script></body></html>"""
