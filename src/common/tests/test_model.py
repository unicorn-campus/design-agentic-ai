from types import SimpleNamespace

from help_desk_runtime.model import ModelClientAdapter


def test_model_adapter_passes_runtime_configuration() -> None:
    captured: dict[str, object] = {}

    def initializer(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    settings = SimpleNamespace(
        llm_model="model-from-env",
        llm_provider="provider-from-env",
        llm_api_key=SimpleNamespace(get_secret_value=lambda: "secret-from-env"),
        llm_reasoning_enabled=True,
        llm_temperature=None,
        llm_max_tokens=None,
    )
    ModelClientAdapter(settings, initializer).create()
    assert captured["model"] == "model-from-env"
    assert captured["model_provider"] == "provider-from-env"
    assert captured["reasoning"] is True
