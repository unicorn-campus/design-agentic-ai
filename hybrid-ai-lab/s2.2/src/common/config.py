"""저장소 기준 경로와 설정. 비밀값을 repr/로그에 노출하지 않음."""
from dataclasses import dataclass, field
from pathlib import Path
import os
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    db_dsn: str = field(repr=False)
    db_password: str = field(repr=False)
    api_key: str = field(repr=False)
    model: str = 'claude-sonnet-5'
    base_date: str = '2026-08-31'


def _value(values: dict, name: str, default: str = '') -> str:
    """.env 값을 우선하고 없으면 프로세스 환경변수와 기본값을 사용함."""
    return values.get(name) or os.getenv(name, default)


def _local_rdb_password() -> str:
    """공통 RDB compose 설정의 로컬 실습용 비밀번호를 중복 하드코딩 없이 읽음."""
    compose_path = ROOT.parent / 'rdb' / 'compose.yml'
    if not compose_path.exists():
        return ''
    for line in compose_path.read_text(encoding='utf-8').splitlines():
        key, separator, value = line.strip().partition(':')
        if separator and key == 'POSTGRES_PASSWORD':
            return value.strip().strip('"\'')
    return ''


def load_settings() -> Settings:
    env_path = ROOT / '.env'
    if not env_path.exists():
        env_path = ROOT.parent / '.env'
    values = dotenv_values(env_path)
    # 지정한 저장소 .env의 키를 우선 사용. 파일을 수정하지 않음.
    key = _value(values, 'CLAUDE_API_KEY')
    configured_dsn = _value(values, 'S22_DB_DSN')
    dsn = configured_dsn or 'host=localhost port=5432 dbname=cardlab user=lab_user'
    password = _value(values, 'S22_DB_PASSWORD')
    if not configured_dsn and not password:
        password = _local_rdb_password()
    return Settings(dsn, password, key)
