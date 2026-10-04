"""평가셋 준비 — eval-set.md를 eval-set.json으로 바꾸고 검증 5검사를 돌림."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.domain.eval_set import build_eval_set_document, eval_set_hash, parse_eval_set_markdown
from app.domain.verification import CHECK_NAMES, check_against_index, check_structure

from .models import QualityError
from .ports import ArtifactStorePort, CorpusPort


class EvalSetService:
    """평가셋 변환 · 검증 서비스.

    파일 읽기 · 쓰기는 ArtifactStorePort, 색인 조각은 CorpusPort로 받음. 실험 실행은 하지 않음.
    """

    def __init__(self, store: ArtifactStorePort, corpus: CorpusPort):
        self.store, self.corpus = store, corpus

    def verify(self, questions: list[dict[str, Any]], *, with_index: bool = True) -> dict[str, Any]:
        """구조 검사(⑤)와 색인 검사(① ② ③ ④)를 돌려 보고서를 만듦.

        인자: with_index=False면 색인 없이 ⑤만 봄(색인 세대가 없는 환경에서 형식만 확인할 때).
        반환값: passed · generation · issues(문항 · 검사 · 사유) · counts를 담은 dict.
        """

        issues = check_structure(questions)
        generation = None
        if with_index:
            generation = self.corpus.active_generation()
            issues += check_against_index(questions, self.corpus.chunks())
        counts = {name: sum(issue.check == no for issue in issues) for no, name in CHECK_NAMES.items()}
        return {
            "passed": not issues,
            "generation": generation,
            "questions": len(questions),
            "counts": counts,
            "issues": [{**asdict(issue), "check_name": CHECK_NAMES[issue.check]} for issue in issues],
        }

    def build(self, markdown_path: Path, json_path: Path, *, with_index: bool = True) -> dict[str, Any]:
        """md를 읽어 문항을 만들고, 검증을 통과했을 때만 json을 씀.

        반환값: 검증 보고서 + eval_set_hash · 문항 구성 · 저장 경로(실패면 None).
        예외: md 꼴이 맞지 않으면 QualityError("eval_set_format").
        부수효과: 통과하면 json_path에 씀. 실패하면 기존 json을 건드리지 않음.
        """

        try:
            questions = parse_eval_set_markdown(self.store.read_text(markdown_path))
        except ValueError as error:
            raise QualityError("eval_set_format", str(error)) from error
        report = self.verify(questions, with_index=with_index)
        report["eval_set_hash"] = eval_set_hash(questions)
        report["composition"] = _composition(questions)
        report["saved_to"] = None
        if report["passed"]:
            self.store.write_json(json_path, build_eval_set_document(questions, markdown_path.name))
            report["saved_to"] = str(json_path)
        return report

    def verify_file(self, json_path: Path, *, with_index: bool = True, out_path: Path | None = None) -> dict[str, Any]:
        """이미 있는 eval-set.json을 다시 검증함(다른 세대에서 근거가 잘렸는지 볼 때 씀).

        부수효과: out_path가 있으면 보고서를 JSON으로 저장함. 평가셋 파일은 바꾸지 않음.
        """

        questions = self.store.read_json(json_path)["questions"]
        report = self.verify(questions, with_index=with_index)
        report["eval_set_hash"] = eval_set_hash(questions)
        if out_path is not None:
            self.store.write_json(out_path, report)
        return report


def _composition(questions: list[dict[str, Any]]) -> dict[str, int]:
    """문서별 문항 수(근거 첫 출처의 D1 · D2 · D3)와 답 없음 수."""

    result = {"D1": 0, "D2": 0, "D3": 0, "no_answer": 0}
    for question in questions:
        if not question["answerable"]:
            result["no_answer"] += 1
            continue
        key = question["relevance"][0]["source"][:2]
        result[key] = result.get(key, 0) + 1
    return result
