"""설정 로더 시험. 기본값·환경변수 우선순위·상대 경로 해석을 확인함."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.infrastructure.settings import ROOT, Settings, load_settings

# 설정 키가 실제 환경에 남아 있으면 기본값 시험이 흔들리므로 시험마다 지움
ENV_KEYS = (
    "DATA_ROOT",
    "AUDIT_LOG_PATH",
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "EMBED_MODEL",
    "EMBED_DEVICE",
    "EMBED_DIMENSION",
    "HF_LOCAL_FILES_ONLY",
    "TIMEOUT_C01",
    "TIME_BUDGET_SECONDS",
    "MAX_TURNS",
    "GRADE_UPPER",
    "API_HOST",
    "API_PORT",
)


@pytest.fixture()
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """설정 관련 환경변수를 모두 지워 .env·기본값만 보이게 함."""

    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture()
def empty_env_file(tmp_path: Path) -> Path:
    """값이 없는 .env 파일 경로를 줌(파일을 읽어도 기본값이 남는지 확인용)."""

    path = tmp_path / ".env"
    path.write_text("# 비어 있음\n", encoding="utf-8")
    return path


def test_defaults_match_design_values(clean_env: None, empty_env_file: Path) -> None:
    """.env와 환경변수가 비면 설계 기본값을 그대로 씀."""

    settings = load_settings(empty_env_file)

    assert settings.embed_model == "nlpai-lab/KURE-v2"
    assert settings.embed_dimension == 768
    assert settings.hf_local_files_only is True
    assert settings.groq_model == "openai/gpt-oss-120b"
    assert settings.groq_reasoning_effort == "low"
    assert (settings.timeout_c01, settings.timeout_c02) == (2.5, 1.5)
    assert (settings.timeout_c03, settings.timeout_c04) == (1.2, 2.5)
    assert settings.time_budget_seconds == 30.0
    assert (settings.max_turns, settings.max_llm_calls, settings.max_rewrites) == (6, 16, 2)
    assert (settings.api_host, settings.api_port) == ("127.0.0.1", 8020)


def test_relative_paths_resolve_against_project_root(clean_env: None, empty_env_file: Path) -> None:
    """상대 경로 기본값은 작업 디렉터리가 아니라 프로젝트 루트 기준 절대 경로로 바뀜."""

    settings = load_settings(empty_env_file)

    assert settings.data_root.is_absolute()
    assert settings.data_root == (ROOT / ".." / ".." / "indexer" / "vector-bm25" / "data").resolve()
    assert settings.audit_log_path == ROOT / "logs" / "audit.jsonl"


def test_env_file_values_are_read(clean_env: None, tmp_path: Path) -> None:
    """.env에 적은 값이 기본값을 대신함."""

    path = tmp_path / ".env"
    path.write_text("API_PORT=7777\nEMBED_DEVICE=cpu\nHF_LOCAL_FILES_ONLY=false\n", encoding="utf-8")

    settings = load_settings(path)

    assert settings.api_port == 7777
    assert settings.embed_device == "cpu"
    assert settings.hf_local_files_only is False


def test_environment_variable_beats_env_file(
    clean_env: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """같은 키가 양쪽에 있으면 환경변수를 씀(컨테이너 주입값이 파일보다 우선)."""

    path = tmp_path / ".env"
    path.write_text("API_PORT=7777\nGRADE_UPPER=0.5\n", encoding="utf-8")
    monkeypatch.setenv("API_PORT", "9999")

    settings = load_settings(path)

    assert settings.api_port == 9999
    assert settings.grade_upper == 0.5


def test_absolute_path_is_kept(clean_env: None, tmp_path: Path) -> None:
    """절대 경로를 주면 그대로 씀(루트를 앞에 붙이지 않음)."""

    data_root = tmp_path / "index-data"
    path = tmp_path / ".env"
    path.write_text(f"DATA_ROOT={data_root}\n", encoding="utf-8")

    assert load_settings(path).data_root == data_root


def test_budget_policy_conversion(clean_env: None, tmp_path: Path) -> None:
    """설정값이 시간 예산 규칙(BudgetPolicy)으로 옮겨지고 커넥터 최악값은 타임아웃 그대로임."""

    path = tmp_path / ".env"
    path.write_text("TIMEOUT_C02=3.0\nMAX_TURNS=4\nTIME_BUDGET_SECONDS=20\n", encoding="utf-8")

    policy = load_settings(path).budget_policy()

    assert policy.total_seconds == 20.0
    assert policy.max_turns == 4
    assert policy.connector_worst_seconds["C-02"] == 3.0
    assert policy.connector_worst_seconds["C-01"] == 2.5


def test_grade_thresholds_conversion(clean_env: None, tmp_path: Path) -> None:
    """채점 기준 설정값이 GradeThresholds로 옮겨짐."""

    path = tmp_path / ".env"
    path.write_text("GRADE_UPPER=0.8\nGRADE_LOWER=0.2\nGRADE_MIN_OVERLAP=2\n", encoding="utf-8")

    thresholds = load_settings(path).grade_thresholds()

    assert (thresholds.upper, thresholds.lower, thresholds.min_overlap) == (0.8, 0.2, 2)
    assert thresholds.min_gap == 0.05


def test_invalid_number_raises_value_error(clean_env: None, tmp_path: Path) -> None:
    """숫자로 읽을 수 없는 값은 ValueError로 막고 키 이름만 알려 줌."""

    path = tmp_path / ".env"
    path.write_text("API_PORT=여덟천이십\n", encoding="utf-8")

    with pytest.raises(ValueError, match="API_PORT"):
        load_settings(path)


def test_out_of_range_number_raises_value_error(clean_env: None, tmp_path: Path) -> None:
    """허용 범위를 벗어난 포트는 서버를 띄우기 전에 막음."""

    path = tmp_path / ".env"
    path.write_text("API_PORT=99999\n", encoding="utf-8")

    with pytest.raises(ValueError, match="API_PORT"):
        load_settings(path)


def test_secret_is_hidden_in_repr(clean_env: None, tmp_path: Path) -> None:
    """Groq 비밀키는 repr·로그 출력에 나오지 않음."""

    path = tmp_path / ".env"
    path.write_text("GROQ_API_KEY=not-a-real-key\n", encoding="utf-8")

    settings: Settings = load_settings(path)

    assert settings.groq_api_key == "not-a-real-key"
    assert "not-a-real-key" not in repr(settings)
