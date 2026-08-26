from __future__ import annotations

from collections.abc import Mapping

from ..contracts import AsyncOperation, JsonObject


class DeterministicRole:
    STAGES = frozenset(
        {
            "S-R1",
            "S-R4",
            "S-R6",
            "S-R7",
            "S-R10",
            "S-B1",
            "S-B2",
            "S-B4",
            "S-B6",
            "S-B7",
            "S-E1",
            "S-E2",
            "S-E4",
        }
    )

    def __init__(self, operations: Mapping[str, AsyncOperation]) -> None:
        self._operations = operations

    async def run(self, stage_id: str, inputs: JsonObject) -> JsonObject:
        if stage_id not in self.STAGES:
            raise ValueError(f"R-D1 미배정 단계: {stage_id}")
        try:
            operation = self._operations[stage_id]
        except KeyError as error:
            raise RuntimeError(f"선행 인터페이스 조립 누락: {stage_id}") from error
        result = await operation(inputs)
        if not isinstance(result, dict):
            raise TypeError(f"{stage_id} 결정론적 결과가 object가 아님")
        return result
