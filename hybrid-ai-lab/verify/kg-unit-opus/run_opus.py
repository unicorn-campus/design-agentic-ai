"""약관 추출 단위 비교를 Claude Opus 5.5로 다시 돌림(gpt-oss-120b 결과와 같은 표본, 스키마 초안, 기대 답, 채점).

- chunk: 청크째(1차 시험 재현). 입력은 doc/output/regulation-chunk-run의 스키마 초안, 기대 답, 질문 매핑
- unit: 조항 단위(2차 시험 재현). 입력은 doc/regulation의 스키마 초안, 기대 답, 질문 매핑
채점과 추출 절차는 schema/doc/tools/fill_test.py 함수를 그대로 씀. 바꾼 것은 LLM 하나뿐임.
실행: {venv}/python run_opus.py chunk|unit
"""

from __future__ import annotations

import asyncio
import copy
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Optional

HERE = Path(__file__).resolve().parent
DOC = HERE.parent.parent / "indexer/graphrag/schema/doc"
sys.path.insert(0, str(DOC / "tools"))

import anthropic  # noqa: E402
from neo4j_graphrag.components.entity_relation_extractor import LLMEntityRelationExtractor, OnError  # noqa: E402
from neo4j_graphrag.components.graph_pruning import GraphPruning  # noqa: E402
from neo4j_graphrag.components.schema import GraphSchema  # noqa: E402
from neo4j_graphrag.llm import LLMInterface, LLMResponse  # noqa: E402

from common import GraphSafeLLM, decisions, load_chunks, load_json, load_units, read_secret  # noqa: E402
from fill_test import extract_one, head_line, report, score  # noqa: E402

MODEL = "claude-opus-5-5"
EFFORT = "medium"  # Opus 5.5 기본값. 온도는 이 모델에서 받지 않음(400)


class OpusLLM(LLMInterface):
    """Anthropic SDK로 Opus 5.5를 부름. 응답의 코드 울타리를 벗기고 그래프 꼴로 다듬음(GraphSafeLLM과 같은 다듬기)."""

    _value = staticmethod(GraphSafeLLM._value)  # _clean이 부르는 값 다듬기

    def __init__(self, api_key: str) -> None:
        super().__init__(model_name=MODEL)
        self._client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=4, timeout=300)
        self.usage = Counter()

    def invoke(self, input: str, message_history: Optional[Any] = None,
               system_instruction: Optional[str] = None) -> LLMResponse:
        return asyncio.run(self.ainvoke(input, message_history, system_instruction))

    async def ainvoke(self, input: str, message_history: Optional[Any] = None,
                      system_instruction: Optional[str] = None) -> LLMResponse:
        kw = {"system": system_instruction} if system_instruction else {}
        msg = await self._client.beta.messages.create(
            model=MODEL, max_tokens=32000, output_config={"effort": EFFORT},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            messages=[{"role": "user", "content": input + "\n\nReturn only the JSON object, no code fences."}], **kw)
        if msg.stop_reason == "refusal":
            raise RuntimeError(f"refusal: {msg.stop_details}")
        if msg.stop_reason == "max_tokens":
            raise RuntimeError("max_tokens에 걸려 응답이 잘림")
        self.usage["input_tokens"] += msg.usage.input_tokens
        self.usage["output_tokens"] += msg.usage.output_tokens
        self.usage["total_tokens"] += msg.usage.input_tokens + msg.usage.output_tokens
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
        return LLMResponse(content=GraphSafeLLM._clean(self, text))


async def main(mode: str) -> None:
    base = DOC / ("output/regulation-chunk-run" if mode == "chunk" else "regulation")
    rd = lambda p: json.loads((base / p).read_text(encoding="utf-8"))
    spec, draft, expected = rd("schema_spec.json"), rd("output/schema_draft.json"), rd("expected_answers.json")["answers"]
    schema = GraphSchema.model_validate(copy.deepcopy(draft))
    criteria = load_json("pass_criteria.json")
    source = load_chunks() if mode == "chunk" else load_units()
    chunks = {c["id"]: c for c in source}
    d = decisions()["input"]
    llm = OpusLLM(read_secret(d["secret_file"], "CLAUDE_API_KEY"))
    extractor = LLMEntityRelationExtractor(llm=llm, create_lexical_graph=False, on_error=OnError.RAISE)
    sem = asyncio.Semaphore(4)
    results = await asyncio.gather(*[
        extract_one(sem, extractor, GraphPruning(), schema, cid,
                    head_line(chunks[cid]["metadata"], spec.get("metadata_header", [])) + chunks[cid]["text"])
        for cid in expected])
    out = HERE / f"output-{mode}"
    out.mkdir(exist_ok=True)
    with (out / "fill_calls.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    sc = score("regulation", results, expected, spec["cq_map"], criteria)
    text = report("regulation", 1, results, sc, criteria, chunks, dict(llm.usage))
    text = text.replace(f"모델 {d['llm_model']}", f"모델 {MODEL}(effort {EFFORT})")
    (out / "fill_report.md").write_text(text, encoding="utf-8")
    (out / "fill_metrics.json").write_text(json.dumps(sc["metrics"], ensure_ascii=False, indent=2), encoding="utf-8")
    print(text)
    for r in results:
        print(r["chunk_id"], dict(Counter(n["label"] for n in r.get("nodes", []))), r.get("error", ""))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
