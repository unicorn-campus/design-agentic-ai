"""8단계(v2): 채우기 시험과 연결 검사.

fill_test.py(문서 하나 범위 채점)를 그대로 쓰고 아래만 더함.
- 메타데이터 노드(CustomerSegment, PseudoMember)와 그 관계, 상담 HAS_TOPIC은 LLM 추출 스키마에서 빼고 코드가 메타데이터로 채움
  (5단계 설계: LLM이 본문에서 뽑지 않음). 그래서 채점에서도 이 관계는 빼고 연결 검사에서만 씀
- 공통 노드 질문(X1, X2, A1, A2)은 대표 이름이 띄어쓰기를 뺀 글자까지 같아야 "값 같음"(7단계 승인 기준)
- 연결 검사: 세 문서 종류의 시험 결과를 한 그래프로 합쳐(공통 노드는 대표 이름으로, Product는 정형 상품 이름으로 합침)
  공통 노드에 잇지 못한 단위 비율, X1 경로 비율, X2 경로 수, 허브 경고를 셈
실행: python tools/fill_test_v2.py [--round=N] [--only=doc,doc] → {doc}/output/fill_*.{jsonl,md,json}, output/connect_report.md
"""

from __future__ import annotations

import asyncio
import copy
import json
import re
import sys
from collections import Counter, defaultdict

from neo4j_graphrag.components.entity_relation_extractor import LLMEntityRelationExtractor, OnError
from neo4j_graphrag.components.graph_pruning import GraphPruning
from neo4j_graphrag.components.schema import GraphSchema

from common import BASE, decisions, load_json, load_units, make_llm, save_json
from fill_test import CONCURRENCY, MATCH, extract_one, head_line, overlap, report

DOCS = ["regulation", "benefit_guide", "consult_log"]
META_LABELS = {"CustomerSegment", "PseudoMember"}
META_RELS = {"IN_SEGMENT", "OF_MEMBER", "HAS_TOPIC", "FOLLOWS"}  # FOLLOWS는 2라운드부터 코드가 채움(라2)


def previous_records() -> dict[str, str | None]:
    """상담 청크 ID → 같은 가명 회원의 바로 앞 상담 record_id(메타데이터만 씀, 2라운드 라2)."""

    consult = [u for u in load_units() if u["doc_type"] == "consult_log"]
    by_member: dict[str, list] = defaultdict(list)
    for u in consult:
        md = u["metadata"]
        by_member[md["member_pseudo_id"]].append((md["consult_date"], md["record_id"], u["id"]))
    out = {}
    for rows in by_member.values():
        rows.sort()
        for i, (_, _, cid) in enumerate(rows):
            out[cid] = rows[i - 1][1] if i else None
    return out


def numbers(s: str) -> set[str]:
    return set(re.findall(r"\d[\d.\-]*\d|\d", str(s)))
SHARED = {"Topic": "name", "MerchantCategory": "name"}
norm = lambda s: re.sub(r"\s+", "", str(s)).removesuffix("카드")


def extraction_schema(draft: dict) -> dict:
    d = copy.deepcopy(draft)
    d["node_types"] = [n for n in d["node_types"] if n["label"] not in META_LABELS]
    d["relationship_types"] = [r for r in d["relationship_types"] if r["label"] not in META_RELS]
    d["patterns"] = [p for p in d["patterns"] if p[1] not in META_RELS]
    d["constraints"] = [c for c in d["constraints"] if c["node_type"] not in META_LABELS]
    return d


def vocab_filter(rec: dict) -> dict:
    """목록에서만 고르는 노드의 이름이 목록에 없으면 그 노드와 관계를 지움(4라운드 라4). 인덱싱도 같은 규칙을 써야 함."""

    sc = load_json("shared_concepts.json")
    if "vocabulary_enforcement" not in sc or "error" in rec:
        return rec
    vocab = {"Topic": {norm(t["name"]) for t in sc["shared_node_types"]["Topic"]["vocabulary"]},
             "MerchantCategory": {norm(c["name"]) for c in sc["shared_node_types"]["MerchantCategory"]["vocabulary"]},
             "ProposalTrait": {norm(t) for t in sc["proposal_traits"]}}
    drop = {n["id"] for n in rec["nodes"] if n["label"] in vocab and norm(n["properties"].get("name", "")) not in vocab[n["label"]]}
    if drop:
        rec = {**rec, "vocab_dropped": [n["properties"].get("name") for n in rec["nodes"] if n["id"] in drop],
               "nodes": [n for n in rec["nodes"] if n["id"] not in drop],
               "rels": [r for r in rec["rels"] if r["start"] not in drop and r["end"] not in drop]}
    return rec


def parse_expected(text: str) -> dict[str, set[str]]:
    """'주제: a, b / 업종: c' 또는 '수용: x / 거절: y' 꼴을 {이름 묶음}으로 나눔. 접두어가 없으면 전체를 이름 목록으로 봄."""

    out: dict[str, set[str]] = defaultdict(set)
    for part in str(text).split("/"):
        k, _, v = part.partition(":") if ":" in part else ("", "", part)
        for name in re.split(r"[,，]", v):
            if name.strip() and name.strip() != "없음":
                out[k.strip()].add(norm(name.strip()))
    return out


def ends(rec: dict, rel: str, label: str | None = None) -> list[dict]:
    by_id = {n["id"]: n for n in rec.get("nodes", [])}
    return [by_id[r["end"]] for r in rec.get("rels", []) if r["type"] == rel and r["end"] in by_id
            and (label is None or by_id[r["end"]]["label"] == label)]


def names(nodes: list[dict], prop: str = "name") -> set[str]:
    return {norm(n["properties"].get(prop, "")) for n in nodes if n["properties"].get(prop)}


def shared_answer(doc: str, q: str, rec: dict) -> tuple[bool, dict[str, set[str]]]:
    """공통 노드 질문의 뽑음 여부와 뽑은 이름 묶음."""

    if q == "X1" and doc in ("regulation", "consult_log"):
        got = {"주제": names(ends(rec, "ABOUT", "Topic")), "업종": names(ends(rec, "MENTIONS_CATEGORY"))}
        if doc == "regulation":
            got = {"": got["주제"]}
    elif q == "X1":  # 혜택 안내. '뽑음'은 업종이 있을 때만(3라운드 가3), 방식은 값 비교에만 씀
        meth = {norm(n["properties"]["apply_method"]) for n in rec.get("nodes", [])
                if n["label"] == "Benefit" and n["properties"].get("apply_method")}
        got = {"업종": names(ends(rec, "APPLIES_TO")), "방식": meth}
        return bool(got["업종"]), got
    elif q == "X2":
        got = {"": names([n for n in rec.get("nodes", []) if n["label"] == "Product"], "product_name")}
    elif q == "A1":
        got = {"": names(ends(rec, "ABOUT", "Topic"))}
    elif q == "A2":
        got = {"": names(ends(rec, "HAS_TRAIT"))}
    else:
        raise KeyError(q)
    return any(got.values()), got


def score_v2(doc: str, results: list[dict], expected: dict, cq_map: dict, criteria: dict) -> dict:
    from fill_test import answer_of

    metrics, examples = {}, []
    prev = previous_records() if doc == "consult_log" else {}
    for q, targets in cq_map.items():
        targets = [t for t in targets if t.get("rel") not in META_RELS]
        pos = neg = hit = fp = same = 0
        for rec in results:
            if "error" in rec:
                continue
            exp = expected[rec["chunk_id"]][q]["answer"]
            if doc == "consult_log" and q == "C5":  # 코드가 메타데이터로 채운 앞 상담(라2)
                got_text = prev.get(rec["chunk_id"]) or ""
                found, ok = bool(got_text), got_text == str(exp).strip()
            elif doc == "regulation" and q == "R5":  # 칸 이름을 빼고 값(숫자, 날짜)만 비교(가1)
                found, got_text = answer_of(rec, targets)
                ok = found and numbers(exp) <= numbers(got_text)
            elif q[0] in "XA":
                found, got = shared_answer(doc, q, rec)
                want = parse_expected(exp)
                if q == "A2":  # 결정(수용, 거절, 보류)은 제안 노드의 속성이라 성격 이름만 맞춰 봄
                    want = {"": set().union(*want.values())} if want else {}
                if doc == "regulation" or q in ("X2", "A1"):
                    want = {"": set().union(*want.values())} if want else {}
                ok = found and all(v <= got.get(k, set()) for k, v in want.items() if v)
                got_text = json.dumps({k: sorted(v) for k, v in got.items()}, ensure_ascii=False)
            else:  # 기대 답이 ' / '로 이은 여러 항목이면 항목 하나라도 맞으면 값 같음(3라운드 가2)
                found, got_text = answer_of(rec, targets)
                ok = found and max(overlap(p, got_text) for p in str(exp).split(" / ")) >= MATCH
            if exp != "없음":
                pos += 1
                hit += found
                same += ok
                if not found:
                    examples.append((q, "못 뽑음", rec["chunk_id"], exp, got_text))
                elif not ok:
                    examples.append((q, "값 다름", rec["chunk_id"], exp, got_text))
            else:
                neg += 1
                fp += found
                if found:
                    examples.append((q, "잘못 뽑음", rec["chunk_id"], exp, got_text))
        recall = hit / pos if pos else None
        fpr = fp / neg if neg else None
        match = same / hit if hit else None
        passed = ((recall is None or recall >= criteria["recall_min"]) and (fpr is None or fpr <= criteria["fp_max"])
                  and (match is None or match >= criteria["match_min"]) and pos > 0)
        metrics[q] = {"pos": pos, "hit": hit, "neg": neg, "fp": fp, "same": same, "recall": recall, "fp_rate": fpr,
                      "match": match, "pass": passed}
    return {"metrics": metrics, "examples": examples}


async def run_doc(doc: str, rnd: int, units: dict, criteria: dict) -> list[dict]:
    spec = load_json(f"{doc}/schema_spec.json")
    schema = GraphSchema.model_validate(extraction_schema(load_json(f"{doc}/output/schema_draft.json")))
    expected = load_json(f"{doc}/expected_answers.json")["answers"]
    llm = make_llm(graph_safe=True)
    extractor = LLMEntityRelationExtractor(llm=llm, create_lexical_graph=False, on_error=OnError.RAISE)
    pruner, sem = GraphPruning(), asyncio.Semaphore(CONCURRENCY)
    results = await asyncio.gather(*[
        extract_one(sem, extractor, pruner, schema, cid,
                    head_line(units[cid]["metadata"], spec.get("metadata_header", [])) + units[cid]["text"])
        for cid in expected])
    results = [vocab_filter(r) for r in results]
    out = BASE / doc / "output"
    with (out / "fill_calls.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    sc = score_v2(doc, results, expected, spec["cq_map"], criteria)
    text = report(doc, rnd, results, sc, criteria, units, dict(llm.usage))
    text = text.replace("- 값이 같음 판정:", "- 값이 같음 판정(공통 노드 질문 X, A는 대표 이름이 띄어쓰기를 뺀 글자까지 같아야 함, 나머지는):")
    (out / "fill_report.md").write_text(text, encoding="utf-8")
    (out / f"fill_report_round{rnd}.md").write_text(text, encoding="utf-8")
    save_json(f"{doc}/output/fill_metrics.json", {"round": rnd, "metrics": sc["metrics"], "usage": dict(llm.usage),
                                                  "all_pass": all(m["pass"] for m in sc["metrics"].values())})
    print(text, flush=True)
    return results


def product_ids() -> dict[str, str]:
    path = BASE.parents[1] / "rdb" / "init" / "02_seed.sql"
    rows, on = {}, False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("COPY product "):
            on = True
            continue
        if on and line.startswith("\\."):
            break
        if on:
            pid, name = line.split("\t")[:2]
            rows[norm(name)] = pid
    return rows


def connect(units: dict, criteria: dict) -> str:
    """세 문서 종류의 시험 결과를 한 그래프로 합쳐 연결을 셈."""

    shared = load_json("shared_concepts.json")
    pid = product_ids()
    topic_map = shared["metadata_nodes"]["Topic(상담 주제)"]["map"]
    seg_re = re.compile(shared["metadata_nodes"]["CustomerSegment"]["rule"])
    edges: list[tuple[str, str, str, str]] = []  # (doc, 시작 키, 관계, 끝 키)
    node_doc: dict[str, str] = {}
    unit_shared: dict[tuple[str, str], set[str]] = defaultdict(set)
    expected = {d: load_json(f"{d}/expected_answers.json")["answers"] for d in DOCS}
    structural = {(s["doc"], s["rel"]) for s in shared["structural_relationships"]}

    def key(doc, cid, n):
        if n["label"] in SHARED and n["properties"].get(SHARED[n["label"]]):
            return f"{n['label']}:{norm(n['properties'][SHARED[n['label']]])}"
        if n["label"] == "Product":
            name = norm(n["properties"].get("product_name", ""))
            return f"Product:{n['properties'].get('product_id') or pid.get(name) or name}"
        return f"{doc}:{cid}:{n['id']}:{n['label']}"

    for doc in DOCS:
        for line in (BASE / doc / "output" / "fill_calls.jsonl").read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if "error" in rec:
                continue
            cid, by_id = rec["chunk_id"], {n["id"]: n for n in rec["nodes"]}
            for n in rec["nodes"]:
                k = key(doc, cid, n)
                node_doc.setdefault(k, "shared" if n["label"] in SHARED or n["label"] == "Product" else doc)
                if node_doc[k] == "shared":
                    unit_shared[(doc, cid)].add(k)
            for r in rec["rels"]:
                if r["start"] in by_id and r["end"] in by_id:
                    edges.append((doc, key(doc, cid, by_id[r["start"]]), r["type"], key(doc, cid, by_id[r["end"]])))
            if doc == "consult_log":  # 메타데이터 노드는 코드가 채움
                md = units[cid]["metadata"]
                cons = next((key(doc, cid, n) for n in rec["nodes"] if n["label"] == "Consultation"), f"{doc}:{cid}:cons")
                seg = seg_re.match(md.get("source", ""))
                if seg:
                    edges.append((doc, cons, "IN_SEGMENT", f"CustomerSegment:{seg.group(1)}"))
                edges.append((doc, cons, "OF_MEMBER", f"PseudoMember:{md.get('member_pseudo_id')}"))
                if md.get("topic") in topic_map:
                    edges.append((doc, cons, "HAS_TOPIC", f"Topic:{norm(topic_map[md['topic']])}"))
    out_edges = defaultdict(list)
    for doc, a, t, b in edges:
        out_edges[a].append((t, b))
    in_edges = defaultdict(list)
    for doc, a, t, b in edges:
        in_edges[b].append((t, a))

    # 1) 공통 노드에 잇지 못한 단위: 기대 답에 공통 노드가 있는 단위 중 공통 노드가 하나도 없는 단위
    need = []
    for doc in DOCS:
        for cid, a in expected[doc].items():
            wants = [q for q in ("X1", "X2", "A1") if q in a and a[q]["answer"] != "없음"]
            if wants:
                need.append((doc, cid, bool(unit_shared.get((doc, cid)))))
    unlinked = sum(1 for *_, ok in need if not ok) / len(need) if need else None
    by_doc_unlinked = {d: f"{sum(1 for x in need if x[0] == d and not x[2])}/{sum(1 for x in need if x[0] == d)}" for d in DOCS}

    # 2) X1 경로: 불만이 있는 상담 단위 중 불만 -ABOUT-> 주제 <-ABOUT- 조항 이 하나라도 있는 비율
    clause_topics = {b for doc, a, t, b in edges if doc == "regulation" and t == "ABOUT"}
    complaint_units = [cid for cid, a in expected["consult_log"].items() if a["C1"]["answer"] != "없음"]
    x1_ok = 0
    x1_rows = []
    for cid in complaint_units:
        tops = {b for doc, a, t, b in edges if doc == "consult_log" and a.startswith(f"consult_log:{cid}:")
                and a.endswith(":Complaint") and t == "ABOUT"}
        hit = tops & clause_topics
        x1_ok += bool(hit)
        x1_rows.append((cid, sorted(tops), sorted(hit)))
    x1 = x1_ok / len(complaint_units) if complaint_units else None

    # 3) X2 경로: 상담 -MENTIONS_PRODUCT-> Product -OFFERS_BENEFIT-> 혜택 (시험 표본끼리만 있어 겹치는 상품이 적을 수 있음)
    offered = {a for doc, a, t, b in edges if t == "OFFERS_BENEFIT"}
    mentioned = [(a, b) for doc, a, t, b in edges if t == "MENTIONS_PRODUCT"]
    x2 = sum(1 for _, b in mentioned if b in offered)

    # 4) 허브: 노드 하나가 그 문서 종류 노드의 30% 이상과 이어지면 경고(구조용 관계 제외)
    doc_nodes = Counter(v for v in node_doc.values() if v != "shared")
    deg = defaultdict(lambda: defaultdict(set))
    for doc, a, t, b in edges:
        if (doc, t) in structural:
            continue
        deg[a][doc].add(b)
        deg[b][doc].add(a)
    hubs = []
    for n, per in deg.items():
        for doc, nb in per.items():
            share = len(nb) / doc_nodes[doc] if doc_nodes[doc] else 0
            if share >= criteria["hub_share_warn"]:
                hubs.append((n, doc, len(nb), doc_nodes[doc], share))
    top_shared = sorted(((n, sum(len(v) for v in per.values())) for n, per in deg.items()
                         if n.split(":")[0] in ("Topic", "MerchantCategory", "Product")), key=lambda x: -x[1])[:10]

    pct = lambda x: "해당 없음" if x is None else f"{x * 100:.0f}%"
    ok_unlinked = unlinked is not None and unlinked <= criteria["connect_unlinked_max"]
    ok_x1 = x1 is not None and x1 >= criteria["x1_path_min"]
    ok_hub = len(hubs) <= criteria["hub_warnings_max"]
    cat_names = sorted({b.split(":", 1)[1] for doc, a, t, b in edges if b.startswith("MerchantCategory:")})
    lines = ["# 연결 검사 보고서", "",
             "- 세 문서 종류의 시험 결과를 한 그래프로 합침. Topic과 MerchantCategory는 띄어쓰기를 뺀 대표 이름으로, "
             "Product는 정형 상품 이름으로 찾은 상품 ID로 합침. 상담의 고객군, 가명 회원, 상담 주제는 메타데이터로 채움", "",
             "| 검사 | 결과 | 기준 | 판정 |", "|---|---|---|---|",
             f"| 공통 노드에 잇지 못한 단위 | {pct(unlinked)}(문서 종류별 못 이은 수/대상 수: "
             + ", ".join(f"{d} {v}" for d, v in by_doc_unlinked.items()) + f") | {criteria['connect_unlinked_max'] * 100:.0f}% 이하 | "
             f"{'통과' if ok_unlinked else '미달'} |",
             f"| X1 경로(불만 → 주제 ← 조항) | {x1_ok}/{len(complaint_units)}({pct(x1)}) | {criteria['x1_path_min'] * 100:.0f}% 이상 | "
             f"{'통과' if ok_x1 else '미달'} |",
             f"| X2 경로(상담 → 카드 상품 → 혜택) | 상담의 카드 언급 {len(mentioned)}개 중 시험 표본 혜택과 이어진 것 {x2}개 | 기준 없음(참고) | 참고 |",
             f"| 허브 경고 | {len(hubs)}건 | {criteria['hub_warnings_max']}건 | {'통과' if ok_hub else '미달'} |", "",
             "## X1 경로 상담별", "", "| 상담 청크 | 불만 주제 | 조항과 겹친 주제 |", "|---|---|---|"]
    lines += [f"| {c} | {', '.join(t.split(':', 1)[1] for t in tops) or '없음'} | "
              f"{', '.join(t.split(':', 1)[1] for t in hit) or '없음'} |" for c, tops, hit in x1_rows]
    lines += ["", "## 연결이 많은 공통 노드(상위 10)", "", "| 노드 | 이웃 수 |", "|---|---:|"]
    lines += [f"| {n} | {k} |" for n, k in top_shared]
    lines += ["", "## 허브 경고", ""] + ([f"- {n}({d}): 이웃 {k}개 / 그 문서 종류 노드 {t}개({s * 100:.0f}%)" for n, d, k, t, s in hubs]
                                        or ["- 없음"])
    lines += ["", "## 시험에서 나온 업종 이름(동의어 표 재료)", "", ", ".join(cat_names) or "없음"]
    save_json("output/connect_metrics.json", {"unlinked": unlinked, "unlinked_by_doc": by_doc_unlinked, "x1": x1,
                                              "x1_ok": x1_ok, "x1_total": len(complaint_units), "x2_mentions": len(mentioned),
                                              "x2_linked": x2, "hubs": hubs, "category_names": cat_names,
                                              "pass": ok_unlinked and ok_x1 and ok_hub})
    text = "\n".join(lines) + "\n"
    (BASE / "output" / "connect_report.md").write_text(text, encoding="utf-8")
    return text


async def main() -> None:
    rnd = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--round=")), "1")  # 측정 반복은 5m1처럼 글자로 씀
    only = next((a.split("=", 1)[1].split(",") for a in sys.argv[1:] if a.startswith("--only=")), DOCS)
    units = {c["id"]: c for c in load_units()}
    criteria = load_json("pass_criteria.json")
    if "--connect-only" not in sys.argv:
        for doc in only:
            await run_doc(doc, rnd, units, criteria)
    print(connect(units, criteria))


if __name__ == "__main__":
    asyncio.run(main())
