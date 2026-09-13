"""S3.2 코드를 복사하지 않고 별도 패키지 이름으로 불러오는 연결 계층."""

from functools import lru_cache
import importlib
from pathlib import Path
import sys
import types


S33_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = S33_ROOT.parent
S32_ROOT = LAB_ROOT / "s3.2"
S32_SRC = S32_ROOT / "src"
_PACKAGE = "_s32_runtime"


@lru_cache(maxsize=None)
def load_s32_module(name: str):
    """S3.2의 ``src`` 모듈을 S3.3 ``src``와 충돌 없이 불러옴."""
    if not S32_SRC.is_dir():
        raise FileNotFoundError(f"S3.2 소스 디렉터리를 찾을 수 없음: {S32_SRC}")
    if _PACKAGE not in sys.modules:
        package = types.ModuleType(_PACKAGE)
        package.__path__ = [str(S32_SRC)]
        package.__package__ = _PACKAGE
        sys.modules[_PACKAGE] = package
    return importlib.import_module(f"{_PACKAGE}.{name}")


def configure_s32(
    *,
    db_path: Path | str | None = None,
    collection: str = "card_docs_ref",
    backend: str = "sentence-transformers",
    model: str = "nlpai-lab/KURE-v1",
):
    """S3.2 검색 설정을 기존 인덱스 위치에 맞게 구성함."""
    helpers = load_s32_module("helpers")
    path = Path(db_path) if db_path else S32_ROOT / "data/chroma/group1"
    return helpers.configure(
        db_path=path,
        collection=collection,
        backend=backend,
        model=model,
    )


def get_search(reference: bool = True):
    """기존 S3.2 검색 함수를 반환함."""
    module_name = "retrieval_ref" if reference else "retrieval"
    return load_s32_module(module_name).search


def ask_llm(system: str, user: str, max_tokens: int = 500):
    """S3.2의 Claude 호출 어댑터를 그대로 사용함."""
    return load_s32_module("llm_client").ask_llm(system, user, max_tokens=max_tokens)

