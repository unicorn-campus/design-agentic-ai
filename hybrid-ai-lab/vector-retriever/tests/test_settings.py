from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import SecretStr


RETRIEVER_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = RETRIEVER_ROOT.parent


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
    indexer = _load(LAB_ROOT / "indexer/vector-bm25/app/settings.py", "indexer_settings_contract")
    retriever = _load(LAB_ROOT / "vector-retriever/app/settings.py", "retriever_settings_shared_contract")
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
    # Indexer는 색인만 담당하므로 검색·답변·LLM·API 계열 키를 두지 않음.
    retriever_only = {
        "RERANK_MODEL",
        "LLM_PROVIDER",
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "CLAUDE_API_KEY",
        "CLAUDE_MODEL",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "LLM_TIMEOUT_SECONDS",
        "LLM_MAX_TOKENS_ANSWER",
        "MAX_LLM_CALLS_CLI",
        "MAX_LLM_CALLS_PER_REQUEST",
        "MAX_LLM_CALLS_TOTAL",
        "REQUEST_TIMEOUT_SECONDS",
        "API_HOST",
        "API_PORT",
        "TOP_K_DEFAULT",
        "CANDIDATE_MULTIPLIER",
        "VECTOR_SEARCH_STRATEGY",
        "MMR_FETCH_MULTIPLIER",
        "MMR_LAMBDA_MULT",
        "HYBRID_WEIGHT_BM25",
        "HYBRID_WEIGHT_VECTOR",
        "ANSWER_GATE_THRESHOLD",
        "RERANK_MAX_LENGTH",
        "TRANSFORM_MODE",
        "TRANSFORM_GATE_THRESHOLD",
        "TRANSFORM_RRF_K",
        "TRANSFORM_ORIGINAL_WEIGHT",
        "TRANSFORM_ORIGINAL_WEIGHT_DECOMPOSITION",
        "TRANSFORM_PER_QUERY_TOP_K",
        "TRANSFORM_MULTI_COUNT",
        "TRANSFORM_DECOMPOSITION_MIN",
        "TRANSFORM_DECOMPOSITION_MAX",
        "TRANSFORM_CACHE_PATH",
        "LLM_MAX_TOKENS_ROUTER",
        "MAX_REPAIRS",
        "TIMEOUT_VECTOR_SEARCH",
        "TIMEOUT_RERANK",
    }

    assert set(indexer._SPECS) | retriever_only == set(retriever._SPECS) | indexer_only
    for name in set(retriever._SPECS) - retriever_only:
        retriever_spec = retriever._SPECS[name]
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
    assert settings.VECTOR_SEARCH_STRATEGY == "similarity"
    assert settings.MMR_FETCH_MULTIPLIER == 2
    assert settings.MMR_LAMBDA_MULT == 0.5
    assert settings.TRANSFORM_GATE_THRESHOLD == 0.86
    assert settings.API_HOST == "127.0.0.1"
    assert settings.CHROMA_PATH == settings_module.APP_DIR.parent / "indexer/vector-bm25/data/chroma"
    assert settings.sources["CHROMA_COLLECTION"] == "default"
    with pytest.raises(TypeError):
        settings.values["CHROMA_COLLECTION"] = "changed"


def test_vector_store_backend_rejects_unknown_value(settings_module) -> None:
    with pytest.raises(settings_module.LLMConfigError):
        settings_module.load_settings({"VECTOR_STORE_BACKEND": "unknown"})


def test_mmr_settings_accept_supported_boundaries(settings_module) -> None:
    settings = settings_module.load_settings(
        {
            "VECTOR_SEARCH_STRATEGY": "mmr",
            "MMR_FETCH_MULTIPLIER": "3",
            "MMR_LAMBDA_MULT": "0",
        }
    )

    assert settings.VECTOR_SEARCH_STRATEGY == "mmr"
    assert settings.MMR_FETCH_MULTIPLIER == 3
    assert settings.MMR_LAMBDA_MULT == 0.0


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("VECTOR_SEARCH_STRATEGY", "unknown"),
        ("MMR_FETCH_MULTIPLIER", "0"),
        ("MMR_LAMBDA_MULT", "-0.1"),
        ("MMR_LAMBDA_MULT", "1.1"),
    ],
)
def test_mmr_settings_reject_invalid_values(settings_module, name: str, value: str) -> None:
    with pytest.raises(settings_module.LLMConfigError):
        settings_module.load_settings({name: value})


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
