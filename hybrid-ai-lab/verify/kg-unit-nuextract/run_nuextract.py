"""약관 채우기 시험을 NuExtract 2.0 8B(Ollama, GGUF Q8_0)로 다시 돌림. gpt-oss-120b, Opus 5.5 시험과 같은 표본, 기대 답, 채점.

NuExtract는 스키마 설명 대신 JSON 틀(template)만 받으므로, 스키마 초안의 노드 5종을 틀 하나로 옮기고
돌려받은 JSON을 노드 기록으로 바꿔 fill_test.py의 score와 report로 셈.
- chunk: 청크째 5건(doc/output/regulation-chunk-run)
- unit: 조항 단위 30건(doc/regulation)
실행: (schema/doc/.venv)/python run_nuextract.py chunk|unit
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOC = HERE.parent.parent / "indexer/graphrag/schema/doc"
sys.path.insert(0, str(DOC / "tools"))

from common import load_chunks, load_json, load_units  # noqa: E402
from fill_test import head_line, report, score  # noqa: E402

MODEL = "hf.co/numind/NuExtract-2.0-8B-GGUF:Q8_0"
URL = "http://localhost:11434/api/generate"

# 스키마 초안(TermsDocument, Clause, Requirement, Deadline, Handling)을 틀 하나로 옮김. 이름이 설명을 대신하므로 뜻이 드러나게 지음
TEMPLATE = {
    "terms_document": {"version": "verbatim-string", "effective_date": "verbatim-string",
                       "supersedes_version": "verbatim-string"},
    "clauses": [{
        "clause_no": "verbatim-string",
        "clause_title": "verbatim-string",
        "eligibility_requirements_amount_period_count": ["verbatim-string"],
        "deadlines_and_notice_timing": ["verbatim-string"],
        "situation_handling": [{"situation": "verbatim-string", "action": "verbatim-string"}],
    }],
}


def prompt(text: str) -> str:
    """모델 카드의 대화 틀(chat_template.json)과 같은 글을 직접 만듦. Ollama 기본 틀을 거치지 않으려고 raw로 보냄."""

    return ("<|im_start|>system\nYou are NuExtract, an information extraction tool created by NuMind.<|im_end|>\n"
            "<|im_start|>user\n# Template:\n" + json.dumps(TEMPLATE, indent=4) + "\n# Context:\n" + text.strip()
            + "<|im_end|>\n<|im_start|>assistant\n")


def call(text: str) -> tuple[dict, dict]:
    body = {"model": MODEL, "prompt": prompt(text), "raw": True, "stream": False,
            "options": {"temperature": 0, "num_ctx": 16384, "num_predict": 6000}}  # 모델 카드 권고: 온도 0
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as resp:
        out = json.loads(resp.read().decode("utf-8"))
    return json.loads(out["response"]), {"prompt_tokens": out.get("prompt_eval_count", 0),
                                         "output_tokens": out.get("eval_count", 0)}


def to_record(cid: str, data: dict) -> dict:
    """NuExtract JSON을 fill_test 채점이 읽는 노드 기록으로 바꿈. 빈 값은 노드로 만들지 않음."""

    nodes, rels = [], []
    add = lambda label, props: nodes.append({"id": f"{cid}:{len(nodes)}", "label": label,
                                             "properties": {k: v for k, v in props.items() if v not in (None, "", [])}})
    td = data.get("terms_document") or {}
    if any(td.values()):
        add("TermsDocument", {"version": td.get("version"), "effective_date": td.get("effective_date"),
                              "supersedes": td.get("supersedes_version")})
    for c in data.get("clauses") or []:
        if not (c.get("clause_no") or c.get("clause_title")):
            continue
        add("Clause", {"clause_no": c.get("clause_no"), "title": c.get("clause_title")})
        for v in c.get("eligibility_requirements_amount_period_count") or []:
            if v:
                add("Requirement", {"description": v})
        for v in c.get("deadlines_and_notice_timing") or []:
            if v:
                add("Deadline", {"description": v})
        for h in c.get("situation_handling") or []:
            if h and (h.get("situation") or h.get("action")):
                add("Handling", {"situation": h.get("situation"), "action": h.get("action")})
    return {"chunk_id": cid, "raw_nodes": [n["label"] for n in nodes], "raw_rels": [], "nodes": nodes, "rels": rels}


def main(mode: str) -> None:
    base = DOC / ("output/regulation-chunk-run" if mode == "chunk" else "regulation")
    rd = lambda p: json.loads((base / p).read_text(encoding="utf-8"))
    spec, expected = rd("schema_spec.json"), rd("expected_answers.json")["answers"]
    criteria = load_json("pass_criteria.json")
    chunks = {c["id"]: c for c in (load_chunks() if mode == "chunk" else load_units())}
    usage, results = Counter(), []
    for cid in expected:  # GPU 하나라 한 건씩 차례로 부름
        t0 = time.time()
        text = head_line(chunks[cid]["metadata"], spec.get("metadata_header", [])) + chunks[cid]["text"]
        try:
            data, u = call(text)
            usage.update(u)
            rec = to_record(cid, data)
            rec["raw_json"] = data
        except Exception as e:  # 한 건 실패는 기록하고 계속함
            rec = {"chunk_id": cid, "error": f"{type(e).__name__}: {str(e)[:300]}"}
        rec["seconds"] = round(time.time() - t0, 1)
        results.append(rec)
        print(cid, rec["seconds"], "s", dict(Counter(n["label"] for n in rec.get("nodes", []))), rec.get("error", ""),
              flush=True)
    usage["total_tokens"] = usage["prompt_tokens"] + usage["output_tokens"]
    out = HERE / f"output-{mode}"
    out.mkdir(exist_ok=True)
    with (out / "fill_calls.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    sc = score("regulation", results, expected, spec["cq_map"], criteria)
    text = report("regulation", 1, results, sc, criteria, chunks, dict(usage))
    text = text.replace("모델 openai/gpt-oss-120b", f"모델 {MODEL}(온도 0)")
    (out / "fill_report.md").write_text(text, encoding="utf-8")
    (out / "fill_metrics.json").write_text(json.dumps(sc["metrics"], ensure_ascii=False, indent=2), encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main(sys.argv[1])
