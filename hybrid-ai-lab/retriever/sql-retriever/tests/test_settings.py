from pathlib import Path

from app.infrastructure.settings import LAB_ROOT, load_settings


def test_common_env_path_is_independent_of_working_directory():
    assert LAB_ROOT.name == "hybrid-ai-lab"
    assert (LAB_ROOT / "rdb" / "compose.yml").is_file()


def test_settings_does_not_expose_secrets_and_env_has_precedence(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("GROQ_API_KEY=file-secret\nSQL_RETRIEVER_DB_PASSWORD=db-secret\n", encoding="utf-8")
    monkeypatch.setenv("GROQ_API_KEY", "runtime-secret")
    settings = load_settings(env)
    assert settings.api_key == "runtime-secret"
    assert "secret" not in repr(settings)
    assert settings.model == "openai/gpt-oss-120b"


def test_missing_key_does_not_block_settings(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    settings = load_settings(tmp_path / "missing.env")
    assert settings.api_key == ""
