"""조별 골격과 강사 완성본이 함께 사용하는 실행 도구."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from lab_io import load_chunks, summarize
from src.helpers import configure, get_collection, settings


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(reference: bool = False) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='S3.2 적재·검색·근거 프롬프트·인용 검사')
    parser.add_argument('action', choices=(
        'check', 'index', 'inspect', 'search', 'variants', 'prompt', 'answer'))
    parser.add_argument('--input', type=Path, default=BASE.parent / 's3.1/data/chunked/chunks.jsonl')
    parser.add_argument('--group', type=int, choices=range(1, 7), default=1)
    parser.add_argument('--db-path', type=Path, help='상대 경로는 s3.2 기준')
    parser.add_argument('--collection', default='card_docs_ref' if reference else 'card_docs')
    parser.add_argument('--backend', choices=('sentence-transformers', 'smoke'), default='sentence-transformers')
    parser.add_argument('--model', help='EMBED_MODEL 덮어쓰기')
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--query')
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--role', default='agent')
    parser.add_argument('--filters', default='{}', help='JSON 객체, 예: {"doc_type":"regulation"}')
    parser.add_argument('--doc-type', choices=('regulation', 'benefit_guide', 'consult_log'))
    parser.add_argument('--member-id', help='상담 화면의 가명 고객키를 검색 필터로 주입')
    parser.add_argument('--version', help='문서 개정판 필터, 예: 1.2')
    parser.add_argument('--questions', type=Path, help='슬라이드 15~16의 질문 3건 JSON')
    parser.add_argument('--output', type=Path, help='JSON 실행 결과 또는 비교표 .md 저장 경로')
    args = parser.parse_args()
    try:
        # smoke 저장소는 학습용 실제 모델 저장소와 기본 경로부터 분리함.
        db_path = args.db_path
        if db_path is None:
            db_path = BASE / f'data/chroma_smoke/group{args.group}' if args.backend == 'smoke' else settings().db_path
            if args.group != 1 and args.backend != 'smoke':
                db_path = BASE / f'data/chroma/group{args.group}'
        config = configure(db_path=db_path, collection=args.collection, backend=args.backend, model=args.model)
        suffix = '_ref' if reference else ''
        if args.action == 'check':
            value = summarize(load_chunks(args.input))
        elif args.action == 'index':
            module = importlib.import_module(f'src.indexing{suffix}')
            chunks = load_chunks(args.input)
            col = get_collection()
            before = col.count()
            value = module.embed_and_upsert(chunks, batch_size=args.batch_size)
            value.update(input_count=len(chunks), count_before=before, count_after=col.count(),
                         metadatas=col.peek(limit=1)['metadatas'])
            value['accounting_ok'] = value['ok'] + len(value['failed']) == len(chunks)
            value['note'] = 'count == ok 비교는 새 컬렉션 기준. 재적재는 동일 ID를 갱신함'
        elif args.action == 'inspect':
            col = get_collection()
            sample = col.peek(limit=1)
            embeddings = sample.pop('embeddings', None)
            dimension = (len(embeddings[0])
                         if embeddings is not None and len(embeddings) else None)
            value = {'count': col.count(), 'embedding_dimension': dimension, 'sample': sample}
            # 벡터 전문 출력은 생략하고 검증에 필요한 차원만 기록함.
        else:
            module = importlib.import_module(f'src.retrieval{suffix}')
            filters = json.loads(args.filters)
            if not isinstance(filters, dict):
                raise ValueError('--filters는 JSON 객체여야 함')
            if args.doc_type:
                filters['doc_type'] = args.doc_type
            if args.member_id:
                filters['member_pseudo_id'] = args.member_id
            if args.version:
                filters['version'] = args.version
            if args.action == 'search':
                if not args.query:
                    raise ValueError('search는 --query 필요')
                value = {'hits': [asdict(hit) for hit in module.search(
                    args.query, args.top_k, filters or None, args.role)]}
            elif args.action == 'variants':
                return run_variants(args, module.search, filters)
            else:
                if not args.query:
                    raise ValueError(f'{args.action}는 --query 필요')
                answer_module = importlib.import_module(f'src.answering{suffix}')
                hits = module.search(args.query, args.top_k, filters or None, args.role)
                prompt = answer_module.build_rag_prompt(args.query, hits)
                empty_prompt = answer_module.build_rag_prompt(args.query, [])
                value = {
                    'query': args.query,
                    'system': answer_module.RAG_SYSTEM,
                    'user_prompt': prompt,
                    'hits': [asdict(hit) for hit in hits],
                    'prompt_checks': check_prompt(prompt, empty_prompt, args.query, hits),
                }
                if args.action == 'answer':
                    from src.evidence import render_answer
                    from src.llm_client import ask_llm

                    responses = []

                    def capture_response(system, user):
                        response = ask_llm(system, user)
                        responses.append(response)
                        return response

                    answer = answer_module.answer_with_sources(
                        args.query, hits, ask_fn=capture_response)
                    value['llm_response'] = responses[0] if responses else None
                    value['answer'] = answer
                    value['rendered_answer'] = render_answer(answer)
                    value['evidence_check'] = answer['verification']
        value['implementation'] = 'reference' if reference else 'student'
        value['backend'] = config.backend
        value['model'] = config.model
        value['db_path'] = str(config.db_path)
        value['collection'] = config.collection
        emit(value)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return 2 if value.get('failed') else 0
    except NotImplementedError as exc:
        print(f'작성 필요: {exc}\n참고 구현 실행은 run_lab_ref.py 사용', file=sys.stderr)
        return 3
    except (ValueError, OSError, KeyError, RuntimeError, ImportError) as exc:
        print(f'실행 중단: {exc}', file=sys.stderr)
        return 1


def check_prompt(prompt: str, empty_prompt: str, question: str, hits: list) -> dict:
    """슬라이드 19 점검 기준 다섯 가지를 기계적으로 확인함."""
    blocks = [f'[검색결과 {index}]' for index in range(1, len(hits) + 1)]
    return {
        'block_count_ok': all(prompt.count(block) == 1 for block in blocks),
        'number_source_chunk_text_ok': all(
            block in prompt
            and '원본 문서:' in prompt
            and str(hit.metadata.get('chunk_id')) in prompt
            and hit.text in prompt
            for block, hit in zip(blocks, hits)
        ),
        'question_last_ok': prompt.rstrip().endswith(question.strip()),
        'all_text_preserved': all(hit.text in prompt for hit in hits),
        'empty_hits_supported': (
            empty_prompt == f'[검색결과 목록]\n\n\n[질문]\n{question.strip()}'
        ),
    }


def run_variants(args, search_fn, filters) -> int:
    """슬라이드 15~16 공동 실습용. 기본 동작 검증에서는 호출하지 않음."""
    if settings().backend == 'smoke':
        raise ValueError('표현 변형 비교에는 실제 임베딩 모델 필요; smoke 사용 불가')
    if args.questions is None:
        raise ValueError('질문·정답 청크 ID를 먼저 작성하고 --questions 지정 필요')
    spec = json.loads(args.questions.read_text(encoding='utf-8-sig'))
    questions, expected = spec.get('questions'), spec.get('expected_chunk_ids')
    if (not isinstance(questions, list) or len(questions) != 3
            or any(not isinstance(q, str) or not q.strip() for q in questions)
            or not isinstance(expected, list) or not expected
            or any(not isinstance(v, str) or not v.strip() for v in expected)):
        raise ValueError('비어 있지 않은 질문 3개와 사전 지정 정답 청크 ID 목록 필요')
    col = get_collection()
    if set(col.get(ids=expected)['ids']) != set(expected):
        raise ValueError('정답 청크 ID 일부가 컬렉션에 없음. 적재 범위를 먼저 확인해야 함')
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    lines = ['# 같은 뜻 질문 3표현 비교', '',
             f"- 실행 시각: {datetime.now(timezone.utc).isoformat()}",
             f'- 모델: {settings().model}', f'- 역할: {args.role}',
             f'- 조건: {json.dumps(filters, ensure_ascii=False)}',
             f'- 사전 정답 ID: {", ".join(expected)}', '',
             '| 표현 | 질문 | Top-1 | Top-2 | Top-3 | 정답 포함 |',
             '|---|---|---|---|---|---|']
    for label, query in zip(('A', 'B', 'C'), questions):
        hits = search_fn(query, 3, filters or None, args.role)
        cells = [f"{h.metadata['chunk_id']} · {h.score}" for h in hits]
        cells += ['—'] * (3 - len(cells))
        rank = next((i for i, h in enumerate(hits, 1) if h.metadata['chunk_id'] in expected), None)
        lines.append('| ' + ' | '.join(map(cell, [label, query, *cells, f'{rank}위' if rank else '없음'])) + ' |')
    lines.extend(['', '## 왜 다른가 — 조별 가설', '', '(검색 결과 확인 후 조가 작성함)', ''])
    output = args.output or BASE / f'data/group{args.group}/w3_query_variants.md'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines), encoding='utf-8')
    print(f'비교표 저장: {output}')
    return 0
