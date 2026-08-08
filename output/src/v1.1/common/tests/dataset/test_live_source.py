"""실제 원천을 부르는 시험. 기본 실행에서 빠져 있고 `-m live_call`로만 돎(D-07).

물리 표 · 열 이름이 정해지고 접속 정보가 들어온 뒤에만 통과함.
그 전에는 무엇이 없는지 알리며 건너뜀 — 없는 값을 지어내 통과시키지 않음.
"""

from __future__ import annotations

import pytest

from common.config import Settings
from common.dataset.live_reader import LiveSourceReader, missing_inputs_for
from common.dataset.paths import spec_of
from common.dataset.readers import read_member_profile
from common.dataset.source_port import Origin


@pytest.mark.live_call
def test_reads_one_member_profile_from_the_real_source(dataset_settings: Settings) -> None:
    missing = missing_inputs_for(spec_of("T-1"), dataset_settings)
    if missing:
        pytest.skip("실접속 준비가 안 됐음 — " + " · ".join(missing))
    result = read_member_profile(
        LiveSourceReader(dataset_settings), member_id="M000000", settings=dataset_settings
    )
    assert result.origin is Origin.LIVE
    assert result.row_count <= result.row_cap
