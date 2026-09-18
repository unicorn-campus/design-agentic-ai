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


def test_shared_settings_keep_the_same_contract() -> None:
    indexer = _load(VECTOR_ROOT / "indexer/app/settings.py", "indexer_settings_contract")
    retriever = _load(VECTOR_ROOT / "retriever/app/settings.py", "retriever_settings_shared_contract")
    indexer_only = {
        "EMBED_BATCH_SIZE",
        "CHUNK_MAX_CHARS",
        "CHUNK_OVERLAP",
        "CHUNK_D2_OVERLAP",
        "CHUNK_TURNS_PER_CHUNK",
        "CHUNK_OVERLAP_TURNS",
        "MAX_INPUT_TOKENS",
        "TIMEOUT_PDF_PER_FILE",
        "TIMEOUT_CHUNK_PER_DOC",
        "TIMEOUT_EMBED_BATCH",
        "KOREAN_OOV_MIN_COUNT",
        "KOREAN_OOV_MIN_SCORE",
    }

    assert set(indexer._SPECS) == set(retriever._SPECS) | indexer_only
    for name, retriever_spec in retriever._SPECS.items():
        indexer_spec = indexer._SPECS[name]
        indexer_default = indexer_spec.default
        retriever_default = retriever_spec.default
        if callable(indexer_default) and callable(retriever_default):
            assert indexer_default.__name__ == retriever_default.__name__
        else:
            assert indexer_default == retriever_default
        assert indexer_spec.parser.__name__ == retriever_spec.parser.__name__
        assert indexer_spec.secret == retriever_spec.secret
        assert indexer_spec.aliases == retriever_spec.aliases


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
    assert settings.VECTOR_STORE_BACKEND == "chroma"
    assert settings.CHROMA_COLLECTION == "card_docs"
    assert settings.API_HOST == "127.0.0.1"
    assert settings.CHROMA_PATH == settings_module.APP_DIR.parent / "indexer/data/chroma"
    assert settings.sources["CHROMA_COLLECTION"] == "default"
    with pytest.raises(TypeError):
        settings.values["CHROMA_COLLECTION"] = "changed"


def test_vector_store_backend_rejects_unknown_value(settings_module) -> None:
    with pytest.raises(settings_module.LLMConfigError):
        settings_module.load_settings({"VECTOR_STORE_BACKEND": "unknown"})


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
