# Event Modeling 4단계 Command 완료 예시 장표 스크립트

## 구성

- 대상: Event Modeling 1 ~ 3단계를 마치고 Command를 구체화하는 설계 참여자
- 분량: 표기 원칙 1장 + 흐름 예시 5장, 총 6장
- 사례: 카드 해지를 고민하는 고객 M-204의 상담 흐름
- 표현: PowerPoint 기본 도형·텍스트 상자·연결선만 사용
- 편집성: Trigger·Command·Event와 세부 데이터를 모두 개별 객체로 구성
- 색상·글꼴: 기존 장표의 네이비·블루·흰색과 Pretendard 유지
- 자료: [이탈위험방지 Event Modeling 작성가이드](./이탈위험방지-이벤트모델링-작성가이드.md)
- 주의: 금액·확률·ID·모델 버전은 설계용 가상 예시임

## 1장. 4단계 완료 예시를 읽는 법

- 한 문장: 3단계에서 찾은 사용자·자동화 Trigger를 작업 요청 Command와 결과 Event에 연결함
- 화면·자동화 Trigger: 누가 또는 무엇이 어떤 작업을 시작하는지 표현
- Command: 명령형 제목, 주요 입력, 담당자 유형 표현
- Event: 과거형 제목, 주요 결과, 출처·버전·기준시점 표현
- 기본 연결: Trigger → Command → Event
- 완료 기준: 주요 Event마다 생성 Command 존재, 모든 Command에 시작 Trigger 존재

## 2장. 문의 접수 뒤 실행 경로를 정함

- 사용자 Trigger: 상담사가 U-1 문의 접수 화면에서 상담 시작을 선택하면 문의 접수가 시작됨
- C-1: 문의를 접수하라
- C-1 입력: memberId, question, counselorId
- C-1 담당자 유형: 규칙 기반 코드
- E-1: 문의가 접수되었음
- E-1 결과: consultationId, receivedAt, permissionState
- 자동화 Trigger: ‘문의가 접수되었음’ Event가 발생하면 실행 경로 결정이 시작됨
- C-2: 실행 경로를 결정하라
- C-2 입력: question, permissionState, 상담 제약
- C-2 담당자 유형: 생성형 AI가 질문 해석 지원, 규칙 기반 코드가 경로·필수 여부·대기시간 확정
- E-2: 실행 경로가 정해졌음
- E-2 결과: selectedRoutes, requiredFlags, timeout, selectionReason

## 3장. 정형검색과 유사도 검색을 함께 시작함

- 공통 조건: E-2가 발생하고 해당 경로가 선택됨
- C-3 자동화 Trigger: C-3 경로가 선택되면 고객 현황 확보가 시작됨
- C-3: 고객 현황을 확보하라
- C-3 입력: memberId, asOfDate
- C-3 담당자 유형: 규칙 기반 코드
- E-3: 고객 현황이 확보되었음
- E-3 결과: cardId, productId, amount, predictionFeatures, source, asOfDate
- C-4 자동화 Trigger: C-4 경로가 선택되면 문서 후보 확보가 시작됨
- C-4: 문서 후보를 확보하라
- C-4 입력: question, memberId, accessScope
- C-4 담당자 유형: 규칙 기반 코드
- E-4: 문서 후보가 확보되었음
- E-4 결과: documentId, paragraph, sourceLocation, version
- 실행 관계: C-3과 C-4는 서로의 결과를 기다리지 않고 함께 시작 가능

## 4장. 고객 현황이 준비되면 관계검색과 예측을 시작함

- 공통 조건: E-3가 발생하고 E-2에서 해당 경로가 선택됨
- C-5 자동화 Trigger: cardId와 productId가 준비되면 관계 경로 확보가 시작됨
- C-5: 관계 경로를 확보하라
- C-5 입력: memberId, cardId, productId
- C-5 담당자 유형: 규칙 기반 코드
- E-5: 관계 경로가 확보되었음
- E-5 결과: customer-card-product-document 경로, 각 연결의 원천
- C-6 자동화 Trigger: predictionFeatures가 준비되면 이탈 위험 예측이 시작됨
- C-6: 이탈 위험을 예측하라
- C-6 입력: predictionFeatures, predictionHorizon, modelVersion
- C-6 담당자 유형: 예측형 AI
- E-6: 고객 이탈 위험이 예측되었음
- E-6 결과: probability, riskLevel, signals, horizon, modelVersion, featureAsOf
- 실행 관계: C-5와 C-6은 함께 실행 가능하며 C-4는 이때 검색 중일 수 있음

## 5장. 선택한 결과를 취합해 초안을 작성함

- 취합 Trigger: E-2의 실행 계획에서 필수 E-3·E-4·E-5가 완료되고 보조 E-6이 완료 또는 보류되면
  근거 선정이 시작됨
- C-7: 근거 묶음을 선정하라
- C-7 입력: executionPlan, E-3 ~ E-6 결과·상태
- C-7 담당자 유형: 규칙 기반 코드
- E-7: 근거 묶음이 선정되었음
- E-7 결과: evidenceBundleId R-01, adoptedEvidence, excludedEvidence, cautions
- 초안 Trigger: ‘근거 묶음이 선정되었음’ Event가 발생하면 초안 작성이 시작됨
- C-8: 상담 초안을 작성하라
- C-8 입력: R-01, predictionResult 또는 predictionStatus, customerConstraints
- C-8 담당자 유형: 생성형 AI가 초안 생성, 규칙 기반 코드가 검증·저장
- E-8: 초안이 작성되었음
- E-8 결과: draftId DRAFT-01, draftVersion v1, proposal, evidenceRefs, cautions

## 6장. 초안 반환과 사람의 확인을 구분함

- 반환 Trigger: E-8이 발생하고 화면 요청 Q-301이 도착하면 초안 반환이 시작됨
- C-9: 초안 데이터를 반환하고 반환 이력을 기록하라
- C-9 입력: requestId, consultationId, draftId, draftVersion
- C-9 담당자 유형: 규칙 기반 코드
- E-9: 초안 데이터가 반환되었음
- E-9 결과: requestId, returnedDraftVersion, returnedAt, sourceType
- 사용자 Trigger: 상담사가 U-3 초안 검토 화면에서 확인을 선택하면 초안 확인 기록이 시작됨
- C-10: 초안 확인 이력을 기록하라
- C-10 입력: consultationId, draftId, draftVersion, counselorId
- C-10 담당자 유형: 규칙 기반 코드
- E-10: 초안 확인이 기록되었음
- E-10 결과: counselorId, confirmedDraftVersion, confirmedAt
- 재반환 규칙: 저장된 초안을 다시 반환하면 E-9를 새로 남길 수 있으나 E-8은 반복하지 않음
- 확인 규칙: 데이터 반환 E-9와 상담사의 확인 E-10을 별도 사실로 유지
