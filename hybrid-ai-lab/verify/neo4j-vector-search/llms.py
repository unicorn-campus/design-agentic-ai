"""검증용 LLM 2종: 결과가 늘 같은 가짜 LLM과, 추가 패키지 없이 로컬 Ollama를 HTTP로 부르는 LLM임.

둘 다 neo4j-graphrag의 LLMInterface(V1, 프롬프트 → JSON 글)를 따름 — LLMEntityRelationExtractor 기본 경로와 같음.
"""

from __future__ import annotations

import asyncio
import json
import urllib.request
from typing import Any, Optional, Sequence

from neo4j_graphrag.llm import LLMInterface, LLMResponse


class FakeCardLLM(LLMInterface):
    """프롬프트 속 카드명·'연회비'를 찾아 노드·관계 JSON을 돌려주는 가짜 LLM.

    왜 가짜인가: 저장·병합·세대·그래프 확장은 LLM 품질과 무관하게 같은 입력에 같은 결과가 나와야 시험할 수 있음.
    긴 카드명을 먼저 찾아 '한빛 담백할인'이 '한빛 담백할인 플러스' 안에서 따로 잡히지 않게 함.
    """

    def __init__(self, card_names: Sequence[str]) -> None:
        super().__init__(model_name="fake-card-llm")
        self._names = sorted(set(card_names), key=len, reverse=True)
        self.calls = 0

    def _extract(self, text: str) -> str:
        found: list[str] = []
        rest = text
        for name in self._names:
            if name in rest:
                found.append(name)
                rest = rest.replace(name, " ")
        nodes = [{"id": str(i), "label": "Card", "properties": {"name": n}} for i, n in enumerate(found)]
        relationships = []
        if "연회비" in text and found:
            nodes.append({"id": "fee", "label": "Fee", "properties": {"name": "연회비"}})
            relationships += [{"type": "HAS_FEE", "start_node_id": str(i), "end_node_id": "fee", "properties": {}}
                              for i in range(len(found))]
        relationships += [{"type": "MENTIONED_WITH", "start_node_id": "0", "end_node_id": str(i), "properties": {}}
                          for i in range(1, len(found))]
        return json.dumps({"nodes": nodes, "relationships": relationships}, ensure_ascii=False)

    def invoke(self, input: str, message_history: Optional[Any] = None,
               system_instruction: Optional[str] = None) -> LLMResponse:
        self.calls += 1
        return LLMResponse(content=self._extract(input))

    async def ainvoke(self, input: str, message_history: Optional[Any] = None,
                      system_instruction: Optional[str] = None) -> LLMResponse:
        return self.invoke(input, message_history, system_instruction)


class OllamaHttpLLM(LLMInterface):
    """로컬 Ollama /api/chat을 표준 라이브러리 HTTP로 부르는 LLM(format=json 요청).

    neo4j-graphrag[ollama] 대신 쓰는 이유: 승인받은 패키지(neo4j-graphrag·neo4j·pytest) 밖의 설치를 피하기 위함.
    """

    def __init__(self, model_name: str, host: str = "http://localhost:11434", timeout: float = 300.0) -> None:
        super().__init__(model_name=model_name)
        self._url = host.rstrip("/") + "/api/chat"
        self._timeout = timeout

    def invoke(self, input: str, message_history: Optional[Any] = None,
               system_instruction: Optional[str] = None) -> LLMResponse:
        messages = ([{"role": "system", "content": system_instruction}] if system_instruction else [])
        messages.append({"role": "user", "content": input})
        body = json.dumps({"model": self.model_name, "messages": messages, "stream": False, "format": "json",
                           "options": {"temperature": 0}}).encode("utf-8")
        request = urllib.request.Request(self._url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return LLMResponse(content=payload["message"]["content"])

    async def ainvoke(self, input: str, message_history: Optional[Any] = None,
                      system_instruction: Optional[str] = None) -> LLMResponse:
        return await asyncio.to_thread(self.invoke, input, message_history, system_instruction)
