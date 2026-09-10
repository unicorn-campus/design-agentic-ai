"""S2.3 결과를 출처가 있는 조항·혜택·상담 입력으로 연결함."""
from collections import defaultdict
import json
from pathlib import Path
import re

CLAUSE = re.compile(r"^제\s*\d+조(?:의\d+)?\s*\([^\n]+", re.M)
BENEFIT = re.compile(r"^D2-C\d{3}-B\d+\s*\|", re.M)


def load_documents(path: Path) -> list[dict]:
    """폴더는 교육생이 편집한 개별 Markdown을 우선 읽음."""
    if path.is_file():
        return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    files = sorted((path / "pages").glob("*.md")) + sorted((path / "records").glob("*.md"))
    if not files:
        candidate = path / "documents.jsonl"
        if candidate.exists():
            return load_documents(candidate)
        raise ValueError(f"S2.3 결과가 없음: {path}. README의 준비 명령을 먼저 실행하세요.")
    import yaml
    documents = []
    for file in files:
        match = re.match(r"\A---\r?\n(.*?)\r?\n---\s*\r?\n(.*)\Z",
                         file.read_text(encoding="utf-8-sig"), re.S)
        if not match:
            raise ValueError(f"YAML 머리말 오류: {file.name}")
        meta = yaml.safe_load(match[1])
        if not isinstance(meta, dict):
            raise ValueError(f"metadata 형식 오류: {file.name}")
        meta = {k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in meta.items()}
        documents.append({"page_content": match[2].strip(), "metadata": meta})
    return documents


def validate_documents(documents: list[dict]) -> None:
    seen = set()
    for i, doc in enumerate(documents, 1):
        if not isinstance(doc, dict) or not isinstance(doc.get("metadata"), dict):
            raise ValueError(f"입력 {i}: metadata 사전 필요")
        md = doc["metadata"]
        for key in ("source", "doc_type", "created_at", "version", "owner_dept", "access_level"):
            if not isinstance(md.get(key), str) or not md[key].strip():
                raise ValueError(f"입력 {i}: {key} 필수 문자열 누락")
        if not isinstance(doc.get("page_content"), str):
            raise ValueError(f"입력 {i}: page_content 문자열 필요")
        if md["doc_type"] not in {"regulation", "benefit_guide", "consult_log"}:
            raise ValueError(f"입력 {i}: 지원하지 않는 doc_type")
        if md["doc_type"] == "consult_log":
            for key in ("record_id", "consult_date", "channel", "member_pseudo_id"):
                if not isinstance(md.get(key), str) or not md[key]:
                    raise ValueError(f"입력 {i}: {key} 누락, S2.3 --pseudonymize 결과 필요")
            if md["access_level"] != "restricted" or "member_id" in md:
                raise ValueError(f"입력 {i}: 상담 가명화·restricted 확인 필요")
            identity = ("D3", md["record_id"])
        else:
            if type(md.get("page")) is not int or md["page"] < 1:
                raise ValueError(f"입력 {i}: page 양의 정수 필요")
            identity = (md["source"], md["page"])
        if identity in seen:
            raise ValueError(f"중복 문서/상담 입력: {identity}")
        seen.add(identity)


def normalize_table(text: str) -> str:
    """D2의 테두리 없는 표와 마지막 셀의 줄바꿈을 Markdown 표로 변환함."""
    lines = text.splitlines()
    result = []
    in_table = False
    for line in lines:
        if "|" in line and not line.startswith("##"):
            cells = line.strip().strip("|").strip()
            result.append("| " + cells + " |")
            if not in_table:
                result.append("| " + " | ".join(["---"] * len(cells.split("|"))) + " |")
            in_table = True
        elif in_table and line and not re.match(r"^(모든 명칭|일반 혜택|가족카드:|카드별 명칭)", line):
            result[-1] = result[-1].rstrip("| ") + " " + line.strip() + " |"
        else:
            result.append(line)
            in_table = False
    return "\n".join(result)


def prepare_units(documents: list[dict]) -> tuple[list[dict], list[dict]]:
    """원문 수정 없이 청킹 경계와 페이지 범위를 준비함. 제외 페이지는 별도 기록함."""
    units, skipped = [], []
    groups = defaultdict(list)
    for doc in documents:
        groups[doc["metadata"]["source"]].append(doc)
    for source, docs in sorted(groups.items()):
        kind = docs[0]["metadata"]["doc_type"]
        if kind == "consult_log":
            units.extend({"text": d["page_content"], "meta": d["metadata"], "key": "D3"} for d in docs)
            continue
        docs.sort(key=lambda d: d["metadata"]["page"])
        if kind == "regulation":
            active = None
            footnotes = []
            for doc in docs:
                if doc['page_content'].startswith('각주와 출처'):
                    for line in doc['page_content'].splitlines():
                        match = re.match(r'^(\*+)\s+(.+)', line)
                        if match:
                            footnotes.append((match[1], line, doc['metadata']['page']))
            for doc in docs:
                md, body = doc["metadata"], doc["page_content"]
                if md.get("section_kind") == "contents" or body.startswith(("한빛카드\n", "문서 메타데이터", "각주와 출처")):
                    skipped.append({"source": source, "page": md["page"], "reason": "표지·메타정보·목차·출처 페이지"})
                    continue
                # 장 제목을 직전 조문에 섞지 않음.
                body = re.sub(r"^제\d+장[^\n]*\n?", "", body, flags=re.M)
                matches = list(CLAUSE.finditer(body))
                prefix = body[:matches[0].start()] if matches else body
                if prefix.strip():
                    if active is None:
                        raise ValueError(f"{source} p{md['page']}: 연결할 조항 없는 본문")
                    active["text"] += "\n" + prefix.strip()
                    active["meta"]["page_end"] = md["page"]
                for j, match in enumerate(matches):
                    end = matches[j + 1].start() if j + 1 < len(matches) else len(body)
                    active = {"text": body[match.start():end].strip(),
                              "meta": {**md, "doc_key": "D1", "page_end": md["page"]}, "key": "D1"}
                    units.append(active)
            for unit in [u for u in units if u['meta']['source'] == source]:
                for marker, note, page in footnotes:
                    if re.search(r'(?<!\*)' + re.escape(marker) + r'(?!\*)', unit['text']):
                        unit['text'] += '\n' + note
                        unit['meta']['footnote_page'] = page
        else:
            card_names = {}
            for doc in docs:
                match = re.match(r"(D2-C\d{3})\n([^\n]+)", doc["page_content"])
                if match:
                    card_names[match[1]] = match[2]
            for doc in docs:
                md, body = doc["metadata"], doc["page_content"]
                if body.startswith(("SYNTHETIC DATA", "카드 찾아보기", "원문 참고", "참고 자료")):
                    skipped.append({"source": source, "page": md["page"], "reason": "표지·목차·참고 목록"})
                    continue
                if body.startswith("문서 적용 기준"):
                    units.append({"text": "## " + body, "meta": {**md, "doc_key": "D2"}, "key": "D2"})
                    continue
                hits = list(BENEFIT.finditer(body))
                prefix = body[:hits[0].start()] if hits else body
                if prefix.strip():
                    card = re.match(r"(D2-C\d{3})\n([^\n]+)\n(.*)", prefix, re.S)
                    if card:
                        # 시행일·공개등급은 metadata에도 보존됨. 문자열은 별도 문맥으로 유지함.
                        title = f"## {card[1]} {card[2]} · 연회비"
                        content = card[3].replace("연회비\n", "", 1)
                        # 표 앞 시행일 줄의 | 는 표 구분자가 아니므로 분리함.
                        first, _, content = content.partition("\n")
                        units.append({"text": title + "\n" + first.replace(" | ", " · ") + "\n" + normalize_table(content),
                                      "meta": {**md, "doc_key": "D2", "card_id": card[1], "card_name": card[2]}, "key": "D2"})
                    elif '참고 카드:' in prefix:
                        skipped.append({"source": source, "page": md["page"], "reason": "카드/혜택 경계 없는 참고 본문", "text": prefix})
                    elif units and units[-1]['meta']['source'] == source:
                        # 이전 페이지의 혜택 각주가 넘어온 경우 직전 입력에 연결함.
                        units[-1]['text'] += '\n' + prefix.strip()
                        units[-1]['meta']['page_end'] = md['page']
                    else:
                        raise ValueError(f"{source} p{md['page']}: 연결할 카드/혜택 없는 본문")
                for j, hit in enumerate(hits):
                    end = hits[j + 1].start() if j + 1 < len(hits) else len(body)
                    heading, _, content = body[hit.start():end].strip().partition("\n")
                    card_id = heading.split('-B', 1)[0]
                    if card_id not in card_names:
                        raise ValueError(f"카드명 연결 실패: {heading}")
                    title = f"## {card_names[card_id]} · {heading.replace(' | ', ' · ')}"
                    units.append({"text": title + "\n" + normalize_table(content),
                                  "meta": {**md, "doc_key": "D2", "card_id": card_id,
                                           "card_name": card_names[card_id]}, "key": "D2"})
    return units, skipped
