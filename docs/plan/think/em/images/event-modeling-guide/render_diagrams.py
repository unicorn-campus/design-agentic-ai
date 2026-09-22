"""Render the guide's editable SVG diagrams and matching Korean PNG images.

Run with Python and Pillow. Defaults to Malgun Gothic on Windows; set
EM_FONT_REGULAR and EM_FONT_BOLD to Korean-capable font paths elsewhere.
"""
from pathlib import Path
import html
import math
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
REG = os.environ.get('EM_FONT_REGULAR', 'C:/Windows/Fonts/malgun.ttf')
BOLD = os.environ.get('EM_FONT_BOLD', 'C:/Windows/Fonts/malgunbd.ttf')
W, H, SCALE = 1600, 1080, 2
C = dict(bg='#F5F7FB', ink='#18263D', muted='#5D6C83', line='#B9C6D7',
         white='#FFFFFF', orange='#FFF0D9', orange_s='#D88A24',
         blue='#E5EFFF', blue_s='#3674CE', green='#E0F3E9', green_s='#36865B',
         purple='#F0E8FF', purple_s='#8058B2', gray='#E9EDF3', red='#FCE9E7', red_s='#B9544C')


class Board:
    def __init__(self, num, title, subtitle, width=W, height=H):
        self.width, self.height = width, height
        self.im = Image.new('RGB', (width*SCALE, height*SCALE), C['bg'])
        self.d = ImageDraw.Draw(self.im)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                    f'<rect width="{width}" height="{height}" fill="{C["bg"]}"/>']
        self.rect(48, 38, 74, 60, C['ink'], radius=16)
        self.text(85, 48, num, 28, C['white'], True, 'center')
        self.text(145, 42, title, 38, bold=True)
        self.text(148, 101, subtitle, 23, C['muted'])
        self.line([(48, 155), (width-48, 155)], C['line'], 1)
        self.text(50, height-56, '이탈 위험 방지 · Event Modeling 작성 예시', 19, C['muted'])
        self.text(width-50, height-56, '가상 데이터 · 설계 제안', 19, C['muted'], anchor='right')

    def text(self, x, y, value, size=24, color=None, bold=False, anchor='left'):
        color = color or C['ink']
        font = ImageFont.truetype(BOLD if bold else REG, size*SCALE)
        svg_anchor = dict(left='start', center='middle', right='end')[anchor]
        for n, part in enumerate(str(value).split('\n')):
            yy = y + n * size * 1.5
            width = self.d.textlength(part, font=font)/SCALE
            xx = x - (width/2 if anchor == 'center' else width if anchor == 'right' else 0)
            if xx < 0 or xx+width > self.width or yy+size*1.5 > self.height:
                raise ValueError(f'Text outside canvas: {part}')
            self.d.text((xx*SCALE, yy*SCALE), part, font=font, fill=color)
            self.svg.append(f'<text x="{x}" y="{yy+size*1.16}" text-anchor="{svg_anchor}" '
                            f'font-family="Malgun Gothic, sans-serif" font-size="{size}" '
                            f'font-weight="{700 if bold else 400}" fill="{color}">{html.escape(part)}</text>')

    def rect(self, x, y, w, h, fill, stroke=None, radius=18):
        self.d.rounded_rectangle((x*SCALE,y*SCALE,(x+w)*SCALE,(y+h)*SCALE),
                                 radius=radius*SCALE, fill=fill, outline=stroke, width=2*SCALE)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
                        f'fill="{fill}" stroke="{stroke or fill}" stroke-width="2"/>')

    def line(self, points, color=None, width=3, arrow=False, dashed=False):
        color = color or C['muted']
        for a,b in zip(points, points[1:]):
            if dashed:
                dx,dy=b[0]-a[0],b[1]-a[1]; dist=math.hypot(dx,dy)
                for t in range(0,int(dist),16):
                    z=min(t+9,dist)
                    self.d.line([(int((a[0]+dx*t/dist)*SCALE),int((a[1]+dy*t/dist)*SCALE)),
                                 (int((a[0]+dx*z/dist)*SCALE),int((a[1]+dy*z/dist)*SCALE))],fill=color,width=width*SCALE)
            else:
                self.d.line([(a[0]*SCALE,a[1]*SCALE),(b[0]*SCALE,b[1]*SCALE)],fill=color,width=width*SCALE)
        pts=' '.join(f'{x},{y}' for x,y in points)
        self.svg.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}" '
                        f'stroke-dasharray="{"9 7" if dashed else "none"}" stroke-linejoin="round"/>')
        if arrow:
            a,b=points[-2:]; ang=math.atan2(b[1]-a[1],b[0]-a[0])
            p=[b,(b[0]-15*math.cos(ang-.45),b[1]-15*math.sin(ang-.45)),
               (b[0]-15*math.cos(ang+.45),b[1]-15*math.sin(ang+.45))]
            self.d.polygon([(int(x*SCALE),int(y*SCALE)) for x,y in p],fill=color)
            self.svg.append(f'<polygon points="{" ".join(f"{x},{y}" for x,y in p)}" fill="{color}"/>')

    def tag(self, x, y, label, tone='gray'):
        font=ImageFont.truetype(BOLD,18*SCALE)
        w=self.d.textlength(label,font=font)/SCALE+26
        self.rect(x,y,w,34,C[tone],radius=10)
        self.text(x+13,y+2,label,18,bold=True)
        return w

    def card(self, x,y,w,h,kicker,title,body='',tone='white',size=26):
        self.rect(x,y,w,h,C[tone],C.get(tone+'_s',C['line']))
        self.text(x+22,y+15,kicker,18,C.get(tone+'_s',C['muted']),True)
        self.text(x+22,y+49,title,size,bold=True)
        if body:
            ny=y+56+len(title.split('\n'))*size*1.5
            self.text(x+22,ny,body,21,C['muted'])

    def note(self, title, body):
        self.rect(50,self.height-177,self.width-100,87,C['white'])
        self.text(75,self.height-164,title,22,bold=True)
        self.text(75,self.height-129,body,21,C['muted'])

    def save(self,name):
        (ROOT/f'{name}.svg').write_text('\n'.join(self.svg+['</svg>']),encoding='utf-8')
        self.im.resize((self.width,self.height),Image.Resampling.LANCZOS).save(ROOT/f'{name}.png')


def scope():
    b=Board('00','범위부터 정하기','이번 단계의 결과: 기본 흐름 · 사전 준비 · 확장 가정의 경계')
    b.rect(50,202,1500,374,C['white'],C['blue_s'])
    b.tag(80,222,'이번 모델의 기본 범위','blue')
    data=[('시작','해지 문의 접수','상담사 A-07 / 회원 M-204'),('진행','현황·근거 확보','상담 S-104의 판단 자료'),
          ('진행','제안 초안 작성','DRAFT-01 / v1'),('끝','상담사 확인','명시적 확인 입력까지')]
    for i,(k,t,d) in enumerate(data):
        x=85+i*365;b.card(x,304,330,190,k,t,d,'blue')
        if i<3:b.line([(x+330,398),(x+358,398)],arrow=True)
    b.card(50,615,480,223,'별도 사전 흐름','색인 배치','D1·D2·합성 D3 준비\n상담마다 실행하지 않음','green')
    b.card(560,615,480,223,'기본 범위 이후 · 가정','제안 확정 → 안내 → 반응','실제 고객 안내와 CRM 기록은\n확장 설계로 분리','gray')
    b.card(1070,615,480,223,'현재 미연결','예측형 AI','위험 확률·등급을 만들지 않음\n예측값: 확인 필요','red')
    b.note('먼저 결정할 것','한 상담의 시작과 끝을 정한 뒤, 사전 작업과 없는 기능을 분리함.')
    b.save('00-scope')


def events():
    b=Board('01','기록할 사실 모으기','이번 단계의 결과: 순서나 담당자를 정하기 전의 이벤트 후보 카드')
    b.tag(50,191,'채택 · 나중에 추적할 사실','orange')
    data=[('E-4','초안이\n작성되었음','어떤 초안을 채택했는가'),('E-1','상담이\n시작되었음','어떤 문의가 접수되었는가'),
          ('E-8','초안 데이터가\n반환되었음','누구에게 어떤 버전을\n반환했는가'),('E-3','근거가\n선정되었음','어떤 출처를 채택했는가'),
          ('E-9','초안 확인이\n기록되었음','누가 어떤 버전을 확인했는가'),('E-2','고객 현황이\n확보되었음','당시 어떤 현황을 사용했는가')]
    for i,(k,t,d) in enumerate(data):
        b.card(50+(i%3)*355,246+(i//3)*238,330,208,k,t,d,'orange',25)
    b.card(50,735,1040,128,'별도 사전 작업의 사실','I-1  색인이 발행되었음','사용 가능한 색인 버전을 남김','orange',25)
    b.card(1140,246,410,244,'보류 · 기록 목적 먼저 확인','화면 새로고침','업무 추적에 필요한가?\n모든 기술 동작을 넣지는 않음','gray',27)
    b.card(1140,528,410,276,'제외 · 발생하지 않은 사실','위험도가 산출되었음','예측 모델이 미연결이므로\n산출 이벤트를 만들 수 없음','red',25)
    b.note('반환도 이벤트 후보','초안 내용이 같아도 반환 이력은 새로 남길 수 있음. 저장 위치보다 기록 목적이 기준임.')
    b.save('01-events')


def timeline():
    b=Board('02','이벤트를 시간순으로 놓기','이번 단계의 결과: 사건의 순서 · 선행 조건 · 반복 조회 구간')
    b.card(410,198,340,145,'사전 흐름','I-1  색인 발행','상담과 별도 주기로 실행','green',25)
    b.line([(580,343),(580,395)],arrow=True,dashed=True,color=C['green_s'])
    b.text(765,245,'근거 선정에 사용할 색인이 먼저 준비됨',22,C['green_s'])
    names=[('E-1','상담 시작'),('E-2','현황 확보'),('E-3','근거 선정'),('E-4','초안 작성'),('E-8','초안 반환'),('E-9','확인 기록')]
    for i,(k,t) in enumerate(names):
        x=50+i*253;b.card(x,400,228,156,k,t,f'순서 {i+1}','orange',25)
        if i<5:b.line([(x+229,480),(x+246,480)],arrow=True)
    b.line([(1226,557),(1226,626),(1106,626),(1106,558)],arrow=True,dashed=True,color=C['blue_s'])
    b.text(1035,647,'다시 조회하면 E-8만 추가 가능',23,C['blue_s'],anchor='center')
    b.text(1035,685,'E-4를 새로 만들 필요 없음',21,C['muted'],anchor='center')
    b.rect(50,755,1500,105,C['gray'])
    b.text(78,770,'확장 가정',21,bold=True)
    b.text(320,785,'E-5 제안 확정     →     E-6 실제 안내     →     E-7 반응 기록',26,bold=True)
    b.note('ID는 발생 순서 번호가 아님','E-8·E-9는 추가된 이력 ID임. 상담 흐름에서는 확장 구간 E-5보다 먼저 발생할 수 있음.')
    b.save('02-timeline')


def browser(b,x,title,subtitle):
    b.rect(x,260,470,518,C['white'],C['line'])
    b.rect(x+1,260,468,54,C['gray'],radius=16)
    b.text(x+21,270,title,24,bold=True)
    b.text(x+24,333,subtitle,19,C['muted'])


def storyboard():
    b=Board('03','사람이 보는 장면 그리기','이번 단계의 결과: 입력 필드와 결과 필드가 있는 간단한 화면 시안')
    b.tag(50,191,'상담사 관점 · Human','purple')
    xs=[50,565,1080]
    browser(b,xs[0],'U-1  문의 접수','인증된 상담사 A-07')
    b.text(74,388,'회원 가명 ID',21,bold=True);b.rect(74,428,420,58,C['bg']);b.text(90,438,'M-204',25)
    b.text(74,512,'고객 문의',21,bold=True);b.rect(74,552,420,105,C['bg']);b.text(90,565,'연회비가 부담돼서\n해지하려고요',24)
    b.rect(74,693,420,59,C['blue_s']);b.text(284,704,'상담 시작',25,C['white'],True,'center')
    browser(b,xs[1],'U-2  고객 현황','상담 S-104')
    for yy,label,val in [(390,'기준월','2026-08'),(475,'승인 사용액','420,000원'),(560,'기준일','2026-08-31'),(645,'연체 지표','자료 없음')]:
        b.text(589,yy,label,20,C['muted']);b.text(589,yy+31,val,28,bold=True)
    browser(b,xs[2],'U-3  초안 검토','DRAFT-01 / v1')
    for yy,label,val in [(387,'결론','연회비 조건 확인 후 상담'),(466,'근거·출처','R-01 / D2-DEMO 데모 2절'),(545,'예측값','확인 필요 · 모델 미연결')]:
        b.text(1104,yy,label,20,C['muted']);b.text(1104,yy+32,val,23,bold=True)
    b.text(1104,628,'주의: 실제 혜택 적용 추가 확인',21,C['muted'])
    b.rect(1104,693,420,59,C['purple_s']);b.text(1314,704,'초안 확인',25,C['white'],True,'center')
    b.line([(524,520),(558,520)],arrow=True);b.line([(1039,520),(1073,520)],arrow=True)
    b.text(50,808,'화면 사이에서 실행할 자동화',21,bold=True)
    for x,t in [(445,'A-1 현황 확보'),(805,'A-2 근거 선정'),(1165,'A-3 초안 작성')]:b.tag(x,804,t,'blue')
    for x,t in [(445,'상담 시작 · 현황 없음'),(805,'현황 있음 · 근거 없음'),(1165,'근거 있음 · 초안 없음')]:
        b.text(x,852,t,19,C['muted'])
    b.note('이 단계에서는 화면 필드를 구체화','화면은 설계 가정임. 자동화의 실행 조건을 적고, 실제 처리 요청은 다음 단계에서 연결함.')
    b.save('03-storyboard')


def commands():
    b=Board('04','요청과 처리 결과 연결하기','이번 단계의 결과: 트리거 → 커맨드 → 이벤트로 이어지는 세 가지 변경 슬라이스')
    xs=[240,680,1120]
    for y,label in [(250,'화면/자동화'),(483,'커맨드'),(728,'이벤트')]:b.text(50,y,label,24,bold=True)
    tops=[('U-1 · Human','시작 버튼 선택','문의 접수'),('A-3 · 규칙 기반 코드','초안 작성 조건 충족','현황·근거 있음 / 초안 없음'),('U-3 · Human','확인 버튼 선택','DRAFT-01 / v1')]
    mids=[('C-1 · 규칙 기반 코드','상담을 시작하라','M-204 + 문의 내용'),('C-4 · 생성형 AI + 코드','초안을 작성하라','현황 + R-01 + 미연결 상태'),('C-6 · 규칙 기반 코드','초안 확인을 기록하라','A-07 + DRAFT-01/v1')]
    ends=[('E-1','상담이 시작되었음','S-104 + 문의 + 발생 시각'),('E-4','초안이 작성되었음','초안 내용 + 근거 + 버전'),('E-9','초안 확인이 기록되었음','확인자 + 초안 버전 + 시각')]
    for i,x in enumerate(xs):
        b.line([(x+190,375),(x+190,438)],arrow=True)
        b.line([(x+190,617),(x+190,681)],arrow=True)
        b.card(x,210,380,166,*tops[i],'white',24)
        b.card(x,444,380,174,*mids[i],'blue',24)
        b.card(x,686,380,163,*ends[i],'orange',23)
    b.note('담당자 유형은 필요한 위치에만 표시','규칙 기반 코드 · 생성형 AI · Human을 요청에 배정함. 예측형 AI는 미연결 상태를 유지함.')
    b.save('04-commands')


def readmodels():
    b=Board('05','저장된 사실을 화면 정보로 바꾸기','이번 단계의 결과: 정보의 원천 → 읽기 모델 → 화면, 그리고 별도로 남기는 반환 이력')
    b.card(50,210,365,181,'E-3 · 선정 기록','근거와 출처','R-01\nD2-DEMO / 데모 2절','orange',26)
    b.card(50,421,365,190,'E-4 · 작성 기록','저장된 초안 v1','DRAFT-01 + 내용 + R-01\n예측 미연결 사유','orange',26)
    b.line([(415,296),(480,296),(480,390),(559,390)],arrow=True)
    b.line([(415,509),(480,509),(480,438),(559,438)],arrow=True)
    b.card(565,313,440,224,'V-3 · 읽기 모델','제안 초안 조회','내용과 근거를 연결\n새 초안을 생성하지 않음','green',28)
    b.line([(1005,425),(1114,425)],arrow=True)
    b.card(1120,258,430,350,'U-3 · 화면','상담사가 볼 정보','결론 / 근거 / 출처\n예측값: 확인 필요\n주의사항\nDRAFT-01 / v1','white',26)
    b.text(52,662,'데이터 조회와 반환·확인 기록은 별개의 동작',25,bold=True)
    cards=[('관측','서버 반환 완료','Q-301', 'white'),('C-5','반환 이력 기록','요청자 + 버전','blue'),
           ('E-8','반환되었음','내용은 그대로','orange'),('Human → C-6','명시적 확인','확인 버튼 선택','purple'),
           ('E-9','확인 기록','사용자 + 버전','orange')]
    for i,(k,t,d,tone) in enumerate(cards):
        x=50+i*304;b.card(x,720,280,155,k,t,d,tone,23)
        if i<4:b.line([(x+280,797),(x+298,797)],arrow=True,dashed=i==2)
    b.note('반환되었다고 확인한 것은 아님','점선 이후에는 별도 Human 입력이 필요함. 캐시에서 읽어도 선택한 반환 이력은 기록할 수 있음.')
    b.save('05-read-models')


def swimlanes():
    b=Board('06','업무영역으로 스웜레인 나누기','이번 단계의 결과: 대표 카드를 업무영역별로 배치한 누적 보드')
    # Draw grouping first; lanes are named once within each layer.
    for y,h,title in [(210,195,'화면/자동화'),(439,195,'커맨드/읽기 모델'),(668,212,'이벤트')]:
        b.rect(50,y,1500,h,C['white'],C['line'])
        b.text(70,y+11,title,23,bold=True)
        b.text(70,y+59,'지식 관리',21,C['green_s'],True)
        b.text(70,y+133,'상담 지원',21,C['blue_s'],True)
        b.line([(205,y+103),(1530,y+103)],C['line'],1,dashed=True)
    # Basic causal paths; the read path points upward to the UI.
    b.line([(373,302),(373,489)],arrow=True)
    b.line([(373,532),(373,718)],arrow=True)
    for x in [707,1025]:
        b.line([(x,384),(x,569)],arrow=True)
        b.line([(x,612),(x,798)],arrow=True)
    b.line([(1343,565),(1343,398)],arrow=True,color=C['green_s'])
    b.line([(1025,796),(1186,707),(1343,707),(1343,612)],arrow=True,color=C['green_s'])
    def chip(x,y,w,title,tone,subtitle=''):
        b.rect(x,y,w,65 if subtitle else 54,C[tone],C.get(tone+'_s',C['line']),12)
        b.text(x+w/2,y+3 if subtitle else y+8,title,20 if subtitle else 22,bold=True,anchor='center')
        if subtitle: b.text(x+w/2,y+34,subtitle,15,C['muted'],anchor='center')
    chip(238,250,270,'A-0 색인 배치','white')
    for x,t in [(572,'A-2 근거 선정'),(890,'A-3 초안 작성'),(1208,'U-3 초안 화면')]:
        chip(x,332,270,t,'white','Human' if x==1208 else '')
    chip(238,479,270,'C-0 색인 발행','blue')
    chip(572,561,270,'C-3 근거 선정','blue');chip(890,561,270,'C-4 초안 작성','blue','생성형 AI + 규칙 기반 코드');chip(1208,561,270,'V-3 초안 조회','green')
    chip(238,708,270,'I-1 색인 발행','orange')
    chip(572,790,270,'E-3 근거 선정','orange');chip(890,790,270,'E-4 초안 작성','orange')
    b.text(1220,796,'반환 이력 E-8은\n5단계의 C-5와 연결',18,C['muted'])
    b.note('스웜레인은 업무영역 · 담당자 유형과 다름','상담 지원 안에서 Human·코드·생성형 AI가 함께 일함. 색과 위치로 레이어를 읽고, 업무영역으로 묶음.')
    b.save('06-swimlanes')


def specifications():
    b=Board('07','구체적인 예시로 사양 붙이기','이번 단계의 결과: 커맨드 또는 읽기 모델 한 개에 연결된 검사 기준')
    xs=[50,565,1080]
    specs=[('C-4  초안을 작성하라','초안 작성 성공',[
        ('GIVEN','현황 E-2 + 근거 R-01\n예측 모델 미연결'),('WHEN','S-104의 초안 작성 요청'),('THEN','E-4에 초안·근거 저장\n예측 수치 없음 / 확인 필요')]),
        ('C-5  반환 이력을 기록하라','같은 기록 재시도',[
        ('GIVEN','Q-301 반환 완료\nE-8이 이미 1건 기록됨'),('WHEN','Q-301 이력 기록 재시도'),('THEN','E-8은 여전히 1건\n새 E-4를 만들지 않음')]),
        ('V-4  초안 제공 이력','반환과 확인 구별',[
        ('GIVEN','E-8 반환 기록 존재\nE-9 확인 기록 없음'),('THEN','반환 기록: 있음\n명시적 확인 기록: 없음')])]
    for x,(target,title,parts) in zip(xs,specs):
        b.rect(x,215,470,626,C['white'],C['line'])
        b.tag(x+23,236,target,'blue' if x<1000 else 'green')
        b.text(x+24,294,title,29,bold=True)
        for i,(kind,body) in enumerate(parts):
            yy=368+i*145
            b.text(x+25,yy,kind,20,C['purple_s'],True)
            b.text(x+25,yy+38,body,24)
        if len(parts)==2:
            b.rect(x+24,697,422,99,C['purple'])
            b.text(x+43,715,'읽기 모델은 Given → Then\n형식으로도 정의 가능',22,C['purple_s'])
    b.note('기대 결과까지 구체적으로 적기','성공 여부만 쓰지 않고 이벤트 개수·버전·표시 값을 적음. 여기의 사양은 시험 실행 결과가 아님.')
    b.save('07-specifications')


def completeness():
    b=Board('08','화면에서 원천까지 거슬러 확인하기','이번 단계의 결과: 필드마다 출처가 연결되는지 검토한 결과')
    b.text(70,196,'화면에 표시할 값',24,bold=True)
    b.text(631,196,'구성하는 읽기 모델',24,bold=True)
    b.text(1170,196,'기록 또는 설정 근거',24,bold=True)
    data=[('결론 옆의 근거 R-01','V-3  제안 초안','E-4의 근거 ID\n+ E-3의 출처'),
          ('예측값: 확인 필요','V-3  제안 초안','E-4의 미연결 사유\n예측 수치 없음'),
          ('명시적 확인 기록 없음','V-4  초안 제공 이력','E-8은 있음\nE-9는 없음')]
    for i,(screen,view,source) in enumerate(data):
        y=265+i*199
        b.card(50,y,440,153,'확인할 필드',screen,'','white',25)
        b.card(585,y,420,153,'정보 구성',view,'','green',26)
        b.card(1100,y,450,153,'역추적 도착점',source,'','orange',25)
        b.line([(1007,y+80),(1093,y+80)],arrow=True)
        b.line([(492,y+80),(578,y+80)],arrow=True)
    b.rect(50,869,1500,112,C['ink'])
    b.text(78,884,'검토 결과',23,C['white'],True)
    b.text(290,888,'필드의 원천 연결   /   반환·확인 구분   /   미연결 상태 표시',26,C['white'],True)
    b.text(290,935,'모델의 연결을 확인한 것이며, 실제 서비스 동작을 검증한 것은 아님.',21,'#D8E1EE')
    b.save('08-completeness')


if __name__ == '__main__':
    for render in [scope,events,timeline,storyboard,commands,readmodels,swimlanes,specifications,completeness]:
        render()
        print('rendered:', render.__name__)
