// node build.js — GraphRAG 용어 19개 세 장 빌드 (script.md 슬라이드 1 ~ 3)
const path = require("path");
const L = require("./lib");
const { C, X0, CW } = L;

// 용어 한 행: [용어, 영문, 설명, 예시] — 예시는 설명 아래 줄에 다른 색으로 붙임
const SLIDES = [
  {
    title: "GraphRAG 용어 ① 그래프 기본 구조",
    lead: "그래프는 노드(점)와 관계(선)로 이뤄지고, 관계를 따라 이동하며 답을 찾음",
    notes: "노드·관계·속성이 그래프의 세 재료이고, 순회·홉·경로는 그 위를 움직이는 말임.",
    rowH: "auto", size: 14,
    rows: [
      ["노드", "Node", "그래프에 저장된 점 하나. 사람·상품 같은 대상이나 문서 조각 하나하나가 노드가 됨",
        "'홍길동' 고객, '여행 카드' 상품, '조각 12'"],
      ["엔티티", "Entity",
        ["문장이나 데이터에 나오는 실제 대상. 그래프에 넣으면 노드가 됨",
          "노드가 모두 엔티티는 아님: 조각·문서·커뮤니티 노드는 대상이 아니므로 엔티티가 아님"],
        "'홍길동'·'여행 카드'는 엔티티 노드, '조각 12'는 엔티티가 아닌 노드"],
      ["레이블", "Label",
        ["노드의 종류를 나타내는 이름표. 한 노드에 0개 이상 붙일 수 있음",
          "다른 문서의 '노드 유형'·'엔티티 유형'과 같은 뜻"],
        "홍길동 노드에 :고객 레이블, (:고객:VIP)처럼 두 개도 가능"],
      ["관계", "Relationship (type)",
        ["두 노드를 잇는 연결과 그 연결의 이름(보유·제공 등)을 함께 이르는 말",
          "항상 시작 노드·끝 노드·방향과 이름 하나를 가짐. 다른 문서의 '관계 유형'도 여기에 포함"],
        "(홍길동)-[:보유]->(여행 카드)의 보유"],
      ["속성", "Property", "노드나 관계에 붙는 '이름: 값' 정보",
        "여행 카드 노드 {연회비: 20000, 출시일: 2024-05-01}, 보유 관계 {발급일: 2025-03-01}"],
      ["방향", "Direction", "관계가 시작 노드에서 끝 노드로 향하는 쪽. 저장은 한 방향이어도 조회는 거꾸로 가능",
        "카드에서 '보유'를 거꾸로 따라 고객 찾기"],
      ["경로", "Path", "노드와 관계가 번갈아 이어진 한 줄의 자취",
        "홍길동 → 여행 카드 → 공항 라운지 혜택"],
      ["그래프 순회 (노드 탐색)", "Traversal", "출발 노드에서 관계를 따라 이웃 노드로 옮겨 가며 원하는 노드를 찾는 일",
        "고객 → 보유 카드 → 그 카드의 혜택"],
      ["홉", "Hop (k-hop)", "관계 하나를 건너는 단위. k홉은 관계를 k번 건넌 거리, 여러 홉 탐색은 멀티홉",
        "고객→카드 1홉, 고객→카드→혜택 2홉"],
    ],
  },
  {
    title: "GraphRAG 용어 ② 인덱싱(그래프 만들기)",
    lead: "문서와 데이터를 노드·관계로 바꿔, 중복 없이 쌓는 단계에서 쓰는 용어",
    notes: "스키마로 틀을 정하고 → 추출로 채우고 → 해소·MERGE로 중복을 막고 → 조각으로 원문과 이음.",
    rowH: 1.1, size: 15,
    rows: [
      ["그래프 스키마", "Graph schema",
        ["둘 수 있는 레이블·관계와 어떤 노드끼리 이을지를 미리 정한 설계도",
          "LLM 추출이 범위 밖 레이블·관계를 만들지 않게 막음",
          "※ Neo4j 문서의 '스키마'는 인덱스·제약을 뜻하기도 함"],
        "(고객)-[:보유]->(카드)만 허용"],
      ["엔티티·관계 추출", "Entity & relation extraction",
        ["문장에서 대상(엔티티)과 그 사이의 관계를 뽑아 노드·레이블·관계·속성으로 바꾸는 일",
          "레이블은 보통 스키마에 정해 둔 목록에서 고름. LLM이나 규칙으로 처리함"],
        "'A카드는 음식점 결제 시 4% 할인' → 노드 A카드(상품)·할인(혜택, 할인율 4%)·음식점(업종), 관계 제공·대상"],
      ["엔티티 해소", "Entity resolution",
        ["이름이 달라도 같은 대상을 가리키는 노드를 찾아 하나로 합치는 일",
          "하지 않으면 같은 대상이 여러 노드로 흩어져 관계가 끊김"],
        "'삼성전자'와 '삼성전자㈜'를 한 노드로 합침"],
      ["고유 제약과 MERGE", "Uniqueness constraint · MERGE",
        ["고유 제약: 정해진 속성 값이 겹치지 않게 DB가 막는 규칙",
          "MERGE: 있으면 그대로 쓰고 없으면 만드는 명령. 함께 쓰면 다시 적재해도 중복이 안 생김"],
        "MERGE (c:고객 {고객ID: 'C001'})"],
      ["조각", "Chunk (TextUnit)",
        ["긴 문서를 검색하기 좋은 크기로 자른 한 토막. MS GraphRAG는 TextUnit이라 부름",
          "조각을 노드로 두고 그 안에 나온 대상과 이어 두면 원문 근거로 되돌아갈 수 있음"],
        "(조각 12)-[:언급]->(여행 카드)"],
    ],
  },
  {
    title: "GraphRAG 용어 ③ 검색(그래프에서 꺼내기)",
    lead: "출발 노드를 찾고, 질의로 관계를 따라가, 근거와 함께 꺼내는 단계에서 쓰는 용어",
    notes: "출발 노드(인덱스로 찾음) → 사이퍼로 순회(템플릿 또는 Text2Cypher) → 출처와 함께 답에 넘김.",
    rowH: 1.1, size: 15,
    rows: [
      ["출발 노드", "Access point (진입점)",
        ["그래프 순회를 시작하는 노드",
          "질문 속 이름과 일치하는 노드, 벡터 검색으로 찾은 노드, 다른 시스템의 조회 결과 등으로 정함"],
        "질문의 '여행 카드'로 상품 노드를 찾아 출발"],
      ["인덱스", "Index",
        ["속성 값으로 노드를 빨리 찾게 돕는 보조 장치",
          "값 일치용 일반 인덱스, 낱말 검색용 전문 인덱스, 뜻 검색용 벡터 인덱스가 있음"],
        "상품 이름 인덱스로 '여행 카드'를 전체를 훑지 않고 바로 찾음"],
      ["사이퍼", "Cypher",
        ["그래프 질의 언어. 노드는 ( ), 관계는 -[ ]-> 처럼 그림 모양으로 씀",
          "Neo4j 등에서 사용"],
        "MATCH (c:고객)-[:보유]->(k:카드) RETURN k.이름"],
      ["사이퍼 템플릿과 Text2Cypher", "Cypher template · Text2Cypher",
        ["질문을 질의문으로 바꾸는 두 방법. 템플릿은 미리 쓴 질의문에 값만 끼워 안전하고 예측 가능함",
          "Text2Cypher는 LLM이 질의문을 직접 써서 유연하지만 실행 전 검증이 필요함"],
        "MATCH (u:업종 {이름: $업종}) … 의 $업종에 '식비'를 끼움"],
      ["출처 되짚기", "Provenance",
        ["답에 쓴 정보가 어느 노드·관계·원문 조각에서 왔는지 기록하고 보여 주는 것",
          "답을 검증하고 잘못된 근거를 찾을 수 있게 함"],
        "'음식점 4% 할인 (근거: 조각 12 → 할인 혜택 노드)'"],
    ],
  },
];

// 설명 칸: 본문(문장 배열이면 문장마다 줄을 나눔) + 다음 줄에 "예:" 줄
function descCell(desc, ex) {
  const lines = Array.isArray(desc) ? desc : [desc];
  return { text: [
    ...lines.map((t) => ({ text: t, options: { color: C.body, breakLine: true } })),
    { text: "예: ", options: { color: C.blue, bold: true } },
    { text: ex, options: { color: C.slate } },
  ], options: { valign: "middle" } };
}

function createSlide(spec) {
  const s = L.newSlide({ title: spec.title, lead: spec.lead, notes: spec.notes });
  const head = ["용어", "영문", "설명"];
  const body = spec.rows.map(([term, en, desc, ex]) => [
    { text: term, options: { color: C.navy, bold: true } },
    { text: en, options: { color: C.slate, bold: false } },
    descCell(desc, ex),
  ]);
  // "auto"면 설명 줄 수(설명 + 예 줄)에 맞춰 행 높이를 정함 — 9행이 본문 아래 끝(7.95″)을 넘지 않게 함
  const lineH = (n) => (n <= 2 ? 0.56 : 0.76);
  const heights = spec.rows.map(([, , desc]) => (spec.rowH === "auto"
    ? lineH((Array.isArray(desc) ? desc.length : 1) + 1) : spec.rowH));
  L.table(s, [head, ...body], { x: X0, y: 1.9, w: CW, colW: [2.5, 2.6, CW - 5.1], rowH: [0.42, ...heights],
    size: spec.size });
  return s;
}

async function main() {
  L.createDeck();
  SLIDES.forEach(createSlide);
  const out = process.argv[2] || path.join(__dirname, "GraphRAG용어.pptx");
  await L.getPptx().writeFile({ fileName: out });
  console.log("✅ PPT 생성 완료:", out);
}

main().catch((e) => { console.error("❌ PPT 생성 실패:", e); process.exit(1); });
