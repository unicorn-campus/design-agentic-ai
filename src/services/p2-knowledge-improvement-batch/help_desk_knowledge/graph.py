from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from neo4j import RoutingControl

from .results import Evidence, SearchResult
from .specs import GraphSpec


@dataclass(frozen=True)
class RoleBinding:
    actor_id: str
    workflow_id: str
    role: str


def load_role_bindings(spec: GraphSpec) -> tuple[RoleBinding, ...]:
    data = json.loads(spec.role_map_path.read_text(encoding="utf-8"))
    bindings = tuple(RoleBinding(**item) for item in data["bindings"])
    if len(bindings) != 2 or len({(item.actor_id, item.workflow_id) for item in bindings}) != 2:
        raise ValueError("⑤ 접근 필터 2행과 role 매핑이 1:1이 아님")
    return bindings


class GraphRetriever:
    def __init__(self, driver: Any, spec: GraphSpec) -> None:
        self._driver = driver
        self._spec = spec
        self._bindings = load_role_bindings(spec)

    def startup_verify(self, actor_id: str, workflow_id: str) -> None:
        expected = self._expected_role(actor_id, workflow_id)
        self._driver.verify_connectivity()
        records, _, _ = self._driver.execute_query(
            "SHOW CURRENT USER YIELD roles RETURN roles",
            database_=self._spec.database,
            routing_=RoutingControl.READ,
        )
        roles = set(records[0]["roles"]) if records else set()
        if expected not in roles:
            raise RuntimeError(f"필수 그래프 role로 접속하지 않음: {expected}")

    def search(
        self,
        actor_id: str,
        workflow_id: str,
        state: Mapping[str, object],
    ) -> SearchResult:
        self.startup_verify(actor_id, workflow_id)
        query, parameters = self._query(workflow_id, state)
        records, _, _ = self._driver.execute_query(
            query,
            parameters_=parameters,
            database_=self._spec.database,
            routing_=RoutingControl.READ,
        )
        evidence = tuple(
            Evidence(
                content=str(record["path_evidence"]),
                source=f"neo4j:S-2:{record['path_ref']}",
                score=float(record["score"]),
            )
            for record in records[: self._spec.result_limit]
        )
        if not evidence:
            return SearchResult.empty("후보 수 0건")
        return SearchResult(evidence_refs=evidence)

    def _expected_role(self, actor_id: str, workflow_id: str) -> str:
        matches = [
            item.role
            for item in self._bindings
            if item.actor_id == actor_id and item.workflow_id == workflow_id
        ]
        if len(matches) != 1:
            raise ValueError("담당자와 워크플로우에 대응하는 role이 1개가 아님")
        return matches[0]

    def _query(
        self,
        workflow_id: str,
        state: Mapping[str, object],
    ) -> tuple[str, dict[str, object]]:
        if workflow_id == "W-1":
            if "customer_ref" not in state:
                raise ValueError("③ State customer_ref가 필요함")
            start = "(start:고객 {customer_ref: $scope_value})"
            value = state["customer_ref"]
        elif workflow_id == "W-2":
            if "batch_date" not in state:
                raise ValueError("③ State batch_date가 필요함")
            start = "(start:문의 {business_date: $scope_value})"
            value = state["batch_date"]
        else:
            raise ValueError("지원하지 않는 워크플로우")
        query = (
            f"MATCH p={start}-[*1..{self._spec.max_hops}]-() "
            "RETURN elementId(start) AS path_ref, "
            "toString(nodes(p)) + toString(relationships(p)) AS path_evidence, "
            "1.0 / length(p) AS score "
            "LIMIT $result_limit"
        )
        return query, {"scope_value": value, "result_limit": self._spec.result_limit}
