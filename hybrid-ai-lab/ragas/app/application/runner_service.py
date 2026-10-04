"""버전 실험 실행기 — 계획 파일 하나로 F0 준비 → 버전마다 F1 ~ F6 → F7 비교표를 돌리고 포인터를 되돌림."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from pydantic import ValidationError

from app.domain.eval_set import eval_set_hash
from app.domain.plan import check_plan, leaf_differences, ordered_versions, parse_target, set_json_path, thread_id

from .compare_service import CompareService
from .models import (FAILED, INDEXER_CONFIG_ENV, RETRIEVER_ENV_NAMES, RUNNING, SKIPPED, SUCCESS, UNSUPPORTED,
                     WAITING, PlanSpec, QualityError, RunnerPaths, StepError, json_safe)
from .ports import (ArtifactStorePort, EnvironmentPort, IndexerPort, LockPort, PointerPort, RetrieverEvalPort,
                    ServerProbePort)
from .ragas_service import RagasService
from .review_service import ReviewService

STEPS = ("F1", "F2", "F3", "F4", "F5", "F6")
FIXED_K = 5  # 버전 비교용 고정 k — Top-k 버전끼리 Δ는 이 값으로 계산함(사용자 결정)


class RunnerService:
    """버전 실험 실행기.

    색인 · 검색은 하위 프로세스 포트(IndexerPort · RetrieverEvalPort)로, RAGAS · 검토표 · 비교표는 같은 가상환경의
    서비스로 부름. 사용 중 세대 포인터는 실행 전에 백업하고, 버전마다 검색 직후와 종료 때 되돌림.
    자동 재시도는 하지 않음 — 재색인 · 채점은 비용이 커서 사람이 --resume으로 다시 돌림.
    """

    def __init__(self, *, store: ArtifactStorePort, pointer: PointerPort, lock: LockPort, indexer: IndexerPort,
                 retriever: RetrieverEvalPort, probe: ServerProbePort, environment: EnvironmentPort,
                 ragas: RagasService, review: ReviewService, compare: CompareService, paths: RunnerPaths,
                 clock: Callable[[], datetime] | None = None):
        self.store, self.pointer, self.lock = store, pointer, lock
        self.indexer, self.retriever, self.probe, self.environment = indexer, retriever, probe, environment
        self.ragas, self.review, self.compare, self.paths = ragas, review, compare, paths
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    # ------------------------------------------------------------------ F0 준비 · 실행 전 검사

    def load_plan(self, plan_path: Path) -> tuple[PlanSpec, dict[str, Any]]:
        """계획 파일을 읽어 형식(pydantic)과 규칙(V1 ~ V4 · V10 · V11)을 검사함.

        반환값: (검사를 통과한 계획, 원문 dict).
        예외: 형식 · 규칙 위반은 QualityError("plan_rejected", exit 2).
        """

        raw = self.store.read_yaml(plan_path)
        try:
            plan = PlanSpec.model_validate(raw)
        except ValidationError as error:
            raise QualityError("plan_rejected", f"계획 파일 형식 오류: {error}", 2) from error
        rejects, _ = check_plan(plan.model_dump())
        if rejects:
            raise QualityError("plan_rejected", " / ".join(rejects), 2)
        return plan, raw

    def _unsupported(self, plan: PlanSpec) -> list[str]:
        """도구가 그 값을 실제로 받는지 확인함(V7-1 · V8 · V9). 반환값: 미지원 사유 목록."""

        _, reasons = check_plan(plan.model_dump())
        target = parse_target(plan.target)
        if target.kind == "arg" and not self.retriever.supports(target.key):
            reasons.append(f"V9 평가 스크립트가 {target.key} 인자를 아직 지원하지 않음")
        if target.kind == "env" and target.tool == "retriever" and target.key not in RETRIEVER_ENV_NAMES:
            reasons.append(f"V8 리트리버가 읽지 않는 환경변수: {target.key}")
        if target.kind == "config" and Path(target.path).name not in INDEXER_CONFIG_ENV:
            reasons.append(f"V8 인덱서가 경로를 바꿔 읽지 못하는 설정 파일: {target.path}")
        return reasons

    def _eval_set(self, plan: PlanSpec) -> tuple[Path, str]:
        """평가셋이 있고 지문이 계획과 같은지 확인함(V5 · V6). 반환값: (절대 경로, 지문)."""

        path = (self.paths.ragas_root / plan.eval_set.path).resolve()
        if not self.store.exists(path):
            raise QualityError("plan_rejected", f"V5 평가셋이 없음: {path} — build_eval_set.py를 먼저 돌림", 2)
        digest = eval_set_hash(self.store.read_json(path)["questions"])
        if digest != plan.eval_set.sha256:
            raise QualityError("plan_rejected", f"V6 평가셋 지문이 계획({plan.eval_set.sha256})과 다름: {digest}", 2)
        return path, digest

    def preflight(self, plan_path: Path) -> dict[str, Any]:
        """실행 전 검사만 하고 아무것도 바꾸지 않음(--check-only).

        반환값: 계획 이름 · 미지원 사유 · 평가셋 경로 · 지문 · 떠 있는 검색 서버 목록.
        예외: 거부 사유가 있으면 QualityError(exit 2).
        """

        plan, _ = self.load_plan(plan_path)
        eval_path, digest = self._eval_set(plan)
        return {"plan": plan.hyperparameter, "unsupported": self._unsupported(plan), "eval_set": str(eval_path),
                "eval_set_hash": digest, "running_servers": self.probe.running_servers(),
                "versions": [str(v["id"]) for v in ordered_versions(plan.model_dump())]}

    def rebuild_compare(self, plan_path: Path) -> dict[str, Any]:
        """실험 폴더에 남은 버전 결과로 비교표만 다시 만듦(채점 결과나 사람 판정을 더한 뒤 씀)."""

        plan, _ = self.load_plan(plan_path)
        return self.compare.build(self.paths.experiments_root / plan.hyperparameter,
                                  hyperparameter=plan.hyperparameter, baseline_id=self._baseline_id(plan),
                                  order=[str(v["id"]) for v in ordered_versions(plan.model_dump())])

    # ------------------------------------------------------------------ 상태 파일

    def _state_path(self, param_dir: Path) -> Path:
        """하이퍼 파라미터 폴더의 상태 파일 위치."""

        return param_dir / "state.json"

    def _save(self, param_dir: Path, state: dict[str, Any]) -> None:
        """단계 시작 직전 · 끝난 직후마다 저장함 — 끊겨도 어느 단계에서 멈췄는지 남음."""

        self.store.write_json(self._state_path(param_dir), state)

    def _mark(self, param_dir: Path, state: dict[str, Any], vid: str, step: str, status: str, **extra: Any) -> None:
        """버전 · 단계 상태를 바꾸고 바로 저장함."""

        record = state["versions"][vid]["steps"].setdefault(step, {})
        record["status"] = status
        record["at"] = self.clock().isoformat(timespec="seconds")
        record.update(json_safe(extra))
        self._save(param_dir, state)

    def _new_state(self, plan_path: Path, plan_sha: str, plan: PlanSpec, versions: list[dict[str, Any]],
                   run_date: str) -> dict[str, Any]:
        """처음 실행할 때의 상태 — 모든 단계가 대기."""

        return {
            "schema_version": 1, "plan_path": str(plan_path), "plan_sha256": plan_sha, "run_date": run_date,
            "pointer_backup": "_backup/active_generation.json",
            "versions": {
                str(v["id"]): {"order": i, "is_baseline": v["value"] == plan.baseline,
                               "thread_id": thread_id(plan.hyperparameter, str(v["id"]), run_date) if plan.reindex else None,
                               "steps": {step: {"status": WAITING} for step in STEPS}}
                for i, v in enumerate(versions)
            },
        }

    # ------------------------------------------------------------------ 실행

    def run(self, plan_path: Path, *, only: list[str] | None = None, resume: bool = False,
            stop_on_error: bool = False) -> dict[str, Any]:
        """계획 파일 하나를 실행함.

        흐름: 실행 전 검사(거부면 아무것도 바꾸지 않음) → 잠금 · 포인터 백업 → 기준 버전부터 버전마다 F1 ~ F6
              (F4 되돌리기는 실패해도 반드시 지남) → F7 비교표 → 포인터 재확인 · 잠금 해제.
        인자: only는 돌릴 버전 id(기준은 항상 포함). resume은 성공 단계를 건너뛰고 실패 · 끊긴 단계부터 다시 함.
        반환값: 버전별 단계 상태 · 비교표 경로 · 경고.
        예외: 실행 전 검사 실패는 QualityError(exit 2). 단계 실패는 상태에 남기고 다음 버전으로 감.
        부수효과: 재색인 · Groq · 평가자 호출, experiments/ 아래 파일 생성, 포인터를 잠시 바꿨다 되돌림.
        """

        plan, raw = self.load_plan(plan_path)
        unsupported = self._unsupported(plan)
        eval_path, eval_digest = self._eval_set(plan)
        servers = self.probe.running_servers()
        if servers:
            raise QualityError("plan_rejected",
                               f"V14 같은 DATA_ROOT를 보는 검색 API 서버가 떠 있음: {servers} — 실험 동안 내림", 2)
        param_dir = self.paths.experiments_root / plan.hyperparameter
        plan_sha = hashlib.sha256(json.dumps(raw, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        versions = ordered_versions(plan.model_dump(), only)
        state_path = self._state_path(param_dir)
        if resume and self.store.exists(state_path):
            state = self.store.read_json(state_path)
            if state.get("plan_sha256") != plan_sha:
                raise QualityError("plan_rejected", "계획 파일이 바뀐 채 --resume 할 수 없음 — 새로 실행하거나 되돌림", 2)
            for v in versions:  # 이번에 처음 고른 버전은 대기 상태로 더함
                state["versions"].setdefault(str(v["id"]), self._new_state(
                    plan_path, plan_sha, plan, [v], state["run_date"])["versions"][str(v["id"])])
        else:
            state = self._new_state(plan_path, plan_sha, plan, versions, self.clock().strftime("%Y%m%d"))

        self.lock.acquire()
        backup_path = param_dir / state["pointer_backup"]
        try:
            # 처음 백업한 원래 값만 지킴 — 이어 하기에서 백업을 덮어쓰면 실험 세대를 '원래 값'으로 착각하게 됨
            if not self.store.exists(backup_path):
                self.store.write_json(backup_path, self.pointer.read())
            backup = self.store.read_json(backup_path)
            self._restore(backup)  # 앞 실행이 강제 종료돼 포인터가 실험 세대에 남았을 때를 대비함
            state["pointer_backup_generation"] = backup.get("generation")
            self._save(param_dir, state)
            for version in versions:
                vid = str(version["id"])
                if unsupported:
                    for step in STEPS:
                        self._mark(param_dir, state, vid, step, UNSUPPORTED, detail=" / ".join(unsupported))
                    continue
                ok = self._run_version(plan, version, param_dir, state, backup, eval_path, eval_digest, resume)
                if not ok and stop_on_error:
                    break
            result_compare = None
            if not unsupported:
                result_compare = self.compare.build(
                    param_dir, hyperparameter=plan.hyperparameter, baseline_id=self._baseline_id(plan),
                    order=[str(v["id"]) for v in ordered_versions(plan.model_dump())])
        finally:
            restored = self._restore(self.store.read_json(backup_path)) if self.store.exists(backup_path) else None
            state["final_pointer_check"] = restored
            self._save(param_dir, state)
            self.lock.release()
        return {"hyperparameter": plan.hyperparameter, "unsupported": unsupported,
                "versions": {vid: {s: v["steps"][s]["status"] for s in STEPS} for vid, v in state["versions"].items()},
                "compare": None if result_compare is None else str(param_dir / "compare.md"),
                "warnings": [] if result_compare is None else result_compare["warnings"],
                "pointer_restored": restored}

    @staticmethod
    def _baseline_id(plan: PlanSpec) -> str:
        """기준 값과 같은 버전의 id."""

        return next(str(v.id) for v in plan.versions if v.value == plan.baseline)

    def _restore(self, backup: dict[str, Any]) -> dict[str, Any]:
        """포인터가 백업과 다르면 백업으로 되돌리고, 확인 결과를 돌려줌.

        반환값: restored(실제로 되돌렸는지) · generation · matches(지금 포인터 내용 = 백업 내용) dict.
        예외: 되돌린 뒤에도 내용이 다르면 QualityError("restore_failed") — 사람이 손으로 복원해야 함.
        """

        changed = self.pointer.read() != backup
        if changed:
            self.pointer.write(backup)
        current = self.pointer.read()
        if current != backup:
            raise QualityError("restore_failed",
                               f"포인터 복원 확인 실패 — 백업 파일로 손으로 되돌려야 함(세대 {backup.get('generation')})")
        return {"restored": changed, "generation": current.get("generation"), "matches": True,
                "sha256": self.pointer.sha256(), "at": self.clock().isoformat(timespec="seconds")}

    def _done(self, state: dict[str, Any], vid: str, step: str, artifact: Path | None) -> bool:
        """이어 하기에서 건너뛸 단계인지 — 성공이고 산출 파일이 실제로 있어야 함."""

        record = state["versions"][vid]["steps"].get(step, {})
        return record.get("status") == SUCCESS and (artifact is None or self.store.exists(artifact))

    def _run_version(self, plan: PlanSpec, version: dict[str, Any], param_dir: Path, state: dict[str, Any],
                     backup: dict[str, Any], eval_path: Path, eval_digest: str, resume: bool) -> bool:
        """버전 하나의 F1 ~ F6. 반환값: 모든 단계가 성공했는지.

        F2 · F3에서 실패해도 F4 되돌리기는 반드시 지남. F5가 실패하면 F6은 건너뜀(ragas.json이 필요함).
        """

        vid = str(version["id"])
        vdir = param_dir / vid
        logs = vdir / "logs"
        target = parse_target(plan.target)
        config_path = vdir / "config.json"
        retriever_out = vdir / "retriever.json"
        version_pointer = vdir / "active_generation.version.json"
        all_ok = True
        try:
            # F1 설정 적용
            if not (resume and self._done(state, vid, "F1", config_path)):
                self._mark(param_dir, state, vid, "F1", RUNNING)
                config = self._apply(plan, version, target, vdir, eval_path, eval_digest, backup)
                self.store.write_json(config_path, config)
                self._mark(param_dir, state, vid, "F1", SUCCESS, artifact=config_path)
            config = self.store.read_json(config_path)

            # F2 색인(재색인 계획만)
            if plan.reindex:
                if resume and self._done(state, vid, "F2", version_pointer):
                    # 앞 실행에서 만든 세대로 포인터를 다시 돌려놓아야 F3가 그 세대를 읽음
                    if not self._done(state, vid, "F3", retriever_out):
                        self.pointer.write(self.store.read_json(version_pointer))
                else:
                    self._mark(param_dir, state, vid, "F2", RUNNING, thread_id=state["versions"][vid]["thread_id"])
                    generation = self.indexer.reindex(state["versions"][vid]["thread_id"], config["indexer_env"], logs)
                    published = self.pointer.read()
                    if published.get("generation") != generation:
                        raise StepError("E-OUT", f"게시된 세대({generation})와 포인터({published.get('generation')})가 다름")
                    self.store.write_json(version_pointer, published)
                    self.store.append_text(self.paths.experiments_root / "_registry.csv",
                                           f"{generation},{state['versions'][vid]['thread_id']},{plan.hyperparameter},"
                                           f"{vid},{backup.get('generation')},{self.clock().isoformat(timespec='seconds')}\n")
                    self._mark(param_dir, state, vid, "F2", SUCCESS, generation=generation)
                config["generation"] = self.store.read_json(version_pointer)["generation"]
                config["base_generation"] = backup.get("generation")
            else:
                self._mark(param_dir, state, vid, "F2", SKIPPED, detail="재색인 아님 — 사용 중 세대를 그대로 씀")
                config["generation"] = self.pointer.read().get("generation")
            self.store.write_json(config_path, config)

            # F3 검색 · 코드 채점
            if not (resume and self._done(state, vid, "F3", retriever_out)):
                self._mark(param_dir, state, vid, "F3", RUNNING)
                args = ["--questions", str(eval_path), "--generate-answer", "--out", str(retriever_out),
                        "--version-label", vid, "--config-snapshot", str(config_path), "--fixed-k", str(FIXED_K),
                        *config["retriever_args"]]
                self.retriever.run(args, config["retriever_env"], logs)
                if not self.store.exists(retriever_out):
                    raise StepError("E-OUT", f"검색 결과 파일이 없음: {retriever_out}")
                self.store.read_json(retriever_out)  # 깨진 JSON이면 여기서 실패로 잡음
                self._mark(param_dir, state, vid, "F3", SUCCESS, artifact=retriever_out)
        except StepError as error:
            all_ok = False
            failing = next((s for s in ("F1", "F2", "F3") if state["versions"][vid]["steps"][s]["status"] == RUNNING), "F1")
            self._mark(param_dir, state, vid, failing, FAILED, code=error.code, detail=error.message)
        except QualityError as error:
            all_ok = False
            failing = next((s for s in ("F1", "F2", "F3") if state["versions"][vid]["steps"][s]["status"] == RUNNING), "F1")
            self._mark(param_dir, state, vid, failing, FAILED, code="E-CFG", detail=error.message)
        finally:
            # F4 되돌리기 — 성공 · 실패 · 중단 모두 지남(RAGAS · 검토표는 로그만 읽어 포인터가 필요 없음)
            self._mark(param_dir, state, vid, "F4", RUNNING)
            check = self._restore(backup)
            if self.store.exists(config_path):
                config = self.store.read_json(config_path)
                config["pointer_restored"] = check
                self.store.write_json(config_path, config)
            self._mark(param_dir, state, vid, "F4", SUCCESS, **check)
        if not all_ok:
            for step in ("F5", "F6"):
                self._mark(param_dir, state, vid, step, SKIPPED, detail="앞 단계 실패")
            return False

        # F5 RAGAS 채점
        ragas_out = vdir / "ragas.json"
        if not (resume and self._done(state, vid, "F5", ragas_out)):
            self._mark(param_dir, state, vid, "F5", RUNNING)
            try:
                report = self.ragas.score_file(retriever_out, ragas_out, provider=plan.scoring.ragas_provider,
                                               repeat=plan.scoring.ragas_repeat)
            except Exception as error:  # 평가자 연결 실패 등 — 검색 결과는 남기고 이 버전만 실패로 둠
                self._mark(param_dir, state, vid, "F5", FAILED, code="E-API", detail=f"{type(error).__name__}: {error}")
                self._mark(param_dir, state, vid, "F6", SKIPPED, detail="RAGAS 결과 없음")
                return False
            self._mark(param_dir, state, vid, "F5", SUCCESS, artifact=ragas_out, scored=report["scored"],
                       failed_scores=len(report["failed_scores"]))

        # F6 검토표 내보내기 — 판정은 기다리지 않음(사람이 채운 뒤 human_review.py agree)
        review_out = vdir / "review.csv"
        if not (resume and self._done(state, vid, "F6", review_out)):
            self._mark(param_dir, state, vid, "F6", RUNNING)
            try:
                rows = self.review.export(retriever_out, ragas_out, review_out, version=vid)
            except QualityError as error:
                self._mark(param_dir, state, vid, "F6", FAILED, code=error.code, detail=error.message)
                return False
            self._mark(param_dir, state, vid, "F6", SUCCESS, artifact=review_out, rows=rows)
        return True

    def _apply(self, plan: PlanSpec, version: dict[str, Any], target: Any, vdir: Path, eval_path: Path,
               eval_digest: str, backup: dict[str, Any]) -> dict[str, Any]:
        """F1 — 바꾸는 종류별로 하위 프로세스에 줄 값을 만들고 설정 스냅샷(config.json)을 꾸림.

        config_file: 원본을 버전 폴더에 복사해 대상 키만 바꾸고, 인덱서에 복사본 절대 경로를 환경변수로 넘김.
        env: 하위 프로세스 환경변수에만 얹음(원본 .env는 열지 않음). code_arg: 추가 인자로 넘김.
        예외: 복사본이 원본과 2곳 이상 다르면 StepError("E-CFG") — 한 번에 하나만 바꾸는 원칙.
        """

        value = version["value"]
        indexer_env: dict[str, str] = {}
        retriever_env = {"DATA_ROOT": str(self.paths.data_root), "AUDIT_LOG_PATH": str(vdir / "logs" / "audit.jsonl")}
        retriever_args: list[str] = []
        copy_info: dict[str, Any] = {}
        if target.kind == "config":
            original_path = self.paths.indexer_dir / target.path
            original = self.store.read_json(original_path)
            changed = set_json_path(original, target.key, value)
            differences = leaf_differences(original, changed)
            if len(differences) > 1:
                raise StepError("E-CFG", f"설정 복사본이 원본과 {len(differences)}곳 다름: {differences}")
            copy_path = vdir / Path(target.path).name
            self.store.write_json(copy_path, changed)
            indexer_env[INDEXER_CONFIG_ENV[copy_path.name]] = str(copy_path.resolve())
            copy_info = {"original": str(original_path), "copy": str(copy_path), "differences": differences,
                         "copy_sha256": hashlib.sha256(self.store.read_text(copy_path).encode("utf-8")).hexdigest()}
        elif target.kind == "env":
            (indexer_env if target.tool == "indexer" else retriever_env)[target.key] = str(value)
        elif target.kind == "arg":
            retriever_args += [target.key, str(value)]
        top_k = int(value) if target.key == "--top-k" else 5
        return {
            "param": plan.hyperparameter, "version": str(version["id"]), "value": value, "baseline": plan.baseline,
            "is_baseline": value == plan.baseline, "apply": plan.apply, "target": plan.target, "reindex": plan.reindex,
            "indexer_env": indexer_env, "retriever_env": retriever_env, "retriever_args": retriever_args,
            "config_copy": copy_info, "base_generation": backup.get("generation"),
            "eval_set_path": str(eval_path), "eval_set_hash": eval_digest,
            "provider": plan.scoring.ragas_provider, "repeat": plan.scoring.ragas_repeat,
            "human_threshold": plan.scoring.human_pass_threshold,
            "top_k": top_k, "metric_k": top_k, "fixed_k": FIXED_K,
            "environment": self.environment.snapshot(),
            "created_at": self.clock().isoformat(timespec="seconds"),
        }
