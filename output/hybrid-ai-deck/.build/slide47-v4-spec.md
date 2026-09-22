# 47페이지 수정 명세

- 제목: build_prompt : 시스템·사용자 프롬프트 구성
- 요약: 원 질문·검색 근거·수정 지침을 답변 LLM의 입력으로 조립
- 처리 도식: query·hits·repair_hints 입력, _run_build_prompt 조립, system_prompt·user_prompt·prompt 반환
- 표: system_prompt는 8개 섹션의 고정 지시문, 공식 기준과 상담 사례의 구분
- 표: user_prompt는 검색결과목록·사용자질문·수정지침 XML, escape 처리와 수정 지침 중복 제거
- 표: prompt는 기존 API·CLI 호환용 user_prompt 동일값
- 진입 전: _finalize_hits에서 답변 관문 판정, 이 노드에서 관문 판정이나 LLM 호출을 수행하지 않음
- 다음 분기: prompt_only=True이면 END, 아니면 generate_answer
- 재진입: verify_evidence의 검증 실패 시 누적 repair_hints를 포함하여 다시 조립
- 근거: graph.py 195~214, 333~340, 437~438, 561~563, 1166~1256행
- 범위: 기존 39페이지 수정 유지. 47페이지 및 해당 발표 노트만 수정. 55장 유지
- 디자인: 기존 네이비 제목과 3단계 도식, 2열 표, 폰트와 푸터 유지
