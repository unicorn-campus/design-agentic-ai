"""교재 슬라이드 28의 첫 실행 및 S3.2 전달 파일 생성."""
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

from lab_io import load_documents, prepare_units, validate_documents
from src.chunking import chunk_by_clause, chunk_by_turn, make_chunk, enforce_token_limit
from token_budget import TokenBudget

BASE = Path(__file__).resolve().parent


def run(args):
    if args.max_chars <= 0 or not 0 <= args.overlap < args.max_chars:
        raise ValueError("0 <= overlap < max_chars 필요")
    if not 0 <= args.d2_overlap < args.max_chars:
        raise ValueError("0 <= d2_overlap < max_chars 필요")
    if args.turns_per_chunk <= 0 or not 0 <= args.overlap_turns < args.turns_per_chunk:
        raise ValueError("0 <= overlap_turns < turns_per_chunk 필요")
    if args.output.resolve() == args.input.resolve() or args.output.resolve().is_relative_to(args.input.resolve()):
        raise ValueError("결과 폴더를 입력 폴더와 분리하세요.")
    if bool(args.tokenizer_json) != bool(args.max_input_tokens):
        raise ValueError('--tokenizer-json과 --max-input-tokens를 함께 지정하세요.')
    budget = TokenBudget(args.tokenizer_json, args.max_input_tokens, args.token_prefix) if args.tokenizer_json else None
    documents = load_documents(args.input)
    validate_documents(documents)
    if args.segment:
        documents = [d for d in documents if d['metadata']['doc_type'] != 'consult_log'
                     or f"_S{args.segment:02d}_" in d['metadata']['source']]
    units, skipped = prepare_units(documents)
    selected = [u for u in units if args.doc == 'all' or u['key'] == args.doc]
    if not selected:
        raise ValueError("선택 조건에 맞는 입력 없음")
    chunks, reviews, counts, exceptions = [], [], Counter(), []
    for unit in selected:
        text, meta, key = unit['text'], unit['meta'], unit['key']
        try:
            if key == 'D3':
                parts = chunk_by_turn(text, meta, args.turns_per_chunk, args.overlap_turns)
            else:
                overlap = args.d2_overlap if key == 'D2' else args.overlap
                parts = chunk_by_clause(text, meta, args.max_chars, overlap)
            if not parts and text.strip():
                raise ValueError("비어 있지 않은 입력에서 조각 0개 반환")
            for part in parts:
                if part.metadata.get('size_exception'):
                    exception_id = f"{key}_exception_{len(exceptions):04d}"
                    part.metadata['exception_id'] = exception_id
                    exceptions.append({**asdict(part), 'chunk_id': exception_id})
                if part.metadata.get('size_exception') and budget is None:
                    reviews.append({'reason': '단일 행+필수 문맥의 글자 수 예외: 모델 토큰 확인 필요',
                                    'metadata': part.metadata, 'text': part.text})
                    continue
                try:
                    checked = enforce_token_limit(part, budget.count, budget.limit) if budget else [part]
                except ValueError as exc:
                    reviews.append({'reason': str(exc), 'metadata': part.metadata, 'text': part.text})
                    continue
                doc_key = f"D3_{meta['record_id']}" if key == 'D3' else key
                # 여러 페이지·조항을 호출해도 문서 전체 번호를 연속 부여함.
                for candidate in checked:
                    if budget:
                        candidate.metadata['tokenizer_sha256'] = budget.sha256
                        candidate.metadata['token_prefix'] = budget.prefix
                    chunk = make_chunk(candidate.text, candidate.metadata, doc_key, counts[doc_key])
                    counts[doc_key] += 1
                    chunks.append(chunk)
        except ValueError as exc:
            reviews.append({"reason": str(exc), "metadata": meta, "text": text})
    ids = [c.chunk_id for c in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("중복 chunk_id 발견")
    by_doc = defaultdict(list)
    for chunk in chunks:
        if chunk.metadata['char_len'] != len(chunk.text):
            raise ValueError("char_len 불일치")
        by_doc[chunk.chunk_id[:2]].append(chunk)
    statistics = {}
    lines = [f"입력: {args.input.resolve()}", f"선택: {args.doc}, 조: {args.segment or '전체'}",
             f"인자: max_chars={args.max_chars}, overlap={args.overlap}, D2 overlap={args.d2_overlap}, "
             f"turns_per_chunk={args.turns_per_chunk}, overlap_turns={args.overlap_turns}"]
    for key, group in sorted(by_doc.items()):
        lengths = [len(c.text) for c in group]
        stats = {"count": len(group), "mean_chars": round(sum(lengths) / len(lengths), 2),
                 "max_chars": max(lengths)}
        statistics[key] = stats
        lines.extend([f"{key} 조각 수: {stats['count']}", f"{key} 평균 길이: {stats['mean_chars']}",
                      f"{key} 최대 길이: {stats['max_chars']}"])
    lines.append(f"입력 단위 {len(selected)}개 / 검토 보류 {len(reviews)}개 / 제외 페이지 {len(skipped)}개")
    lines.append(f"단일 행+필수 문맥 길이 예외 후보: {len(exceptions)}개")
    lines.append(f"토큰 검사: {budget.source if budget else '미설정(예외 후보 보류)'}")
    lines.append("글자 수는 Python len 기준. 검색 정확도·응답 품질을 측정한 값이 아님.")
    console_lines = lines.copy()
    for exception in exceptions:
        md = exception['metadata']
        lines.append(f"예외 {exception['chunk_id']}: char_len={md['char_len']} / {md['exception_reason']}")
    report = {"parameters": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
              "input_documents": len(documents), "input_units": len(selected), "statistics": statistics,
              "review_count": len(reviews), "exception_count": len(exceptions), "skipped": skipped,
              "size_exceptions": [{"metadata": e['metadata']} for e in exceptions],
              "input_sha256": hashlib.sha256(json.dumps(documents, ensure_ascii=False, sort_keys=True).encode()).hexdigest()}
    args.output.mkdir(parents=True, exist_ok=True)
    def write(name, content):
        (args.output / name).write_text(content, encoding='utf-8')
    write('chunks.jsonl', ''.join(json.dumps(asdict(c), ensure_ascii=False) + '\n' for c in chunks))
    write('review.jsonl', ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in reviews))
    write('exceptions.jsonl', ''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in exceptions))
    write('report.json', json.dumps(report, ensure_ascii=False, indent=2))
    write('chunking_run1.txt', '\n'.join(lines) + '\n')
    preview = ['# 청킹 결과 확인', '', '자동 생성 결과임. 원문·조건을 대조하고 온라인 조별 문서에 판정 기록 필요.', '']
    for chunk in chunks:
        preview.extend([f"## {chunk.chunk_id}", '',
                        '```json', json.dumps(chunk.metadata, ensure_ascii=False), '```', '', chunk.text, ''])
    write('chunks.md', '\n'.join(preview))
    print('\n'.join(console_lines))
    print(f"결과: {args.output.resolve()}")
    return 2 if reviews else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=BASE.parent / 's2.3/data/parsed')
    parser.add_argument('--output', type=Path, default=BASE / 'data/chunked')
    parser.add_argument('--doc', choices=['D1', 'D2', 'D3', 'all'], default='D1')
    parser.add_argument('--segment', type=int, choices=range(1, 7))
    parser.add_argument('--max-chars', type=int, default=600)
    parser.add_argument('--overlap', type=int, default=80)
    parser.add_argument('--d2-overlap', type=int, default=0)
    parser.add_argument('--turns-per-chunk', type=int, default=4)
    parser.add_argument('--overlap-turns', type=int, default=1)
    parser.add_argument('--tokenizer-json', type=Path, help='임베딩 모델의 로컬 tokenizer.json')
    parser.add_argument('--max-input-tokens', type=int, help='선택한 모델의 실제 입력 토큰 한도')
    parser.add_argument('--token-prefix', default='', help='모델 입력에 붙일 접두사(예: passage: )')
    args = parser.parse_args(argv)
    try:
        return run(args)
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        print(f"실행 중단: {exc}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
