"""2번 시험: 사람이 정한 뼈대(skeleton_consult_draft.json)를 스키마로 주고 상담 48건 전체에서 노드와 관계를 실제로 뽑아,
뼈대 타입이 채워지는지 강사용 대조표 정답과 비교함.

추출: neo4j-graphrag LLMEntityRelationExtractor(Groq gpt-oss-120b) → GraphPruning(뼈대 밖은 지움)
입력 글: v3 세대 청크 앞에 메타데이터 머리줄([상담ID], 상담일, 채널, 주제)을 붙임(Consultation 속성은 메타데이터로 채운다는 설계)
정답: _instructor/D3/상담근거_대조표.jsonl(complaint_cause, proposal, proposal_decision, hold_condition),
      정제검증_기대값.json(previous_record_id → FOLLOWS 정답)
실행: ../neo4j-vector-search/.venv/Scripts/python fill_skeleton.py [--skeleton=파일] [--out=폴더] → output-fill-v3/
"""

from __future__ import annotations

import asyncio
import copy
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

from neo4j_graphrag.components.entity_relation_extractor import LLMEntityRelationExtractor, OnError
from neo4j_graphrag.components.graph_pruning import GraphPruning
from neo4j_graphrag.components.schema import GraphSchema
from neo4j_graphrag.components.types import TextChunk, TextChunks

from sample_schema import MODEL, GroqHttpLLM, read_env_key

ROOT = Path(__file__).resolve().parent
LAB = ROOT.parent.parent
CHUNKS = LAB / "indexer/vector-bm25/data/artifacts/d3v3-20261018/prepared-chunks.json"
INST = LAB / "docs/_instructor/D3"
OUT = ROOT / "output-fill-v3"
# LLM이 수용, 거절, 보류를 영어나 다른 낱말로 적을 수 있어 정답과 비교할 때만 맞춤
DECISION = {"수용": ["수용", "accept", "agree", "동의", "승낙"], "거절": ["거절", "reject", "declin", "refus", "거부"],
            "보류": ["보류", "hold", "defer", "pending", "postpon", "유보", "재검토"]}


class SanitizingLLM(GroqHttpLLM):
    """추출 응답을 Neo4jGraph 꼴에 맞게 다듬음.

    왜 필요한가: Neo4jNode와 Neo4jRelationship은 정해진 칸 밖 키를 거부(extra="forbid")하고 id는 글자여야 함.
    LLM이 가끔 키를 더 넣거나 id를 숫자로, 속성 값을 null이나 객체로 적어 한 건 전체가 버려졌음(2026-10-18 실측).
    """

    @staticmethod
    def _value(v):
        if v is None:
            return None
        if isinstance(v, (str, int, float, bool)):
            return v
        if isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v):
            return v
        return json.dumps(v, ensure_ascii=False)

    def _clean(self, content: str) -> str:
        try:
            d = json.loads(content)
        except json.JSONDecodeError:
            return content
        nodes = [{"id": str(n.get("id")), "label": str(n.get("label")),
                  "properties": {k: self._value(v) for k, v in (n.get("properties") or {}).items() if self._value(v) is not None}}
                 for n in d.get("nodes", []) if isinstance(n, dict)]
        rels = [{"type": str(r.get("type")), "start_node_id": str(r.get("start_node_id")), "end_node_id": str(r.get("end_node_id")),
                 "properties": {k: self._value(v) for k, v in (r.get("properties") or {}).items() if self._value(v) is not None}}
                for r in d.get("relationships", []) if isinstance(r, dict)]
        return json.dumps({"nodes": nodes, "relationships": rels}, ensure_ascii=False)

    async def ainvoke(self, input, message_history=None, system_instruction=None):
        res = await super().ainvoke(input, message_history, system_instruction)
        res.content = self._clean(res.content)
        return res


def norm_decision(v) -> str | None:
    s = str(v or "").lower()
    for k, words in DECISION.items():
        if any(w in s for w in words):
            return k
    return None


async def main() -> None:
    global OUT
    # --skeleton=파일, --out=폴더: 뼈대 판을 바꿔 같은 시험을 다시 돌릴 때
    opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    skeleton = opts.get("skeleton", "skeleton_consult_draft.json")
    if "out" in opts:
        OUT = ROOT / opts["out"]
    raw = json.loads((ROOT / skeleton).read_text(encoding="utf-8"))
    raw.pop("_설명", None)
    schema = GraphSchema.model_validate(copy.deepcopy(raw))
    data = json.loads(CHUNKS.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else next(v for v in data.values() if isinstance(v, list))
    consult = [r for r in rows if r["metadata"]["doc_type"] == "consult_log"]
    gt = {r["record_id"]: r for r in map(json.loads, (INST / "상담근거_대조표.jsonl").read_text(encoding="utf-8").splitlines())}
    prev = {e["record_id"]: e["previous_record_id"]
            for e in json.loads((INST / "정제검증_기대값.json").read_text(encoding="utf-8"))}

    llm = SanitizingLLM(MODEL, read_env_key("GROQ_API_KEY"))
    extractor = LLMEntityRelationExtractor(llm=llm, create_lexical_graph=False, on_error=OnError.RAISE)
    pruner = GraphPruning()
    OUT.mkdir(exist_ok=True)
    results = []
    with (OUT / "fill_calls.jsonl").open("w", encoding="utf-8") as log:
        for i, r in enumerate(consult, 1):
            md = r["metadata"]
            rid = md["record_id"]
            head = f"[상담ID] {rid} | 상담일: {md['consult_date']} | 채널: {md['channel']} | 주제: {md['topic']}\n"
            rec = {"record_id": rid}
            t0 = time.time()
            try:
                for attempt in range(3):  # 형식 오류는 같은 입력으로 다시 부르면 대개 풀려서 2번까지 다시 함
                    try:
                        graph = await extractor.run(
                            chunks=TextChunks(chunks=[TextChunk(text=head + r["text"], index=0, uid=rid)]), schema=schema)
                        break
                    except Exception:
                        if attempt == 2:
                            raise
                        rec["retries"] = attempt + 1
                pruned = await pruner.run(graph, schema)
                g = pruned.graph
                rec.update(
                    raw_nodes=[n.label for n in graph.nodes], raw_rels=[x.type for x in graph.relationships],
                    nodes=[{"label": n.label, "properties": n.properties} for n in g.nodes],
                    rels=[{"type": x.type, "start": x.start_node_id, "end": x.end_node_id} for x in g.relationships],
                    node_ids={n.id: n.label for n in g.nodes})
            except Exception as e:  # 한 건 실패는 기록하고 계속함
                rec["error"] = f"{type(e).__name__}: {str(e)[:300]}"
            rec["seconds"] = round(time.time() - t0, 1)
            log.write(json.dumps(rec, ensure_ascii=False) + "\n")
            log.flush()
            results.append(rec)
            print(f"{i}/{len(consult)} {rid} {'오류' if 'error' in rec else len(rec['nodes'])}", flush=True)

    # 채점
    score = Counter()
    rows_out = []
    for rec in results:
        rid = rec["record_id"]
        g = gt[rid]
        if "error" in rec:
            score["실패"] += 1
            continue
        labels = Counter(n["label"] for n in rec["nodes"])
        rels = Counter(x["type"] for x in rec["rels"])
        decisions = {norm_decision(n["properties"].get("decision")) for n in rec["nodes"] if n["label"] == "Proposal"}
        want_c, want_h, want_f = bool(g.get("complaint_cause")), bool(g.get("hold_condition")), bool(prev.get(rid))
        has_c, has_h, has_f = labels["Complaint"] > 0, labels["ReconsiderCondition"] > 0, rels["FOLLOWS"] > 0
        for name, want, has in (("불만", want_c, has_c), ("재검토 조건", want_h, has_h), ("이전 상담 연결", want_f, has_f)):
            score[f"{name} {'정답 있음' if want else '정답 없음'} {'뽑음' if has else '안 뽑음'}"] += 1
        score["제안 뽑음" if labels["Proposal"] else "제안 안 뽑음"] += 1
        score["응답 일치" if g["proposal_decision"] in decisions else "응답 불일치"] += 1
        score["제안-불만 ADDRESSES 있음" if rels["ADDRESSES"] else "제안-불만 ADDRESSES 없음"] += 0 if not want_c else 1
        rows_out.append(f"| {rid} | {g['proposal_decision']} | {'O' if want_c else '-'}/{'O' if has_c else '-'} | "
                        f"{labels['Proposal']} | {', '.join(sorted(d for d in decisions if d)) or '-'} | "
                        f"{'O' if want_h else '-'}/{'O' if has_h else '-'} | {'O' if want_f else '-'}/{'O' if has_f else '-'} |")
    raw_extra = Counter(l for rec in results if "error" not in rec for l in rec["raw_nodes"]
                        if l not in {"Consultation", "Complaint", "Proposal", "ReconsiderCondition"})
    lines = ["# 뼈대 채우기 시험(상담 48건, v3 원문)", "",
             f"- 모델 {MODEL}, LLMEntityRelationExtractor + GraphPruning, 뼈대 `{skeleton}`", "",
             "| 항목 | 건수 |", "|---|---:|"] + [f"| {k} | {v} |" for k, v in sorted(score.items())] + [
             "", "- 가지치기로 지운 뼈대 밖 노드 라벨: " + (", ".join(f"{k}({v})" for k, v in raw_extra.most_common()) or "없음"),
             f"- 토큰: {dict(llm.usage).get('total_tokens')}", "",
             "| 상담ID | 정답 응답 | 불만 정답/뽑음 | 제안 수 | 뽑은 응답 | 조건 정답/뽑음 | 이전 상담 정답/뽑음 |",
             "|---|---|---|---:|---|---|---|"] + rows_out
    (OUT / "fill_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:30]))


if __name__ == "__main__":
    asyncio.run(main())
