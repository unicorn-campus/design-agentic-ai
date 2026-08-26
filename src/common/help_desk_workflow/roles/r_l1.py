from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

from ..contracts import (
    AnswerDraftOutput,
    EvidenceRefsOutput,
    FaqCandidatesOutput,
    JsonObject,
    ModelInvoker,
    RouteDecisionOutput,
    SqlCandidateOutput,
    SummaryDraftOutput,
    TopicEvidenceOutput,
)

PROMPT_DIR = Path(__file__).parents[1] / "prompts"


class LlmGenerationRole:
    STAGES = frozenset({"S-R2", "S-R3", "S-R5", "S-R8", "S-B3", "S-B5", "S-B8", "S-E3"})
    OUTPUTS: ClassVar = {
        "S-R2": RouteDecisionOutput,
        "S-R3": SqlCandidateOutput,
        "S-R5": EvidenceRefsOutput,
        "S-R8": AnswerDraftOutput,
        "S-B3": SqlCandidateOutput,
        "S-B5": TopicEvidenceOutput,
        "S-B8": FaqCandidatesOutput,
        "S-E3": SummaryDraftOutput,
    }

    def __init__(self, invoke_model: ModelInvoker) -> None:
        self._invoke_model = invoke_model
        self._system_prompt = (PROMPT_DIR / "r_l1_system.md").read_text(
            encoding="utf-8"
        )
        self._user_prompt = (PROMPT_DIR / "r_l1_user.md").read_text(encoding="utf-8")

    async def run(self, stage_id: str, inputs: JsonObject) -> JsonObject:
        if stage_id not in self.STAGES:
            raise ValueError(f"R-L1 미배정 단계: {stage_id}")
        payload = json.dumps(inputs, ensure_ascii=False, sort_keys=True, default=str)
        user_prompt = self._user_prompt.replace("{{stage_id}}", stage_id).replace(
            "{{input_json}}", f"<workflow_input>{payload}</workflow_input>"
        )
        result = await self._invoke_model(stage_id, self._system_prompt, user_prompt)
        return self.OUTPUTS[stage_id].model_validate(result).model_dump()
