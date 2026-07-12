from __future__ import annotations

import argparse
import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from kg_rag.concepts.jsonl import read_jsonl
from kg_rag.io import read_json
from kg_rag.m2na_v2.mapping_review_app import serve_mapping_review_app
from kg_rag.m2na_v2.review_app import serve_review_app
from kg_rag.m2na_v2.reviews import pipeline_status
from kg_rag.paths import DEFAULT_DERIVED_DIR
from kg_rag.story_pilot.review_app import serve_story_review_app


DEFAULT_PREPARATION_ROOT = DEFAULT_DERIVED_DIR / "kg_rag" / "m2na_v2" / "pilot80"
DEFAULT_PILOT_ROOT = DEFAULT_DERIVED_DIR / "kg_rag" / "story_pilot12"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
VISUALIZATION_ROOTS = {
    "global": PROJECT_ROOT / "data" / "visualization" / "global_kg",
    "concept": PROJECT_ROOT / "data" / "visualization" / "concept_kg",
}


class HubState:
    def __init__(self, *, preparation_root: Path, pilot_root: Path) -> None:
        self.preparation_root = preparation_root
        self.pilot_root = pilot_root

    @property
    def seeds_path(self) -> Path:
        return self.preparation_root / "seeds.jsonl"

    def dashboard(self) -> dict[str, Any]:
        preparation = pipeline_status(seeds_path=self.seeds_path, output_root=self.preparation_root)
        return {
            "preparation": preparation,
            "guided_mapping": _guided_summary(self.pilot_root),
            "stories": _story_summary(self.pilot_root),
        }

    def guided_mappings(self) -> dict[str, Any]:
        seeds = {str(item["concept_id"]): item for item in read_jsonl(self.seeds_path)}
        rows: list[dict[str, Any]] = []
        guided_root = self.pilot_root / "guided_mappings"
        for item in read_jsonl(self.pilot_root / "guided_mapping_index.jsonl"):
            concept_id = str(item["concept_id"])
            concept_dir = guided_root / concept_id
            evaluation = _safe_json(concept_dir / "candidate_evaluations.json")
            selected = _safe_json(concept_dir / "selected_mapping_plan.json")
            candidates = evaluation if isinstance(evaluation, list) else evaluation.get("candidates", [])
            rows.append(
                {
                    "concept_id": concept_id,
                    "seed": seeds.get(concept_id, {}),
                    "selected_candidate_id": item.get("selected_candidate_id"),
                    "selected_plan": selected,
                    "candidates": candidates,
                }
            )
        return {"summary": _guided_summary(self.pilot_root), "rows": rows}

def serve_hub(
    *,
    preparation_root: Path,
    pilot_root: Path,
    host: str,
    port: int,
    mechanism_port: int,
    mapping_port: int,
    story_port: int,
) -> ThreadingHTTPServer:
    state = HubState(preparation_root=preparation_root, pilot_root=pilot_root)
    _start_embedded_servers(
        preparation_root=preparation_root,
        pilot_root=pilot_root,
        host=host,
        mechanism_port=mechanism_port,
        mapping_port=mapping_port,
        story_port=story_port,
    )
    return ThreadingHTTPServer((host, port), _handler_for(state, mechanism_port, mapping_port, story_port))


def _start_embedded_servers(
    *,
    preparation_root: Path,
    pilot_root: Path,
    host: str,
    mechanism_port: int,
    mapping_port: int,
    story_port: int,
) -> None:
    servers = (
        serve_review_app(seeds_path=preparation_root / "seeds.jsonl", output_root=preparation_root, host=host, port=mechanism_port),
        serve_mapping_review_app(
            mapping_root=preparation_root / "mapping_plans",
            seeds_path=preparation_root / "seeds.jsonl",
            host=host,
            port=mapping_port,
        ),
        serve_story_review_app(pilot_root=pilot_root, host=host, port=story_port),
    )
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()


def _handler_for(state: HubState, mechanism_port: int, mapping_port: int, story_port: int) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/":
                self._send_html(_html(mechanism_port, mapping_port, story_port))
            elif path == "/api/dashboard":
                self._send_json(state.dashboard())
            elif path == "/api/guided-mappings":
                self._send_json(state.guided_mappings())
            elif path.startswith("/visualizations/"):
                self._send_visualization_asset(path)
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_html(self, value: str) -> None:
            payload = value.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_json(self, value: Any) -> None:
            payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_visualization_asset(self, path: str) -> None:
            parts = [part for part in path.split("/") if part]
            if len(parts) not in {2, 3} or parts[0] != "visualizations":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            root = VISUALIZATION_ROOTS.get(parts[1])
            asset = "index.html" if len(parts) == 2 else parts[2]
            if root is None or asset not in {"index.html", "graphdata.js"}:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            file_path = root / asset
            if not file_path.exists():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            payload = file_path.read_bytes()
            content_type = "text/html; charset=utf-8" if asset.endswith(".html") else "application/javascript; charset=utf-8"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return Handler


def _safe_json(path: Path) -> Any:
    return read_json(path) if path.exists() else {}


def _guided_summary(pilot_root: Path) -> dict[str, int]:
    rows = read_jsonl(pilot_root / "guided_mapping_index.jsonl")
    failures = read_jsonl(pilot_root / "guided_mapping_failures.jsonl")
    return {"completed": len(rows), "failed": len(failures)}


def _story_summary(pilot_root: Path) -> dict[str, int]:
    rows = read_jsonl(pilot_root / "final_story_status.jsonl")
    accepted = sum(1 for item in rows if item.get("judge_status") == "accept")
    invalid = sum(1 for item in rows if item.get("invalid_for_official_eval"))
    return {"completed": len(rows), "accepted": accepted, "invalid": invalid}


def _html(mechanism_port: int, mapping_port: int, story_port: int) -> str:
    return _HTML.replace("__MECHANISM_PORT__", str(mechanism_port)).replace("__MAPPING_PORT__", str(mapping_port)).replace("__STORY_PORT__", str(story_port))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the integrated M2NA V2 experiment review workspace.")
    parser.add_argument("--preparation-root", type=Path, default=DEFAULT_PREPARATION_ROOT)
    parser.add_argument("--pilot-root", type=Path, default=DEFAULT_PILOT_ROOT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8769)
    parser.add_argument("--mechanism-port", type=int, default=8770)
    parser.add_argument("--mapping-port", type=int, default=8771)
    parser.add_argument("--story-port", type=int, default=8772)
    args = parser.parse_args(argv)
    server = serve_hub(**vars(args))
    print(f"Experiment Hub: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


_HTML = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M2NA 实验工作台</title>
<style>
:root{--ink:#17242b;--muted:#66757e;--paper:#eef2f3;--panel:#fff;--line:#d7e0e3;--teal:#087a73;--navy:#17343c;--blue:#2b68aa;--green:#18724b;--amber:#a76400}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.5 "Segoe UI","Microsoft YaHei",sans-serif}button,input{font:inherit}button{cursor:pointer}.top{height:64px;display:flex;align-items:center;justify-content:space-between;padding:0 24px;background:var(--navy);color:#fff}.top h1{font-size:18px;margin:0}.top span{font-size:12px;color:#c2d3d6}.tabs{display:flex;gap:4px;padding:12px 24px 0;background:var(--paper);border-bottom:1px solid var(--line)}.tab{border:1px solid transparent;border-bottom:0;background:transparent;padding:10px 14px;border-radius:6px 6px 0 0;color:var(--muted)}.tab.active{background:#fff;border-color:var(--line);color:var(--teal);font-weight:700}.screen{height:calc(100vh - 112px)}.view{display:none;height:100%}.view.active{display:block}.dashboard{padding:24px;max-width:1180px;margin:auto}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.card{border:1px solid var(--line);background:var(--panel);padding:16px;border-radius:7px}.card h2{font-size:14px;margin:0 0 10px}.metric{font-size:28px;font-weight:700;color:var(--teal)}.caption{font-size:12px;color:var(--muted)}.note{margin-top:18px;background:#f8fbfb;border:1px solid #d7e9e7;padding:14px;border-radius:6px;color:#355057}.frame{width:100%;height:100%;border:0;background:#fff}.guided{height:100%;display:grid;grid-template-columns:330px 1fr}.guided aside{overflow:auto;padding:16px;background:#fff;border-right:1px solid var(--line)}.guided main{overflow:auto;padding:24px}.guided input{width:100%;padding:8px;border:1px solid var(--line);border-radius:5px}.guided-list{display:grid;gap:6px;margin-top:12px}.guided-item{border:1px solid var(--line);background:#fff;text-align:left;padding:10px;border-radius:5px}.guided-item.active{border-color:var(--teal);box-shadow:inset 3px 0 var(--teal)}.meta{font-size:12px;color:var(--muted)}.guided-card{background:#fff;border:1px solid var(--line);padding:16px;border-radius:6px;margin-bottom:14px}.guided-card h2{margin:0 0 4px}.candidate{border-top:1px solid var(--line);padding:12px 0}.candidate:first-of-type{border-top:0}.score{display:inline-block;background:#e1f1f0;color:#075e59;padding:2px 7px;border-radius:999px;font-size:12px;font-weight:700}.empty{color:var(--muted);margin:80px auto;text-align:center}@media(max-width:800px){.top{padding:0 14px}.top span{display:none}.tabs{overflow:auto;padding-left:12px}.cards{grid-template-columns:repeat(2,1fr)}.guided{grid-template-columns:1fr;height:auto}.guided aside{border-right:0;border-bottom:1px solid var(--line);max-height:40vh}.screen{height:calc(100vh - 112px)}}
</style></head><body>
<header class="top"><div><h1>M2NA 实验工作台</h1><span>从机制证据到最终寓言故事的统一审核入口</span></div><span id="updated">正在读取实验状态</span></header>
<nav class="tabs"><button class="tab active" data-view="overview">总览</button><button class="tab" data-view="kg-global">K12 全局图谱</button><button class="tab" data-view="kg-concept">概念中心图谱</button><button class="tab" data-view="mechanisms">1. 概念机制审核</button><button class="tab" data-view="mappings">2. 结构映射审核</button><button class="tab" data-view="guided">3. LLM-guided Copycat</button><button class="tab" data-view="stories">4. 最终故事审核</button></nav>
<section class="screen"><div class="view active" id="overview"><div class="dashboard"><div class="cards" id="cards"></div><div class="note">审核动作仍由原有页面执行，并且继续写入原有的追加式 JSONL 审核记录。此工作台只统一入口和状态，不改变实验数据或审核规则。</div></div></div><div class="view" id="kg-global"><iframe class="frame" src="/visualizations/global/"></iframe></div><div class="view" id="kg-concept"><iframe class="frame" src="/visualizations/concept/"></iframe></div><div class="view" id="mechanisms"><iframe class="frame" src="http://127.0.0.1:__MECHANISM_PORT__/"></iframe></div><div class="view" id="mappings"><iframe class="frame" src="http://127.0.0.1:__MAPPING_PORT__/"></iframe></div><div class="view" id="guided"><div class="guided"><aside><input id="guidedQuery" placeholder="搜索概念名称或 ID"><div id="guidedList" class="guided-list"></div></aside><main id="guidedDetail"><div class="empty">正在读取 LLM-guided Copycat 结果</div></main></div></div><div class="view" id="stories"><iframe class="frame" src="http://127.0.0.1:__STORY_PORT__/"></iframe></div></section>
<script>
const app={guided:[],selected:null};const $=id=>document.getElementById(id);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function show(id){document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.dataset.view===id));document.querySelectorAll('.view').forEach(x=>x.classList.toggle('active',x.id===id));}document.querySelectorAll('.tab').forEach(x=>x.onclick=()=>show(x.dataset.view));
function card(name,value,caption){return `<article class="card"><h2>${name}</h2><div class="metric">${value}</div><div class="caption">${caption}</div></article>`}async function loadDashboard(){const d=await (await fetch('/api/dashboard')).json(),p=d.preparation,g=d.guided_mapping,s=d.stories;$('cards').innerHTML=card('ConceptSeed',`${p.seed_count||0} / 80`,'已冻结的试点概念')+card('概念机制图',`${p.approved_count||0} 已批准` ,`${p.valid_count||0} 条规则有效`) +card('LLM-guided 映射',`${g.completed||0} / 12`,`${g.failed||0} 条构建失败`) +card('最终故事',`${s.completed||0} / 108`,`${s.accepted||0} 条自动通过，${s.invalid||0} 条无效`);$('updated').textContent='状态已更新';}
function candidates(row){const data=row.candidates||[];return data.map((x,i)=>{const plan=x.mapping_plan||x.plan||x;const score=x.score??x.total_score??plan.score??'--';const mappings=plan.node_mappings||plan.mappings||[];return `<div class="candidate"><b>候选 ${esc(x.candidate_id||i+1)}</b> ${String(x.candidate_id||'')===String(row.selected_candidate_id)?'<span class="score">已选中</span>':''}<span class="score">结构分 ${esc(score)}</span><div class="meta">${esc(x.rationale||plan.rationale||'无额外说明')}</div><div class="meta">节点映射 ${esc(Array.isArray(mappings)?mappings.length:0)} 条</div></div>`}).join('')||'<div class="empty">没有候选映射数据</div>'}
function filteredGuided(){const q=$('guidedQuery').value.trim().toLowerCase();return app.guided.filter(x=>`${x.concept_id} ${x.seed.canonical_name||''}`.toLowerCase().includes(q));}function renderGuided(){const rows=filteredGuided();if(!rows.some(x=>x.concept_id===app.selected))app.selected=rows[0]?.concept_id||null;$('guidedList').innerHTML=rows.map(x=>`<button class="guided-item ${x.concept_id===app.selected?'active':''}" data-id="${esc(x.concept_id)}"><b>${esc(x.seed.canonical_name||x.concept_id)}</b><div class="meta">${esc(x.seed.subject||'')} · ${esc(x.concept_id)}</div></button>`).join('')||'<div class="empty">无匹配概念</div>';document.querySelectorAll('.guided-item').forEach(x=>x.onclick=()=>{app.selected=x.dataset.id;renderGuided();});const row=app.guided.find(x=>x.concept_id===app.selected);$('guidedDetail').innerHTML=row?`<article class="guided-card"><h2>${esc(row.seed.canonical_name||row.concept_id)}</h2><div class="meta">${esc(row.concept_id)} · ${esc(row.seed.subject||'')}</div><p>${esc(row.seed.definition||'')}</p><h3>LLM-guided Copycat 候选</h3>${candidates(row)}</article>`:'<div class="empty">选择一个概念查看结果</div>';}async function loadGuided(){const d=await (await fetch('/api/guided-mappings')).json();app.guided=d.rows||[];renderGuided();}
$('guidedQuery').addEventListener('input',renderGuided);Promise.all([loadDashboard(),loadGuided()]).catch(e=>{$('updated').textContent=`读取失败: ${e.message}`});
</script></body></html>"""
