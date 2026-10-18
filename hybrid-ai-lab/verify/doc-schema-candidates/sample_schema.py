"""문서 종류별 표본으로 그래프 스키마 후보를 뽑는 시험 스크립트(neo4j-graphrag SchemaFromTextExtractor + Groq).

표본 규칙(대화에서 제안한 절차):
  - 층마다 시작 수만큼 먼저 보고, 그 뒤 1건씩 더 봄. 새 노드 타입이나 새 관계가 0개인 상태가 연속 3건이면 멈춤. 층 상한 30건
  - 약관(10청크): 상한보다 적어 전부 봄
  - 상담 이력(48건): 세그먼트(원천 파일) 6개에서 2건씩 12건으로 시작, 이후 세그먼트를 돌아가며 1건씩 추가
  - 혜택 안내(160청크): 청크 성격(카드 개요, 혜택 상세, 참고 카드, 공통 안내)으로 층을 나눠 층마다 10건으로 시작
표본 단위는 기존 벡터 인덱스의 청크(정제, 가명처리 뒤 글)임. 1건마다 LLM을 한 번 불러 "새 타입이 몇 개 늘었는지"를 셈.

실행(검증 가상환경): ../neo4j-vector-search/.venv/Scripts/python sample_schema.py [--examples] [문서종류 ...]
  --examples: 앞서 나온 이름을 다음 호출의 examples로 넘김(출력 output-examples/, 멈춤 규칙 없이 층 상한까지)
  --chunks=경로: 다른 세대의 prepared-chunks.json으로 돌림, --out=폴더: 출력 폴더 이름
  --cq: 문서 종류별 역량 질문(COMPETENCY_QUESTIONS)을 examples 앞에 넣음(현재 상담 이력만 정의)
  --no-stop: --examples 없이도 멈춤 규칙 없이 층 상한까지 봄(비교용)
입력: ../../indexer/vector-bm25/data/artifacts/ch2-20261003-001/prepared-chunks.json (읽기만 함)
비밀값: ../../.env 또는 프로젝트 루트 .env의 GROQ_API_KEY(값은 출력하지 않음)
출력: output/calls.jsonl(호출마다 결과), output/candidates_{문서종류}.json, output/summary.md
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Optional

from neo4j_graphrag.components.schema import SchemaFromTextExtractor
from neo4j_graphrag.llm import LLMInterface, LLMResponse

ROOT = Path(__file__).resolve().parent
LAB = ROOT.parent.parent
CHUNKS = LAB / "indexer/vector-bm25/data/artifacts/ch2-20261003-001/prepared-chunks.json"
OUT = ROOT / "output"
MODEL = "openai/gpt-oss-120b"
SEED = 20261018
START, RUN_LENGTH, CAP = 10, 3, 30


def read_env_key(name: str) -> str:
    """hybrid-ai-lab/.env를 먼저 보고, 없으면 프로젝트 루트 .env를 봄(2026-10-18 기준 키는 루트에만 있음)."""

    for env in (LAB / ".env", LAB.parent / ".env"):
        if not env.exists():
            continue
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(f"{name}="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                if value:
                    return value
    raise SystemExit(f"{LAB / '.env'} 또는 {LAB.parent / '.env'}에 {name} 값이 없음")


class GroqHttpLLM(LLMInterface):
    """Groq OpenAI 호환 API를 표준 라이브러리 HTTP로 부르는 LLM(JSON 모드).

    groq 패키지 대신 쓰는 이유: 검증 가상환경에 새 패키지를 설치하지 않기 위함.
    호출 하나의 전체 마감은 asyncio.wait_for로 따로 둠(소켓 timeout은 단계별이라 최악 시간을 보장하지 못함).
    """

    def __init__(self, model_name: str, api_key: str, timeout: float = 90.0, deadline: float = 240.0) -> None:
        super().__init__(model_name=model_name)
        self._key, self._timeout, self._deadline = api_key, timeout, deadline
        self.usage = Counter()

    def _post(self, body: bytes) -> dict:
        request = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=body, headers={
            "Authorization": f"Bearer {self._key}", "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "doc-schema-candidates/1.0"})
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def invoke(self, input: str, message_history: Optional[Any] = None,
               system_instruction: Optional[str] = None) -> LLMResponse:
        messages = ([{"role": "system", "content": system_instruction}] if system_instruction else [])
        messages.append({"role": "user", "content": input})
        body = json.dumps({"model": self.model_name, "messages": messages, "response_format": {"type": "json_object"},
                           "include_reasoning": False, "reasoning_effort": "medium", "temperature": 0},
                          ensure_ascii=False).encode("utf-8")
        for attempt in range(6):
            try:
                payload = self._post(body)
                for k, v in (payload.get("usage") or {}).items():
                    if isinstance(v, (int, float)):
                        self.usage[k] += v
                return LLMResponse(content=payload["choices"][0]["message"]["content"])
            except urllib.error.HTTPError as e:
                # 429(분당 토큰 한도)와 5xx만 기다렸다 다시 함. 다른 오류는 바로 실패로 기록
                if e.code != 429 and e.code < 500:
                    raise RuntimeError(f"Groq HTTP {e.code}: {e.read()[:300]!r}") from e
                wait = float(e.headers.get("retry-after") or 0) or min(60, 5 * 2 ** attempt)
                time.sleep(min(wait, 90))
        raise RuntimeError("Groq 재시도 6회 모두 실패")

    async def ainvoke(self, input: str, message_history: Optional[Any] = None,
                      system_instruction: Optional[str] = None) -> LLMResponse:
        return await asyncio.wait_for(asyncio.to_thread(self.invoke, input, message_history, system_instruction),
                                      timeout=self._deadline)


def key(label: str) -> str:
    """같은 이름의 대소문자, 띄어쓰기, 밑줄 차이를 한 이름으로 봄(뜻이 같은 다른 이름은 사람이 합침)."""

    return re.sub(r"[^0-9a-z가-힣]", "", label.lower())


def benefit_kind(md: dict) -> str:
    label = md.get("section_label") or ""
    if not label:
        return "공통 안내"
    if "참고 카드" in label:
        return "참고 카드"
    if re.search(r"-B\d+", label):
        return "혜택 상세"
    return "카드 개요"


def build_plans(rows: list[dict]) -> dict[str, list[tuple[str, list[dict], int]]]:
    """문서 종류마다 (층 이름, 보는 순서대로 정렬한 청크, 시작 수) 목록을 만듦."""

    rng = random.Random(SEED)
    by_type = defaultdict(list)
    for r in rows:
        by_type[r["metadata"]["doc_type"]].append(r)
    plans = {}
    reg = by_type["regulation"][:]
    rng.shuffle(reg)
    plans["regulation"] = [("약관 전체", reg, len(reg))]

    segs = defaultdict(list)
    for r in by_type["consult_log"]:
        segs[r["metadata"]["source"]].append(r)
    for v in segs.values():
        rng.shuffle(v)
    names = sorted(segs)
    order = [segs[n][i] for i in range(2) for n in names]  # 세그먼트마다 2건씩
    order += [segs[n][i] for i in range(2, max(len(v) for v in segs.values())) for n in names if i < len(segs[n])]
    plans["consult_log"] = [("상담 전체(세그먼트 균형)", order, 2 * len(names))]

    kinds = defaultdict(list)
    for r in by_type["benefit_guide"]:
        kinds[benefit_kind(r["metadata"])].append(r)
    plans["benefit_guide"] = []
    for name in sorted(kinds):
        v = kinds[name][:]
        rng.shuffle(v)
        plans["benefit_guide"].append((name, v, min(START, len(v))))
    return plans


class Vocab:
    """문서 종류 하나에서 지금까지 나온 이름과 빈도. examples 방식에서 다음 호출에 넘길 글을 만듦."""

    def __init__(self) -> None:
        self.nodes, self.rels, self.patterns, self.names = Counter(), Counter(), Counter(), {}

    def add(self, nodes: list[str], rels: list[str], patterns: list[list[str]]) -> None:
        for n in {key(x): x for x in nodes}.items():
            self.nodes[n[0]] += 1
            self.names.setdefault(n[0], n[1])
        for t in {key(x): x for x in rels}.items():
            self.rels[t[0]] += 1
            self.names.setdefault("r:" + t[0], t[1])
        for p in {tuple(p) for p in patterns}:
            self.patterns[p] += 1

    def examples(self, top_nodes: int = 25, top_rels: int = 30, top_patterns: int = 15) -> str:
        """빈도 순 상위만 넘김. 모두 넘기면 프롬프트가 길어지고 드문 잡음 이름까지 굳어짐."""

        if not self.nodes:
            return ""
        return ("Schema found so far in other samples of the same document type. Reuse these exact labels when the "
                "input text expresses the same concept. Add a new label only for a concept not covered here. "
                "Do not include labels that the input text does not support.\n"
                "Node types: " + ", ".join(self.names[k] for k, _ in self.nodes.most_common(top_nodes)) + "\n"
                "Relationship types: " + ", ".join(self.names["r:" + k] for k, _ in self.rels.most_common(top_rels))
                + "\nPatterns: " + ", ".join(f"({a})-[{r}]->({b})" for (a, r, b), _ in
                                            self.patterns.most_common(top_patterns)))


# 역량 질문: 스키마로 만든 그래프가 답해야 할 질문. 답이 될 타입 이름은 일부러 적지 않음(질문만으로 타입이 생기는지 보려고)
COMPETENCY_QUESTIONS = {
    "consult_log": [
        "고객이 말한 불만 원인은 무엇인가?",
        "상담사가 어떤 제안을 했는가?",
        "고객은 그 제안을 수용했는가, 거절했는가, 보류했는가? 그 이유는 무엇인가?",
        "고객은 어떤 조건이 되면 다시 검토하겠다고 했는가?",
        "이 상담은 같은 고객의 어떤 이전 상담과 이어지는가?",
    ],
    # 약관: 평가셋 문항(연회비 면제 조건, 해지 시 연회비 반환 등)이 답할 수 있어야 하는 범위
    "regulation": [
        "어떤 조건을 채우면 어떤 면제나 혜택을 받는가?",
        "회원이 해지, 철회, 항변 같은 요청을 하면 어떤 절차와 기한이 적용되는가?",
        "어떤 수수료나 비용이 어떤 경우에 부과되거나 공제되거나 돌려받는가?",
        "어떤 조항이 다른 조항을 참조하거나 예외를 두는가?",
        "회원과 카드사는 각각 어떤 의무를 지는가?",
    ],
    "benefit_guide": [
        "이 카드는 어떤 혜택을 주는가?",
        "혜택을 받으려면 전월 이용실적, 결제 채널, 가맹점 업종 같은 어떤 조건을 채워야 하는가?",
        "혜택의 한도와 제외 대상은 무엇인가?",
        "연회비는 얼마이며 브랜드에 따라 다른가?",
        "비슷한 혜택을 주는 다른 카드는 무엇인가?",
    ],
}


def cq_text(doc_type: str) -> str:
    qs = COMPETENCY_QUESTIONS.get(doc_type)
    if not qs:
        return ""
    return ("Competency questions: design node types, relationship types and properties so that a graph built with "
            "this schema can answer the following questions about documents like the input text.\n"
            + "\n".join(f"{i}. {q}" for i, q in enumerate(qs, 1)))


async def run_layer(extractor, doc_type: str, layer: str, chunks: list[dict], start: int, log,
                    vocab: Optional[Vocab] = None, early_stop: bool = True, cq: bool = False) -> dict:
    seen_nodes, seen_rels = set(), set()
    zero_run, used, stop = 0, 0, "모두 봄"
    for i, r in enumerate(chunks):
        if i >= CAP:
            stop = f"상한 {CAP}건"
            break
        if early_stop and i >= start and zero_run >= RUN_LENGTH:
            stop = f"연속 {RUN_LENGTH}건 새 타입 0개"
            break
        rec = {"doc_type": doc_type, "layer": layer, "order": i + 1, "chunk_id": r["chunk_id"],
               "section": r["metadata"].get("section_label") or r["metadata"].get("source")}
        t0 = time.time()
        try:
            parts = [cq_text(doc_type) if cq else "", vocab.examples() if vocab else ""]
            schema = await extractor.run(text=r["text"], examples="\n\n".join(p for p in parts if p))
            if vocab:
                vocab.add([n.label for n in schema.node_types], [t.label for t in schema.relationship_types],
                          [[p.source, p.relationship, p.target] for p in schema.patterns])
            nodes = [n.label for n in schema.node_types]
            rels = [t.label for t in schema.relationship_types]
            rec.update(nodes=nodes, relationships=rels,
                       node_props={n.label: [p.name for p in n.properties] for n in schema.node_types},
                       patterns=[[p.source, p.relationship, p.target] for p in schema.patterns])
            new_n = [n for n in nodes if key(n) not in seen_nodes]
            new_r = [t for t in rels if key(t) not in seen_rels]
            seen_nodes |= {key(n) for n in nodes}
            seen_rels |= {key(t) for t in rels}
            rec.update(new_nodes=new_n, new_relationships=new_r)
            zero_run = zero_run + 1 if not new_n and not new_r else 0
        except Exception as e:  # 한 건 실패는 기록만 하고 계속함. 실패 건은 새 타입 0개로 세지 않음
            rec["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        rec["seconds"] = round(time.time() - t0, 1)
        used = i + 1
        log.write(json.dumps(rec, ensure_ascii=False) + "\n")
        log.flush()
        print(f"[{doc_type}/{layer}] {i + 1}: 새 노드 {len(rec.get('new_nodes', []))}, "
              f"새 관계 {len(rec.get('new_relationships', []))}{' 오류' if 'error' in rec else ''}", flush=True)
    return {"layer": layer, "population": len(chunks), "start": start, "used": used, "stop": stop}


def summarize(calls: list[dict], layers: dict[str, list[dict]]) -> str:
    lines = ["# 문서 종류별 스키마 후보(자동 추출 결과, 사람 확정 전)", "",
             f"- 모델: Groq `{MODEL}`, 추출기: neo4j-graphrag `SchemaFromTextExtractor`(프롬프트 방식), 무작위 시드 {SEED}",
             f"- 멈춤 규칙: 시작 수를 본 뒤 새 노드 타입과 새 관계가 연속 {RUN_LENGTH}건 0개면 멈춤, 층 상한 {CAP}건", ""]
    for doc_type, ls in layers.items():
        rows = [c for c in calls if c["doc_type"] == doc_type]
        ok = [c for c in rows if "error" not in c]
        node_cnt, rel_cnt, pat_cnt = Counter(), Counter(), Counter()
        names = {}
        for c in ok:
            for n in set(c["nodes"]):
                node_cnt[key(n)] += 1
                names.setdefault(key(n), n)
            for t in set(c["relationships"]):
                rel_cnt[key(t)] += 1
                names.setdefault("r:" + key(t), t)
            for p in {tuple(p) for p in c["patterns"]}:
                pat_cnt[p] += 1
        lines += [f"## {doc_type}", "", "| 층 | 전체 | 시작 | 본 건수 | 멈춘 이유 |", "|---|---:|---:|---:|---|"]
        lines += [f"| {l['layer']} | {l['population']} | {l['start']} | {l['used']} | {l['stop']} |" for l in ls]
        lines += ["", f"- 호출 {len(rows)}건, 성공 {len(ok)}건, 실패 {len(rows) - len(ok)}건",
                  f"- 노드 타입 후보 {len(node_cnt)}개, 관계 후보 {len(rel_cnt)}개", "",
                  "노드 타입 후보(제안한 청크 수 순): " + ", ".join(f"{names[k]}({v})" for k, v in node_cnt.most_common()),
                  "", "관계 후보(제안한 청크 수 순): " + ", ".join(f"{names['r:' + k]}({v})" for k, v in rel_cnt.most_common()),
                  "", "자주 나온 패턴 상위 10: " + "; ".join(f"({a})-[{r}]->({b}) {v}" for (a, r, b), v in pat_cnt.most_common(10)),
                  ""]
        cand = {"doc_type": doc_type, "layers": ls, "node_types": [{"label": names[k], "chunks": v} for k, v in node_cnt.most_common()],
                "relationship_types": [{"label": names["r:" + k], "chunks": v} for k, v in rel_cnt.most_common()],
                "patterns": [{"pattern": list(p), "chunks": v} for p, v in pat_cnt.most_common()]}
        (OUT / f"candidates_{doc_type}.json").write_text(json.dumps(cand, ensure_ascii=False, indent=2), encoding="utf-8")
    return "\n".join(lines) + "\n"


async def main() -> None:
    global OUT
    args = sys.argv[1:]
    # --examples: 같은 문서 종류에서 앞서 나온 이름을 다음 호출의 examples로 넘김. 비교를 위해 멈춤 규칙 없이 상한까지 봄
    with_examples = "--examples" in args
    if with_examples:
        OUT = ROOT / "output-examples"
    opts = dict(a[2:].split("=", 1) for a in args if a.startswith("--") and "=" in a)
    chunks_path = Path(opts["chunks"]) if "chunks" in opts else CHUNKS  # 다시 인덱싱한 세대의 청크로 돌릴 때
    if "out" in opts:
        OUT = ROOT / opts["out"]
    data = json.loads(chunks_path.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else next(v for v in data.values() if isinstance(v, list))
    llm = GroqHttpLLM(MODEL, read_env_key("GROQ_API_KEY"))
    extractor = SchemaFromTextExtractor(llm=llm)
    OUT.mkdir(exist_ok=True)
    only = {a for a in args if not a.startswith("--")}  # 문서 종류를 골라 돌릴 때(예: regulation)
    print("청크:", chunks_path, "출력:", OUT, flush=True)
    layers = {}
    with (OUT / "calls.jsonl").open("w", encoding="utf-8") as log:
        for doc_type, plan in build_plans(rows).items():
            if only and doc_type not in only:
                continue
            vocab = Vocab() if with_examples else None  # 문서 종류마다 새로 시작(층끼리는 이어 씀)
            layers[doc_type] = [await run_layer(extractor, doc_type, name, chunks, start, log, vocab=vocab,
                                                early_stop=not (with_examples or "--no-stop" in args),
                                                cq="--cq" in args)
                                for name, chunks, start in plan]
    calls = [json.loads(l) for l in (OUT / "calls.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    (OUT / "summary.md").write_text(summarize(calls, layers), encoding="utf-8")
    (OUT / "layers.json").write_text(json.dumps(layers, ensure_ascii=False, indent=2), encoding="utf-8")
    print("토큰 사용:", dict(llm.usage))
    print("저장:", OUT / "summary.md")


if __name__ == "__main__":
    asyncio.run(main())
