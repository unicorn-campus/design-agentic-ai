"""Render the guide's editable SVG figures and matching PNG previews."""
from PIL import ImageFont
from render_diagrams import Board, C, REG, BOLD, SCALE


def box(b, x, y, w, h, label, title, detail='', tone='white', size=24):
    """Draw a card, checking that its text fits inside its own bounds."""
    b.rect(x, y, w, h, C[tone], C.get(tone + '_s', C['line']))
    rows = [(label, 16, True, y + 12, C.get(tone + '_s', C['muted'])),
            (title, size, True, y + 43, C['ink'])]
    if detail:
        rows.append((detail, 19, False, y + 50 + len(title.split('\n')) * size * 1.5, C['muted']))
    for value, fs, bold, yy, color in rows:
        font = ImageFont.truetype(BOLD if bold else REG, fs * SCALE)
        for line in value.split('\n'):
            if b.d.textlength(line, font=font) / SCALE > w - 36:
                raise ValueError(f'Card too narrow: {line}')
        if yy + len(value.split('\n')) * fs * 1.5 > y + h - 6:
            raise ValueError(f'Card too short: {value}')
        b.text(x + 18, yy, value, fs, color, bold)


def scope():
    b = Board('00', '상담 한 건의 범위 정하기',
              '이번 결과: 시작과 끝 · 사전 준비 · 설계용 시나리오')
    items = [('시작 · Human', '해지 문의 접수', 'M-204 / 상담 S-104'),
             ('조회 · 코드/AI', '질문에 필요한 자료 확보', '현황 · 문서 · 관계 · 예측'),
             ('작성 · 생성형 AI + 코드', '상담 초안 구성', '근거 R-01 / DRAFT-01 v1'),
             ('끝 · Human', '상담사 확인', 'A-07의 명시적 확인')]
    for i, (label, title, body) in enumerate(items):
        x = 50 + i * 380
        box(b, x, 235, 350, 190, label, title, body, 'blue', 23)
        if i < 3:
            b.line([(x + 350, 328), (x + 374, 328)], arrow=True)
    box(b, 50, 530, 470, 270, '상담 전에 수행', '지식 준비', '문서 정리·색인 발행\n원천이 연결된 관계 자료 준비', 'green', 27)
    box(b, 565, 530, 470, 270, '이후 단계에서 계속 사용할 사례', '하나의 복합 질문', '연회비 부담 + 장보기 혜택\n추가 소비를 원하지 않는 고객', 'white', 27)
    box(b, 1080, 530, 470, 270, '기본 흐름 이후', '후속 업무', '고객에게 실제 안내\n해지 실행·CRM 기록 등', 'gray', 27)
    b.note('설계 예시로 읽기', '조회 값·문서·관계·예측은 설명용 가정이며, 실제 시스템 실행 결과가 아님.')
    b.save('node-00-scope')


def events():
    b = Board('01', '나중에 확인할 사실 모으기', '이번 결과: 아직 시간순으로 정리하지 않은 이벤트 카드')
    data = [
        ('E-8', '초안이\n작성되었음', 'DRAFT-01 / v1'),
        ('E-1', '문의가\n접수되었음', 'S-104 / 고객 질문'),
        ('E-5', '관계 경로가\n확보되었음', '고객→카드→상품→문서'),
        ('E-6', '고객 이탈 위험이\n예측되었음', '90일 내 82% / 가상값'),
        ('E-10', '초안 확인이\n기록되었음', 'A-07 / 확인 시각'),
        ('E-2', '실행 경로가\n정해졌음', '선택 경로 / 이유'),
        ('E-3', '고객 현황이\n확보되었음', '카드 / 사용액 / 기준월'),
        ('E-4', '문서 후보가\n확보되었음', '안내 문단 / H-17'),
        ('E-7', '근거 묶음이\n선정되었음', 'R-01 / 채택·제외 사유'),
        ('E-9', '초안 데이터가\n반환되었음', '요청 ID / 초안 버전'),
    ]
    for i, (label, title, detail) in enumerate(data):
        box(b, 50 + (i % 5) * 304, 220 + (i // 5) * 285,
            280, 237, label, title, detail, 'orange', 23)
    b.text(65, 810, '작성 · 반환 · 사람의 확인은 각각 다른 사실', 28, bold=True)
    b.note('같은 초안을 다시 조회하면', '반환 이력은 추가할 수 있지만, 초안을 다시 작성한 것은 아니므로 E-8은 반복하지 않음.')
    b.save('node-01-events')


def timeline():
    b = Board('02', '사건을 시간순으로 놓기', '이번 결과: 준비된 자료에서 상담사의 확인까지 이어지는 한 번의 이야기')
    box(b, 50, 195, 600, 132, '별도 준비 흐름 · I-1', '문서 색인과 관계 자료가 준비되었음',
        '상담 전 준비 / 자료 버전 보존', 'green', 24)
    b.text(720, 225, '아래는 한 상담의 가능한 기록 순서입니다.\nE-4가 E-3보다 먼저 기록되는 경우도 가능합니다.',
           22, C['muted'])
    top = [('E-1', '문의 접수'), ('E-2', '경로 결정'), ('E-3', '현황 확보'),
           ('E-4', '문서 후보 확보'), ('E-5', '관계 경로 확보')]
    bottom = [('E-6', '이탈 위험 예측'), ('E-7', '근거 묶음 선정'), ('E-8', '초안 작성'),
              ('E-9', '초안 반환'), ('E-10', '상담사 확인')]
    for y, data in [(385, top), (700, bottom)]:
        for i, (label, title) in enumerate(data):
            x = 50 + i * 304
            box(b, x, y, 280, 143, label, title, '', 'orange', 23)
            if i < 4:
                b.line([(x + 280, y + 75), (x + 299, y + 75)], arrow=True)
    b.line([(1538, 458), (1569, 458), (1569, 610), (29, 610), (29, 775), (47, 775)],
           arrow=True, dashed=True)
    b.text(800, 633, '확보한 자료와 특징으로 판단한 뒤 상담사에게 제공', 22, C['muted'], anchor='center')
    b.note('기록 순서와 실행 의존관계 구분', '이벤트 번호는 실행 순번이 아님. 병렬 시작·조건부 선택·취합 조건은 자동화와 사양에 명시.')
    b.save('node-02-timeline')


def storyboard():
    b = Board('03', '상담사가 볼 화면 그리기', '이번 결과: 입력·현황·초안 검토 화면의 필드와 시작 행동')
    xs = [50, 565, 1080]
    for x, label, title in zip(xs, ['U-1 · 입력', 'U-2 · 현황', 'U-3 · 검토'],
                              ['문의 접수', '고객 현황', '제안 초안']):
        b.rect(x, 230, 470, 570, C['white'], C['line'])
        b.rect(x, 230, 470, 65, C['gray'])
        b.text(x + 22, 241, label, 20, C['muted'], True)
        b.text(x + 22, 319, title, 29, bold=True)
    b.text(72, 400, '가명 회원 ID', 20, C['muted'])
    b.text(72, 435, 'M-204', 27, bold=True)
    b.text(72, 515, '고객 질문과 상담 요청', 20, C['muted'])
    b.text(72, 552, '연회비 부담 · 장보기 혜택\n추가 소비 없는 상담 초안', 23)
    b.rect(72, 707, 425, 58, C['blue_s'])
    b.text(284, 717, '상담 시작', 23, C['white'], True, 'center')
    b.text(587, 400, '보유 카드 / 상품', 20, C['muted'])
    b.text(587, 435, 'CARD-204 / P-01', 26, bold=True)
    b.text(587, 515, '전월 승인 사용액', 20, C['muted'])
    b.text(587, 552, '420,000원', 27, bold=True)
    b.text(587, 638, '기준월 · 집계 정의 · 출처', 22, C['muted'])
    b.text(1102, 400, '초안 · 근거 · 주의사항', 20, C['muted'])
    b.text(1102, 435, '추가 소비 없이 조건 확인', 23, bold=True)
    b.text(1102, 515, '향후 90일 내 고객 이탈', 20, C['muted'])
    b.text(1102, 552, '예측 확률 82% · 높음', 24, bold=True)
    b.text(1102, 638, 'R-01 / DRAFT-01 v1', 22, C['muted'])
    b.rect(1102, 707, 425, 58, C['purple_s'])
    b.text(1314, 717, '초안 확인', 23, C['white'], True, 'center')
    b.line([(520, 520), (559, 520)], arrow=True)
    b.line([(1035, 520), (1074, 520)], arrow=True)
    b.text(65, 829, '자동화: 문의 접수 → 경로 결정·자료 확보 → 근거 준비 후 초안 작성', 23, bold=True)
    b.note('3단계는 화면 구상', '5단계에서 같은 U-3에 표시할 값과 출처를 읽기 모델로 연결함. 확률은 설계용 가상값.')
    b.save('node-03-storyboard')


def routing():
    b = Board('03', '질문에 따라 경로 선택하기', '이번 결과: 질문의 각 확인 항목을 담당 경로에 배정한 실행 계획')
    box(b, 50, 200, 1500, 135, 'U-1 · Human', '연회비 부담과 장보기 혜택을 확인하고 추가 소비 없는 초안을 요청',
        '회원 M-204 / 상담 S-104', 'white', 25)
    box(b, 450, 397, 700, 143, 'A-1 → C-2 · 생성형 AI + 규칙 기반 코드', '질문 해석 → 실행할 경로와 선택 이유 확정',
        '필수·보조 구분 / 필요한 입력·대기 시간도 저장', 'blue', 24)
    b.line([(800, 335), (800, 392)], arrow=True)
    data = [('수치·상태 필요 → 선택', '정형검색 · C-3', '이번 질문: 필수'),
            ('조건·발언 필요 → 선택', '벡터검색 · C-4', '이번 질문: 필수'),
            ('문서 연결 확인 필요 → 선택', '그래프검색 · C-5', '이번 질문: 필수'),
            ('이탈 판단 필요 → 선택', '예측형 AI · C-6', '이번 질문: 보조')]
    for i, (label, title, detail) in enumerate(data):
        x = 50 + i * 380
        b.line([(800, 540), (800, 578), (x + 175, 578), (x + 175, 626)], arrow=True)
        box(b, x, 632, 350, 184, label, title, detail, 'green' if i < 3 else 'purple', 25)
    b.note('다른 질문이면 다른 계획', '사용액만 물으면 C-3만 선택. 선택하지 않은 경로는 실행하지도, 취합할 때 기다리지도 않음.')
    b.save('node-03-routing')


def contracts():
    b = Board('04', '요청에서 결과까지 연결하기', '이번 결과: 시작 조건 → 커맨드 → 결과 이벤트의 네 슬라이스')
    xs = [235, 565, 895, 1225]
    for y, label in [(235, '화면/자동화'), (469, '커맨드'), (742, '이벤트')]:
        b.text(50, y, label, 22, bold=True)
    columns = [
        ('현황 경로 선택', '회원·조회 시점', 'C-3 · 규칙 기반 코드', '고객 현황을\n확보하라',
         '고객 정보계 조회', 'E-3', '고객 현황 확보', 'CARD-204 / 420,000원'),
        ('문서 경로 선택', '질의·회원·접근 조건', 'C-4 · 규칙 기반 코드', '문서 후보를\n확보하라',
         '벡터 저장소 검색', 'E-4', '문서 후보 확보', 'GUIDE-DEMO / H-17'),
        ('선택 + C-3 ID 준비', '회원·카드·상품 ID', 'C-5 · 규칙 기반 코드', '관계 경로를\n확보하라',
         '관계 저장소 탐색', 'E-5', '관계 경로 확보', '상품→안내 문서 + 원천'),
        ('선택 + 특징 준비', 'C-3 이용·보유·상담 집계', 'C-6 · 예측형 AI', '고객 이탈 위험을\n예측하라',
         'CHURN-DEMO/v1 추론', 'E-6', '고객 이탈 위험 예측', '90일 내 82% / 높음'),
    ]
    for x, d in zip(xs, columns):
        box(b, x, 215, 300, 150, '자동화 시작 조건', d[0], d[1], 'white', 21)
        b.line([(x + 150, 366), (x + 150, 425)], arrow=True)
        box(b, x, 430, 300, 210, d[2], d[3], d[4], 'blue', 23)
        b.line([(x + 150, 641), (x + 150, 688)], arrow=True)
        box(b, x, 695, 300, 152, d[5], d[6], d[7], 'orange', 21)
    b.note('입출력과 담당자 유형', '검색 결과는 원천·기준시점을 보존하고, 예측 결과는 모델 버전과 특징 시점을 보존.')
    b.save('node-04-contracts')


def execution():
    b = Board('04', '병렬 실행과 조건부 분기',
              '보조 실행 흐름도 · 화살표는 입력 의존관계 · 이번 복합 질문의 계획')
    box(b, 50, 190, 1500, 125, '화면/자동화 · 문의 접수 / 담당자 유형: 규칙 기반 코드',
        'E-2 실행 계획 확인 → 선택한 경로만 시작',
        'C-3·C-4·C-5 필수 / C-6 보조 / 권한 확인 완료', 'blue', 26)
    # Two independent starts; C-5 and C-6 depend only on C-3 inputs.
    b.line([(460, 315), (460, 357)], arrow=True)
    b.line([(1280, 315), (1280, 357)], arrow=True)
    box(b, 50, 365, 800, 135, '고객 정보 · 규칙 기반 코드', 'C-3 고객 현황·예측 특징 확보',
        '카드·상품 ID / 이용 추이·보유 기간·상담 정확 집계', 'green', 25)
    box(b, 1060, 365, 490, 135, '지식·관계 · 규칙 기반 코드', 'C-4 문서 후보 검색',
        '질문·회원·접근 조건으로 시작', 'green', 25)
    b.line([(450, 500), (450, 530), (245, 530), (245, 554)], arrow=True)
    b.line([(450, 530), (670, 530), (670, 554)], arrow=True)
    box(b, 50, 560, 390, 158, '지식·관계 · 규칙 기반 코드', 'C-5 관계 검색',
        'C-3의 카드·상품 ID 필요\nC-4 완료를 기다리지 않음', 'blue', 25)
    box(b, 465, 560, 390, 158, '상담 판단 · 예측형 AI', 'C-6 이탈 예측',
        'C-3의 정확한 특징 필요\nC-5 완료를 기다리지 않음', 'purple', 25)
    box(b, 1060, 560, 490, 158, '대안 흐름 · 규칙 기반 코드', '실패했을 때의 선택',
        '필수 경로 실패 → 초안 보류\n예측 실패·5초 초과 → 예측 보류', 'gray', 25)
    # Explicit C-3 result contribution, alongside C-4/C-5/C-6 outcomes.
    b.line([(850, 432), (955, 432), (955, 750), (810, 750)], arrow=False)
    b.line([(1305, 500), (1580, 500), (1580, 750), (810, 750)], arrow=False)
    b.line([(245, 718), (245, 750), (810, 750)], arrow=False)
    b.line([(660, 718), (660, 750), (810, 750), (810, 760)], arrow=True)
    box(b, 50, 765, 1500, 128, '상담 판단 · 규칙 기반 코드 / C-7 시작 조건',
        '필수 C-3·C-4·C-5 완료 + 보조 C-6 완료 또는 보류 → 근거 선정 요청',
        '선택하지 않은 경로는 대기 대상에서 제외 / 필수 근거가 없으면 선정 단계에서도 보류', 'orange', 25)
    b.note('조건은 자동화와 사양에 연결', '타임라인의 대체물이 아님. 정상·예측 보류·필수 자료 실패는 각각 별도 시나리오로 확인.')
    b.save('node-04-execution')


def merge():
    b = Board('05', '결과를 취합하고 화면에 연결하기', '정상 시나리오 · 선택한 필수 경로 완료 + 보조 예측 완료 또는 보류 후 C-7 시작')
    data = [('E-3 · 고객 사실', '전월 사용액 420,000원', '기준월 · 집계 정의'),
            ('E-4 · 문서·발언', '안내 문단 / H-17', '조건 확인 · 추가 소비 거절'),
            ('E-5 · 적용 문서 연결', 'P-01 → GUIDE-DEMO', '연결마다 원천 보존'),
            ('E-6 · 고객 이탈 예측', '90일 내 이탈 확률 82%', 'CHURN-DEMO/v1 · 가상값')]
    for i, (label, title, detail) in enumerate(data):
        x = 50 + i * 380
        box(b, x, 200, 350, 165, label, title, detail, 'green' if i < 3 else 'purple', 22)
        b.line([(x + 175, 365), (x + 175, 412)], arrow=True)
    box(b, 50, 420, 1500, 150, 'C-7 · 규칙 기반 코드 → E-7', '동일 고객·상품·시점·권한 확인 → R-01 근거 묶음 선정',
        '원천 충돌·누락을 보존 / 이탈 예측은 별도 판단 자료 / 추가 소비 거절을 제약으로 전달', 'orange', 25)
    b.line([(285, 570), (285, 634)], arrow=True)
    bottom = [('C-8 → E-8 · 생성형 AI + 코드', '근거로 초안 작성·저장', 'DRAFT-01/v1\n문장별 출처 검사'),
              ('V-3 · 읽기 모델', '화면용 결과 구성', '초안 + R-01 + 현황\n이탈 예측 + 확인 상태'),
              ('U-3 · Human', '상담사 초안 검토', '추가 소비 없이 조건 확인\n이탈 위험 높음 / 확인 버튼')]
    for i, (label, title, detail) in enumerate(bottom):
        x = 50 + i * 510
        box(b, x, 640, 480, 220, label, title, detail, ['blue', 'green', 'white'][i], 25)
        if i < 2:
            b.line([(x + 480, 748), (x + 505, 748)], arrow=True)
    b.note('결과가 준비되지 않은 경우', '예측 보류는 값 없이 상태를 전달. 필수 근거 누락·충돌은 선정 보류 → U-3에 사유 표시, 초안 없음.')
    b.save('node-05-merge')


def boundaries():
    b = Board('06', '업무영역을 따라 전체 흐름 정리하기',
              '행 = 스웜레인(업무영역) / 열 = 업무 진행 단계 / 카드 색 = 레이어 / 카드 위 = 담당자 유형',
              width=2920, height=1740)
    legends = [('화면/자동화', 'white'), ('커맨드/읽기 모델', 'blue'),
               ('이벤트', 'orange'), ('사양', 'purple')]
    for i, (label, tone) in enumerate(legends):
        x = 300 + i * 410
        b.rect(x, 180, 30, 30, C[tone], C.get(tone + '_s', C['line']), 6)
        b.text(x + 42, 180, label, 22, bold=True)
    b.text(2860, 182, '업무 진행 →', 22, C['muted'], True, 'right')
    columns = ['문의 접수', '라우팅', '현황·문서 확보', '관계·예측',
               '결과 취합', '초안 작성', '결과 반환', '상담사 확인']
    b.text(65, 240, '스웜레인 ↓', 24, bold=True)
    for j, title in enumerate(columns):
        x = 300 + j * 320
        b.rect(x, 235, 304, 47, C['ink'], radius=8)
        b.text(x + 152, 243, title, 24, C['white'], True, 'center')
    lanes = ['문의·결과 제공', '고객 정보', '지식·관계', '상담 판단']
    for i, lane in enumerate(lanes):
        y = 300 + i * 300
        b.rect(50, y, 2820, 290, C['white'], C['line'], 10)
        b.rect(50, y, 225, 290, C['gray'], C['line'], 10)
        b.text(162, y + 117, lane, 24, bold=True, anchor='center')
        for j in range(1, 8):
            x = 292 + j * 320
            b.line([(x, y + 8), (x, y + 280)], C['line'], 1, dashed=True)
    # Only actual slices are shown; empty intersections contain no invented cards.
    slices = [
        (0, 0, 'Human → 규칙 기반 코드',
         ['U-1 문의 입력·시작', 'C-1 문의 접수', 'E-1 문의가 접수되었음', '회원·상담사 권한 확인']),
        (3, 1, '생성형 AI + 규칙 기반 코드',
         ['E-1 접수 후 자동화', 'C-2 실행 경로 결정', 'E-2 실행 경로가 정해졌음', '선택 이유·필수 여부 저장']),
        (1, 2, '규칙 기반 코드',
         ['현황 경로 선택·권한 확인', 'C-3 현황·예측 특징 확보', 'E-3 고객 현황이 확보되었음', '정확 집계·기준시점 보존']),
        (2, 2, '규칙 기반 코드',
         ['문서 경로 선택·질의 준비', 'C-4 문서 후보 확보', 'E-4 문서 후보가 확보되었음', '원문 위치·버전·권한 보존']),
        (2, 3, '규칙 기반 코드',
         ['관계 선택 + C-3 ID 준비', 'C-5 관계 경로 확보', 'E-5 관계 경로가 확보되었음', '연결별 원천·상품 일치 확인']),
        (3, 3, '예측형 AI + 규칙 기반 코드',
         ['예측 선택 + C-3 특징 준비', 'C-6 이탈 위험 예측', 'E-6 이탈 위험이 예측되었음', '예측 기간·모델 버전 보존']),
        (3, 4, '규칙 기반 코드',
         ['선택 경로 취합 조건 충족', 'C-7 결과 취합·근거 선정', 'E-7 근거 묶음이 선정되었음', '필수 근거 검사·R-01 저장']),
        (3, 5, '생성형 AI + 규칙 기반 코드',
         ['E-7 근거 선정 후 자동화', 'C-8 초안 작성·검사·저장', 'E-8 초안이 작성되었음', '문장별 출처·고객 제약 검사']),
        (0, 6, '규칙 기반 코드 → Human',
         ['U-3에 초안 데이터 반환', 'V-3 화면용 데이터 구성\nC-9 반환 이력 기록',
          'E-9 초안 데이터가\n반환되었음', '반환 요청별 중복 기록 방지']),
        (0, 7, 'Human → 규칙 기반 코드',
         ['U-3 확인 버튼 클릭', 'C-10 상담사 확인 기록', 'E-10 초안 확인이\n기록되었음', '반환과 Human 확인 구분']),
    ]
    for lane, col, performer, cards in slices:
        x, y = 300 + col * 320, 300 + lane * 300
        b.text(x + 12, y + 8, performer, 18, C['muted'], True)
        for j, (value, (_, tone)) in enumerate(zip(cards, legends)):
            yy = y + 42 + j * 58
            b.rect(x + 6, yy, 292, 54, C[tone], C.get(tone + '_s', C['line']), 8)
            font = ImageFont.truetype(REG, 18 * SCALE)
            assert all(b.d.textlength(line, font=font) / SCALE <= 270 for line in value.split('\n')), value
            b.text(x + 17, yy + (2 if '\n' in value else 12), value, 18)
    b.text(65, 1512, '같은 열의 작업은 병렬 실행 가능 · 다음 열도 필요한 입력이 준비되면 시작 · 정확한 시작·취합 조건은 4~5단계 참조',
           22, C['muted'])
    b.note('정상 시나리오의 C-1~C-10과 E-1~E-10을 모두 배치',
           '라우팅은 경로 결정 E-2로, 결과 취합은 근거 묶음 선정 E-7로 기록. 예측 보류·필수 자료 실패는 7단계의 대안 시나리오로 연결.')
    b.save('node-06-boundaries')


def specs():
    b = Board('07', '구체적인 예시로 사양 정하기', '이번 결과: 커맨드 또는 읽기 모델에 연결한 정상·예외 기준')
    data = [
        ('C-2 · 질문 해석·경로 선택', '사용액만 물으면 C-3만 선택',
         'Given  지난달 사용액 질문\nWhen   경로 결정 요청\nThen   C-3 선택 / 나머지는 선택하지 않음'),
        ('C-7 · 근거 선정', '완료 순서가 달라도 같은 근거',
         'Given  같은 결과 · E-3/E-4 기록 순서만 다름\nWhen   취합 조건 충족 후 근거 선정 요청\nThen   같은 R-01 / 계획별 중복 선정 없음'),
        ('C-6 · 보조 이탈 예측', '시간 초과이면 예측 보류',
         'Given  예측 요청 후 5초 초과\nWhen   예측 대기 종료\nThen   보류 기록 / 확률·등급 없이 진행'),
        ('V-3 · 읽기 모델', '필수 자료 실패이면 초안 보류',
         'Given  C-5 실패 / 필수 자료 확보 중단\nThen   연결 확인 필요 표시\n         초안 없음 / E-7·E-8 없음'),
    ]
    for i, (label, title, detail) in enumerate(data):
        box(b, 50 + (i % 2) * 765, 215 + (i // 2) * 335, 735, 285,
            label, title, detail, 'blue' if i < 2 else 'purple', 27)
    b.note('사양과 실행 결과는 다름', '예시의 기대 동작을 정한 것임. 실제 구현 후 같은 조건으로 결과를 확인해야 함.')
    b.save('node-07-specs')


if __name__ == '__main__':
    for render in [scope, events, timeline, storyboard, routing, contracts, execution, merge, boundaries, specs]:
        render()
        print('rendered:', render.__name__)
