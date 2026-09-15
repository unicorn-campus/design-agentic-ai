from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import SecretStr


RETRIEVER_ROOT = Path(__file__).resolve().parents[1]
VECTOR_ROOT = RETRIEVER_ROOT.parent


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def settings_module(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    module = _load(RETRIEVER_ROOT / "app/settings.py", "retriever_settings_contract")
    for name, value in list(module.os.environ.items()):
        if name in module._SPECS or name == "ANTHROPIC_API_KEY":
            monkeypatch.delenv(name, raising=False)
    app_dir = tmp_path / "vector" / "retriever"
    app_dir.mkdir(parents=True)
    monkeypatch.setattr(module, "APP_DIR", app_dir)
    monkeypatch.setattr(module, "LAB_ROOT", tmp_path)
    return module


def test_settings_files_are_byte_identical() -> None:
    indexer = VECTOR_ROOT / "indexer/app/settings.py"
    retriever = VECTOR_ROOT / "retriever/app/settings.py"
    assert indexer.read_bytes() == retriever.read_bytes()


def test_precedence_and_blank_values(settings_module, monkeypatch: pytest.MonkeyPatch) -> None:
    module = settings_module
    (module.LAB_ROOT / ".env").write_text("CHROMA_COLLECTION=lab\n", encoding="utf-8")
    (module.APP_DIR / ".env").write_text("CHROMA_COLLECTION=app\n", encoding="utf-8")
    monkeypatch.setenv("CHROMA_COLLECTION", "environment")

    settings = module.load_settings({"CHROMA_COLLECTION": "cli"})
    assert settings.CHROMA_COLLECTION == "cli"
    assert settings.sources["CHROMA_COLLECTION"] == "cli"

    settings = module.load_settings({"CHROMA_COLLECTION": "   "})
    assert settings.CHROMA_COLLECTION == "environment"
    monkeypatch.setenv("CHROMA_COLLECTION", " ")
    settings = module.load_settings()
    assert settings.CHROMA_COLLECTION == "app"

    (module.APP_DIR / ".env").write_text("CHROMA_COLLECTION=\n", encoding="utf-8")
    settings = module.load_settings()
    assert settings.CHROMA_COLLECTION == "lab"


def test_defaults_and_app_specific_chroma_path(settings_module) -> None:
    settings = settings_module.load_settings()
    assert settings.CHROMA_COLLECTION == "card_docs"
    assert settings.API_HOST == "127.0.0.1"
    assert settings.CHROMA_PATH == settings_module.APP_DIR.parent / "indexer/data/chroma"
    assert settings.sources["CHROMA_COLLECTION"] == "default"
    with pytest.raises(TypeError):
        settings.values["CHROMA_COLLECTION"] = "changed"


def test_secret_str_and_alias_source_do_not_expose_value(
    settings_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "contract-secret-must-not-appear"
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)
    settings = settings_module.load_settings()
    assert isinstance(settings.CLAUDE_API_KEY, SecretStr)
    assert settings.CLAUDE_API_KEY.get_secret_value() == secret
    assert settings.sources["CLAUDE_API_KEY"] == "environment:ANTHROPIC_API_KEY"
    assert secret not in repr(settings)


@pytest.mark.parametrize("name,value", [("API_PORT", "0"), ("TOP_K_DEFAULT", "abc")])
def test_invalid_integer_mentions_only_variable_name(settings_module, name: str, value: str) -> None:
    with pytest.raises(settings_module.LLMConfigError) as caught:
        settings_module.load_settings({name: value})
    assert name in str(caught.value)
    assert value not in str(caught.value)


def test_only_allowed_environment_names_are_read(settings_module, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UNRELATED_PASSWORD", "must-not-be-copied")
    settings = settings_module.load_settings()
    assert "UNRELATED_PASSWORD" not in settings.values
    assert "must-not-be-copied" not in repr(settings)
