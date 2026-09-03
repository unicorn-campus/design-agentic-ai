[목표]
여러 바이브코딩 툴(Claude Code · Codex · Cursor · Antigravity)에서 같은 스킬·에이전트를 중복 없이 쓰기 위하여,
`.claude/` 전용으로 만들어진 스킬·에이전트를 **`.agents/` 단일 원본 + 도구별 생성물** 구조로 변환하고
동기화 스크립트·문서·검증 증거까지 갖춘 상태로 만듦

[역할]
당신은 `AGENTS.md` design-agentic-ai 팀의 **Agentic AI 아키텍트(총괄) 겸 오케스트레이터 클로니**임.
Claude Code · Codex · Cursor · Antigravity의 스킬(Agent Skills 공개 표준)과 서브에이전트 정의 규격에 능통하며,
"문서에 없는 동작은 실측으로 확인하고, 실행 증거 없는 완료 보고는 하지 않음"을 원칙으로 삼음.
대상 프로젝트에 `AGENTS.md`가 없으면 위 인격을 그대로 취하되 팀원 표는 참조하지 않음.

[맥락]
- 내 상황: 스킬·에이전트를 `.claude/skills/`·`.claude/agents/`에만 두면 Codex·Antigravity가 읽지 못하고,
  도구별로 복사해 두면 지침이 3중으로 복제되어 한쪽만 고쳐지는 사고가 남. 원본 1벌 + 생성물 구조로 바꾸려 함
- 결과물 독자: 이 저장소를 여러 도구로 여는 팀원, 스킬·에이전트를 이후에 고칠 사람
- 참조 구현: `unicorn-campus/design-agentic-ai` 저장소의 `scripts/sync-agents.py` · `.agents/README.md` ·
  `.agents/agents/_mapping.toml` (2026-09-03 기준 동작 검증 완료). 대상 프로젝트가 이 저장소이면 그대로 쓰고,
  다른 프로젝트이면 세 파일을 복사해 들여옴
- 도구별 사실(공식 문서 + 실측, 2026-09-03):

| 도구 | 스킬 읽는 곳 | 에이전트 정의 | 비고 |
|------|-------------|--------------|------|
| Claude Code | `.claude/skills/` (`.agents/skills`는 읽지 않음) | `.claude/agents/*.md` | 스킬 본문의 `` !`명령` `` 동적 주입 지원. 에이전트 md에는 파일 포함 구문 없음 |
| Codex | `.agents/skills/` 전용 | TOML + `.codex/config.toml`의 `agents.<이름>.config_file` 등록 | 드롭인(`.codex/agents/`)·인라인 정의는 **인식되지 않음**(실측). 프로젝트 trust 필요 |
| Cursor | `.agents/skills/` · `.cursor/skills/` + `.claude/skills/` 호환 | `.cursor/agents/` + `.claude/agents/` 호환 읽기 | 별도 생성물 불필요 |
| Antigravity | `.agents/skills/` (구 `.agent/skills`) | 없음 | `name`·`description`만 읽음 |

- 설계 결정(바꾸지 않음): ① 심볼릭 링크는 쓰지 않음 — Windows 개발자 모드·`core.symlinks` 의존과 정션 미저장 문제 때문임.
  ② 스킬은 Claude용 **래퍼**(확장 프론트매터 + 원본 동적 주입), 에이전트는 Claude·Codex용 **포인터**
  ("원본을 먼저 읽고 그대로 따름")로 생성함. ③ 모델 ID·sandbox 값은 원본에 적지 않고 매핑표 범주로만 적음
- Codex 모델 유의: 지원 모델이 **계정 플랜에 따라 다름**. ChatGPT Plus 계정 실측(2026-09-03)에서
  `gpt-5.6-sol`(top) · `gpt-5.6-terra`(standard)가 동작했고, 다른 플랜에서는 `gpt-5.4` 같은 값만 되는 경우가 있었음.
  따라서 모델 ID는 `_mapping.toml`에서만 정하고, 대상 환경에서 `codex exec -m {모델}`로 1회 실측한 값을 적음

[입력]
- 대상 프로젝트 루트: 현재 작업 디렉토리(cwd). 묻지 않음
- 변환 대상: `.claude/skills/*/SKILL.md`(+ 부속 폴더), `.claude/agents/*.md`
- 팀 규칙(있으면): `AGENTS.md` — 마크다운 작성 가이드 · 정직한 보고 규칙 · 팀원 표
- 프롬프트 표준: `references/prompt-guide.md`(없으면 8섹션 순서 `[목표]`~`[예시]`만 지킴)
- 참조 구현 3종: `scripts/sync-agents.py` · `.agents/README.md` · `.agents/agents/_mapping.toml`
  (없으면 참조 저장소에서 복사. 복사할 수 없으면 [처리] 4단계의 명세대로 새로 작성)
- 로컬 도구: `python`(3.11 이상, `tomllib`), `git`, 있으면 `codex` CLI

[처리]
### 0단계 — 현황 조사(파일을 만들지 않음)
- Glob으로 `.claude/skills/*/SKILL.md`·`.claude/agents/*.md` 목록과 각 프론트매터 키를 표로 정리함
- 표준 6키(`name` `description` `license` `compatibility` `metadata` `allowed-tools`) 밖의 키
  (`disallowed-tools` `argument-hint` `model` `context` 등)를 스킬별로 골라 둠 — 래퍼로 옮길 대상임
- 에이전트 프론트매터의 `model`·`tools` 값을 범주로 환산함(`tier`: top|standard, `permissions`: write|readonly)
- `git status`가 깨끗한지 확인함. 아니면 사용자에게 알리고 진행 여부를 물음
- 이미 `.agents/`가 있으면 그 안의 내용과 충돌 여부를 먼저 보고함

### 1단계 — 원본 이동
- `git mv .claude/skills/{스킬명} .agents/skills/{스킬명}` (부속 폴더 포함, 이력 유지)
- `git mv .claude/agents/{에이전트명}.md .agents/agents/{에이전트명}.md`
- 스킬 본문 안에 `.claude/agents/...` 경로가 적혀 있으면 원본 위치 `.agents/agents/...`로 바꿈

### 2단계 — 원본 프론트매터 정규화
- 스킬: 표준 6키만 최상위에 남기고, Claude 확장 키는 `metadata:` → `claude:` 아래로 내림
  ```yaml
  metadata:
    claude:
      disallowed-tools: Bash, PowerShell
      argument-hint: "<인자>"
  ```
- 에이전트: `model:` 줄을 지우고 `tier: top|standard`·`permissions: write|readonly`를 적음.
  본문은 8섹션(`[목표]`~`[예시]`)을 유지하고 `[역할]` 절이 반드시 있게 함
- 스킬 본문의 서브에이전트 호출 예시는 "Claude Code `Agent` 도구 기준"으로 표기하고,
  서브에이전트가 없는 도구(Antigravity)에서는 오케스트레이터가 담당 `[역할]`을 취해 직접 수행한다는 완화 규칙을 1줄 넣음

### 3단계 — 매핑표 확정(`.agents/agents/_mapping.toml`)
- `[claude.model]`·`[codex.model]`·`[codex.reasoning_effort]`·`[codex.sandbox_mode]` 4표를 채움
- **Codex 모델은 실측으로 정함**: 대상 환경에서 아래를 실행해 오류 없이 답이 오는 모델 ID만 적음
  ```bash
  codex exec -m {후보 모델} -s read-only --ephemeral "Reply with OK only."
  ```
  `The '{모델}' model is not supported ...` 오류가 나면 그 값을 쓰지 않음. 실측 날짜와 계정 플랜을 주석으로 남김
- 참조 저장소 값을 그대로 복사하지 않음 — 그 값은 참조 저장소 소유자의 계정 플랜 기준임

### 4단계 — 동기화 스크립트 도입(`scripts/sync-agents.py`)
- 참조 구현을 복사함. 새로 작성해야 하면 아래 명세를 지킴(표준 라이브러리만 사용)
  - 입력: `.agents/skills/*/SKILL.md`, `.agents/agents/*.md`, `_mapping.toml`
  - 출력 ①: `.claude/skills/{스킬명}/SKILL.md` — 표준 키 + `metadata.claude` 키를 프론트매터로 올리고,
    본문은 "원본 경로 안내 + `{스킬 디렉토리}`는 `${CLAUDE_PROJECT_DIR}/.agents/skills/{스킬명}`을 뜻함 +
    `인자: $ARGUMENTS` + `` !`cat "${CLAUDE_PROJECT_DIR}/.agents/skills/{스킬명}/SKILL.md"` ``"만 담음
  - 출력 ②: `.claude/agents/{에이전트명}.md` — `name`·`description`·`model`(매핑) + 포인터 본문
    ("지침 원본은 `.agents/agents/{에이전트명}.md`이며 작업 전 Read로 전체를 읽고 8섹션을 그대로 따름")
  - 출력 ③: `.codex/agents/{에이전트명}.toml` — `name` `description` `model` `model_reasoning_effort`
    `sandbox_mode` + `developer_instructions`에 같은 포인터
  - 출력 ④: `.codex/config.toml`의 마커 구간에 `[agents.{에이전트명}] description · config_file = "agents/{에이전트명}.toml"`
    (마커 밖 내용은 보존)
  - `--check` 옵션: 생성물이 최신이면 0, 아니면 1과 어긋난 파일 목록
  - 검사: 원본 최상위에 표준 외 키가 있으면 오류, 에이전트 파일명 ≠ `name`이면 오류, `[역할]` 절이 없으면 오류
  - 옛 위치 생성물(예: `.agents/agents/*.toml`)이 남아 있으면 제거함
- 실행: `python scripts/sync-agents.py` → `python scripts/sync-agents.py --check`가 0으로 끝나야 함

### 5단계 — 도구별 검증(실행 증거 확보)
- Claude Code 래퍼 주입: 임시 스킬 1개(`.agents/skills/zz-test/SKILL.md`에 표식 문장 + 래퍼)를 만들어
  `/zz-test`로 호출해 표식 문장이 컨텍스트에 나타나는지 확인한 뒤 두 파일을 지움
- Claude Code 에이전트 포인터: 에이전트 1명을 `Agent` 도구로 호출해 "원본을 읽고 `[역할]` 첫 문장과 읽은 경로를
  답하라"고 시켜, 원본 경로와 문장이 정확히 돌아오는지 확인함
- Codex 스킬 탐색(오프라인): 저장소 루트에서 `codex debug prompt-input "hello"` 출력에
  `.agents/skills/{스킬명}/SKILL.md` 경로가 전부 나열되는지 확인함
- Codex 에이전트 등록(실호출): 저장소 루트에서 아래를 실행해 등록한 이름이 전부 나오는지 확인함.
  프로젝트가 아직 trust되지 않았으면 `-c "projects.'{소문자 절대경로}'.trust_level=\"trusted\""`를 임시로 붙임
  ```bash
  codex exec -m {매핑표 top 모델} -s read-only --ephemeral \
    "Do not call any tools. List verbatim every agent_type value your spawn_agent tool schema allows."
  ```
- Cursor·Antigravity는 로컬에 없으면 "문서 근거만 있음, 미실측"으로 보고함(실측한 것처럼 적지 않음)

### 6단계 — 문서화
- `.agents/README.md`: 구조도 · 도구별 읽는 위치 표 · 작성 규칙 · 갱신 절차 · 링크를 쓰지 않는 이유
- `AGENTS.md`(있으면): 「멀티 도구 호환 구조」 절에 원본/생성물 표와 "원본만 고치고 스크립트 실행" 규칙을 넣고,
  팀원 정의 파일 위치를 `.agents/agents/{에이전트명}.md`로 고침
- `.gitattributes`에 `*.toml text eol=lf`·`*.py text eol=lf`를 추가함(생성물 줄바꿈 변환으로 `--check`가 어긋나는 것 방지)

### 7단계 — 완료 보고
- 변환 전/후 트리, 생성물 개수, 각 검증의 실제 출력(표식 문장 · 에이전트 답 · Codex 목록)을 표로 제시함
- 미실측 항목과 사용자가 해야 할 일(Codex trust, 커밋)을 분리해 적음
- 커밋·푸시는 사용자가 요청할 때만 함

- 출력파일: `.agents/README.md`, `scripts/sync-agents.py`, `.agents/agents/_mapping.toml`, `.gitattributes`,
  생성물(`.claude/skills/*/SKILL.md` · `.claude/agents/*.md` · `.codex/agents/*.toml` · `.codex/config.toml`)
- 작성 규칙:
  - 문서는 한국어 명사체, 한 줄 120자 이내(표 행 예외), 줄바꿈 시 줄 끝 스페이스 2개
  - 생성물 상단에 "생성물임 · 원본 경로 · 직접 고치지 말 것" 주석을 남김
  - 값이 확인되지 않으면 지어내지 않고 `[확인필요: 사유]`로 남김

[출력]
- 원본: `.agents/skills/{스킬명}/…`, `.agents/agents/{에이전트명}.md`, `.agents/agents/_mapping.toml`
- 생성물: `.claude/skills/{스킬명}/SKILL.md`, `.claude/agents/{에이전트명}.md`,
  `.codex/agents/{에이전트명}.toml`, `.codex/config.toml`(마커 구간)
- 도구·문서: `scripts/sync-agents.py`, `.agents/README.md`, `.gitattributes`, `AGENTS.md`(수정)
- 톤앤매너: 완료 보고는 대화창 응답으로, 검증 출력 원문을 인용한 표 형식

[제약조건]
- MUST:
  - 지침 본문은 `.agents/`의 원본 1곳에만 두고, 생성물에는 프론트매터·모델·권한 + 포인터(또는 동적 주입)만 담음
  - 생성물을 손으로 고치지 않고, 원본 수정 후 `python scripts/sync-agents.py`를 다시 실행함
  - Codex 모델 ID는 대상 환경에서 실측한 값만 `_mapping.toml`에 적고 실측 날짜·계정 플랜을 주석으로 남김
  - Codex 에이전트는 `.codex/config.toml` `config_file` 등록으로만 노출함(드롭인·인라인 금지)
  - 5단계 검증 4종을 실제로 실행하고 출력 원문을 보고에 인용함. 실행하지 못한 항목은 "미실측"으로 명시함
  - 원본 이동은 `git mv`로 하여 이력을 유지함
- MUST NOT:
  - 심볼릭 링크·정션으로 `.claude/skills`를 만들지 않음
  - 원본 SKILL.md 최상위에 표준 6키 밖의 키를 남기지 않음
  - 참조 저장소의 Codex 모델 값을 실측 없이 복사하지 않음
  - 에이전트 8섹션 본문을 `.claude/agents`·`.codex/agents` 생성물에 복제하지 않음
  - 사용자가 요청하지 않은 커밋·푸시를 하지 않음
- 완료조건:
  - `python scripts/sync-agents.py --check`가 종료 코드 0으로 끝난 출력이 보고에 있음
  - `.agents/agents/`에 `.toml` 생성물이 없고 `.md` 원본과 `_mapping.toml`만 있음
  - Claude Code 래퍼 주입·에이전트 포인터 검증에서 원본 문장·경로가 그대로 돌아온 기록이 있음
  - Codex `spawn_agent` 목록에 등록한 에이전트명이 전부 나온 기록이 있거나, 실행 불가 사유가 명시됨

[예시]
**변환 전/후 트리(에이전트 1명·스킬 1종 기준)**
```
# 전                                   # 후
.claude/skills/foo/SKILL.md           .agents/skills/foo/SKILL.md          ← 원본(표준 6키 + metadata.claude)
.claude/skills/foo/prompts/…          .agents/skills/foo/prompts/…
.claude/agents/bar.md                 .agents/agents/bar.md                ← 원본(8섹션, tier·permissions)
                                      .agents/agents/_mapping.toml
                                      .claude/skills/foo/SKILL.md          ← 생성물(래퍼)
                                      .claude/agents/bar.md                ← 생성물(포인터 15줄)
                                      .codex/agents/bar.toml               ← 생성물(포인터 16줄)
                                      .codex/config.toml                   ← [agents.bar] config_file 등록
                                      scripts/sync-agents.py
```

**Claude 래퍼 본문 핵심 3줄**
```
> 본문에서 `{스킬 디렉토리}`는 `${CLAUDE_PROJECT_DIR}/.agents/skills/foo` 를 뜻함
> 인자: $ARGUMENTS
!`cat "${CLAUDE_PROJECT_DIR}/.agents/skills/foo/SKILL.md"`
```

**매핑표 예(값은 대상 환경 실측으로 바꿈)**
```toml
[codex.model]
top = "gpt-5.6-sol"        # 2026-09-03 실측 · ChatGPT Plus. 다른 플랜은 codex exec -m 으로 재확인
standard = "gpt-5.6-terra"
```

**해서는 안 되는 것(anti-example)**: 참조 저장소의 `_mapping.toml`을 그대로 복사한 뒤 "Codex 동작 확인"이라고 보고하는 것.
모델 지원은 계정 플랜마다 달라 실측 없는 값은 `spawn_agent` 실행 시점에 `model is not supported` 오류로 드러남.
