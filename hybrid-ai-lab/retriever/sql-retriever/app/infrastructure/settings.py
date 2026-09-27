"""작업 디렉터리에 의존하지 않고 공통 .env를 읽습니다."""
from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
LAB_ROOT = ROOT.parents[1]
MODEL = "openai/gpt-oss-120b"


@dataclass(frozen=True)
class Settings:
    db_dsn: str = field(repr=False)
    db_password: str = field(repr=False)
    api_key: str = field(repr=False)
    model: str = MODEL
    statement_timeout_ms: int = 5000
    llm_timeout_seconds: float = 30.0
    max_tokens: int = 2500


def load_settings(env_path: Path | None = None) -> Settings:
    values = dotenv_values(env_path or LAB_ROOT / ".env", interpolate=False)

    def get(key, default=""):
        return os.environ.get(key, values.get(key) or default)

    dsn = get("SQL_RETRIEVER_DB_DSN") or get("S22_DB_DSN")
    password = get("SQL_RETRIEVER_DB_PASSWORD") or get("S22_DB_PASSWORD")
    if not dsn:
        dsn = "host=localhost port=5432 dbname=cardlab user=lab_user"
        if not password:
            compose = LAB_ROOT / "rdb" / "compose.yml"
            if compose.is_file():
                for line in compose.read_text(encoding="utf-8").splitlines():
                    name, separator, value = line.strip().partition(":")
                    if separator and name == "POSTGRES_PASSWORD":
                        password = value.strip().strip("\"'")
                        break
    try:
        timeout = int(get("SQL_RETRIEVER_STATEMENT_TIMEOUT_MS", "5000"))
        llm_timeout = float(get("SQL_RETRIEVER_LLM_TIMEOUT_SECONDS", "30"))
        tokens = int(get("SQL_RETRIEVER_MAX_TOKENS", "2500"))
        if not 100 <= timeout <= 60000 or not 1 <= llm_timeout <= 120 or not 128 <= tokens <= 8192:
            raise ValueError()
    except ValueError as error:
        raise ValueError("SQL 검색기의 시간·토큰 제한 설정을 확인해 주세요.") from error
    return Settings(dsn, password, get("GROQ_API_KEY"), MODEL, timeout, llm_timeout, tokens)
