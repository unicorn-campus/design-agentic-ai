-- 런치픽 저장소 스키마 — ⑦ 5-2절 저장소 배치 표 S-1 ~ S-8a
-- 저장소 종류는 ⑤가 확정한 것을 인용함: **표 DB만이며 벡터 색인은 없음**(S-7).
--
-- ⑦ 5-3절 점검 결과를 반영함:
--   문제 1 — 위치정보(6개월)를 이력 본문에 섞지 않고 별도 표로 분리
--   문제 2 — S-3에 기간 기반 물리 삭제 작업을 붙이지 않음(조회 시 범위 제한)
--   문제 3 — 접근 로그를 일반 관측 기록과 분리 저장(S-8a)

-- ── 계정: 이미지별로 다른 계정을 발급함(⑦ 4-2절 K-7 ~ K-12) ─────────────────
CREATE ROLE lp_rw  LOGIN PASSWORD 'lp_rw_local';
CREATE ROLE lp_ro  LOGIN PASSWORD 'lp_ro_local';
CREATE ROLE lp_obs LOGIN PASSWORD 'lp_obs_local';

-- ═══════════════════════════════════════════════════════════════════════════
-- DB1 회원·취향 저장소 (S-1)
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE member (
  member_ref        TEXT PRIMARY KEY,        -- F-9 준식별자. 원본 식별자 대체
  email_enc         TEXT NOT NULL,           -- F-3 · K-6 키로 암호화
  nickname_enc      TEXT NOT NULL,           -- F-3 · K-6 키로 암호화
  plan_type         TEXT NOT NULL DEFAULT 'FREE' CHECK (plan_type IN ('FREE','PREMIUM')),
  job_cluster_code  TEXT,                    -- [확인필요: 직군 데이터 수집 경로]
  region_code       TEXT NOT NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 취향 프로파일 — 취향 벡터의 실체는 **카테고리 선호 점수 배열**(J-7 · ES:05#19행)
CREATE TABLE preference_profile (
  member_ref        TEXT PRIMARY KEY REFERENCES member(member_ref) ON DELETE CASCADE,
  category_scores   JSONB NOT NULL DEFAULT '{}'::jsonb,  -- F-10 {"KOR-SOUP":0.8,...}
  feedback_count    INT  NOT NULL DEFAULT 0,             -- 5건 미만이면 콜드스타트
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  prev_scores       JSONB,                               -- ⑥ G-6 갱신 직전 1세대 보관
  prev_updated_at   TIMESTAMPTZ
);

-- 식이제한 — F-1. **A-1만 읽음**. K-5 전용 키로 암호화된 열을 따로 둠
CREATE TABLE dietary_restriction (
  member_ref        TEXT PRIMARY KEY REFERENCES member(member_ref) ON DELETE CASCADE,
  allergen_names    TEXT[] NOT NULL DEFAULT '{}',  -- F-1 (로컬 데모는 평문 배열)
  diet_types        TEXT[] NOT NULL DEFAULT '{}',
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ④ 5-1절 S-R2 동의 상태 확인 대상. 동의는 철회될 수 있으므로 요청 시점에 봄
CREATE TABLE consent (
  member_ref        TEXT PRIMARY KEY REFERENCES member(member_ref) ON DELETE CASCADE,
  location_consent  BOOLEAN NOT NULL DEFAULT FALSE,  -- US:NFR-SYS-040
  sensitive_consent BOOLEAN NOT NULL DEFAULT FALSE,  -- 알레르기 별도 동의
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 위치정보 — ⑦ 5-3 문제 1. 이력 본문에 섞지 않고 **분리된 표**로 두어
-- 6개월 자동 삭제를 이 표에만 걺(US:NFR-SYS-040#체크리스트)
CREATE TABLE location_trace (
  id                BIGSERIAL PRIMARY KEY,
  member_ref        TEXT NOT NULL,
  lat               DOUBLE PRECISION NOT NULL,  -- F-2
  lng               DOUBLE PRECISION NOT NULL,  -- F-2
  captured_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON location_trace (captured_at);

-- K-4 콜드스타트 Prior 표 (⑤ 3절 · [확인필요: 직군 데이터 수집 경로])
CREATE TABLE job_cluster_prior (
  job_cluster_code  TEXT NOT NULL,
  region_code       TEXT NOT NULL,
  category_code     TEXT NOT NULL,
  prior_score       DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (job_cluster_code, region_code, category_code)
);

-- ═══════════════════════════════════════════════════════════════════════════
-- DB2 추천 이력 저장소 (S-2) — ① Q-2 사후 대조용. 근거·태그·원시 컨텍스트
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE recommendation (
  recommendation_id     TEXT PRIMARY KEY,
  member_ref            TEXT NOT NULL,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  filter_applied        BOOLEAN NOT NULL,          -- ⑤ 5절 신설 키
  filter_ruleset_version TEXT NOT NULL,            -- ⑤ 5절 신설 키
  excluded_count        INT NOT NULL DEFAULT 0,
  coldstart             BOOLEAN NOT NULL DEFAULT FALSE,
  generation_status     TEXT NOT NULL,
  fallback_reason       TEXT,
  llm_call_count        INT NOT NULL DEFAULT 0,    -- ⑥ G-3 요청당 모델 호출 수
  -- D-16 원시 컨텍스트 보존 — 출력 태그를 입력값과 대조하려면 원본이 남아야 함
  raw_context           JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX ON recommendation (member_ref, created_at DESC);

CREATE TABLE recommendation_item (
  recommendation_id TEXT NOT NULL REFERENCES recommendation(recommendation_id) ON DELETE CASCADE,
  rank              INT NOT NULL,
  restaurant_id     TEXT NOT NULL,
  reason_text       TEXT NOT NULL,   -- F-5
  confidence        DOUBLE PRECISION NOT NULL,
  context_tags      TEXT[] NOT NULL DEFAULT '{}',  -- F-5
  accepted          BOOLEAN,
  rejected_reason   TEXT,
  responded_at      TIMESTAMPTZ,
  PRIMARY KEY (recommendation_id, rank)
);

-- ═══════════════════════════════════════════════════════════════════════════
-- DB3 식사기록·피드백 저장소 (S-3) — 무료 30일 / 프리미엄 무제한
-- 물리 삭제 작업을 붙이지 않음(⑦ 5-3 문제 2). 조회 시 범위 제한으로 처리함
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE meal_record (
  meal_id           TEXT PRIMARY KEY,
  member_ref        TEXT NOT NULL,
  restaurant_id     TEXT NOT NULL,
  category_code     TEXT NOT NULL,   -- F-4 원문 대신 코드값만
  eaten_at          TIMESTAMPTZ NOT NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (member_ref, restaurant_id, eaten_at)   -- S-E2 중복 기록 검증
);
CREATE INDEX ON meal_record (member_ref, eaten_at DESC);

CREATE TABLE feedback (
  feedback_id       TEXT PRIMARY KEY,
  meal_id           TEXT NOT NULL REFERENCES meal_record(meal_id) ON DELETE CASCADE,
  member_ref        TEXT NOT NULL,
  category_code     TEXT NOT NULL,
  liked             BOOLEAN,          -- F-11 좋아요/별로 이진값. NULL = 스킵(중립)
  keyword_codes     TEXT[] NOT NULL DEFAULT '{}',  -- 맛·양·속도
  reject_reason_code TEXT,
  context_snapshot  JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  reminder_sent_at  TIMESTAMPTZ
);
CREATE INDEX ON feedback (member_ref, created_at DESC);

-- ═══════════════════════════════════════════════════════════════════════════
-- DB4 식당 캐시 저장소 (S-4) — 갱신형. 추천 경로는 여기만 읽음(J-6)
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE restaurant_cache (
  restaurant_id     TEXT PRIMARY KEY,
  display_name      TEXT NOT NULL,          -- ⑥ G-1 외부 유래 문자열
  signature_menu    TEXT NOT NULL,
  category_code     TEXT NOT NULL,
  lat               DOUBLE PRECISION NOT NULL,
  lng               DOUBLE PRECISION NOT NULL,
  walk_minutes      INT NOT NULL,
  rating            DOUBLE PRECISION NOT NULL DEFAULT 0,
  business_status   TEXT NOT NULL,          -- [확인필요: 식당 영업 상태 필드]
  open_from_hour    INT NOT NULL DEFAULT 11,
  open_to_hour      INT NOT NULL DEFAULT 22,
  -- [확인필요: 식당 식재료·알레르겐 정보 원천] — 이 설계서 전체에서 가장 무거운 미확정.
  -- NULL이면 A-1 중단 조건 ②로 그 식당을 후보에서 뺌(페일세이프 B-2)
  allergen_codes    TEXT[],
  region_code       TEXT NOT NULL,
  -- ⑥ G-2 · S-B13 — 출처·수집 시각을 함께 남김
  source            TEXT NOT NULL DEFAULT 'C-2',
  collected_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  expired           BOOLEAN NOT NULL DEFAULT FALSE   -- S-B14 신선도 상한 초과
);
CREATE INDEX ON restaurant_cache (region_code, expired);
CREATE INDEX ON restaurant_cache (collected_at);

-- ═══════════════════════════════════════════════════════════════════════════
-- DB5 구독·결제 저장소 (S-5) — 결제 수단 원문 보관 0건(⑤ F-6)
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE subscription (
  member_ref        TEXT PRIMARY KEY,
  plan_type         TEXT NOT NULL DEFAULT 'FREE' CHECK (plan_type IN ('FREE','PREMIUM')),
  next_billing_date DATE,
  failure_count     INT NOT NULL DEFAULT 0,
  grace_until       DATE,               -- 3회 실패 시 7일 유예(US:UFR-PAY-020)
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════════════════════
-- 로컬 시험용 — C-2 (E)지도·식당 API의 **원시 응답** 대역.
-- 설계상 저장소가 아님(⑦ 5-2절 표에 없음). `LP_PLACES_MODE=mock`일 때
-- SYNC 워커가 여기서 읽어 S-B11 적재 전 검사를 태움.
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE raw_place_feed (
  id          BIGSERIAL PRIMARY KEY,
  region_code TEXT NOT NULL,
  payload     JSONB NOT NULL,
  consumed    BOOLEAN NOT NULL DEFAULT FALSE
);

-- ═══════════════════════════════════════════════════════════════════════════
-- DB6 관측 기록 저장소 (S-6 / S-8) — 변조 방지. 쓰기 전용 계정만 씀
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE obs_span (
  id                BIGSERIAL PRIMARY KEY,
  point             TEXT NOT NULL,      -- O-1 ~ O-11
  span_name         TEXT NOT NULL,
  step              TEXT NOT NULL,      -- S-R1 ~ S-E6
  trace_id          TEXT NOT NULL,
  member_ref        TEXT,               -- 마스킹 후 값(준식별자 가림)
  latency_ms        INT NOT NULL DEFAULT 0,
  is_error          BOOLEAN NOT NULL DEFAULT FALSE,
  reason_code       TEXT,
  attributes        JSONB NOT NULL DEFAULT '{}'::jsonb,  -- M-1 ~ M-3 적용 후
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON obs_span (trace_id);
CREATE INDEX ON obs_span (point, created_at DESC);

-- S-8a 개인정보 접근 로그 — **일반 관측 기록과 분리 저장**(⑦ 5-3 문제 3 해결)
-- 6개월 보관 대상이며 값은 남기지 않고 주체·시각·항목 종류만 남김(⑥ O-9 · M-4)
CREATE TABLE obs_access_log (
  id                    BIGSERIAL PRIMARY KEY,
  actor                 TEXT NOT NULL,   -- A-1 / A-3 / operator
  member_ref            TEXT NOT NULL,   -- 마스킹 후 값
  field_ids             TEXT[] NOT NULL, -- ⑤ F-n 인용. 값 자체는 없음
  allergen_key_decrypt  BOOLEAN NOT NULL DEFAULT FALSE,  -- K-5 복호 호출 여부
  trace_id              TEXT NOT NULL,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON obs_access_log (created_at);

-- ═══════════════════════════════════════════════════════════════════════════
-- 권한 — ⑤ 3절 쓰기 금지 규칙을 계정 권한으로 강제함
-- ═══════════════════════════════════════════════════════════════════════════
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO lp_rw;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO lp_rw;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO lp_ro;
-- 읽기 전용 계정은 관측 기록을 읽지 못함(운영자 계정 전용)
REVOKE SELECT ON obs_span, obs_access_log FROM lp_ro;

-- S-6 `변조 방지` — 업무 계정은 관측 기록을 **고치거나 지울 수 없음**.
-- 개인정보 접근 로그는 6개월 보관 의무 대상이므로(US:NFR-SYS-030) 업무
-- 경로가 지울 수 있으면 보관 의무가 계정 권한으로 무너짐.
REVOKE ALL ON obs_span, obs_access_log FROM lp_rw;

-- 관측 기록은 **쓰기 전용**. 읽기는 운영자 계정으로만(⑦ K-12)
GRANT INSERT ON obs_span, obs_access_log TO lp_obs;
GRANT USAGE, SELECT ON SEQUENCE obs_span_id_seq, obs_access_log_id_seq TO lp_obs;
