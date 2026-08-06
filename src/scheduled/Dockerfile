# ⑦ 2절 — 런타임 이미지. **비밀값을 이미지에 굽지 않음**(⑦ 4-3 위반 1번).
# 키·접속정보는 전부 실행 시 환경변수로 주입되며 빌드 인자로 받지 않음.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements-base.txt /app/requirements-base.txt
COPY scheduled/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 공용 패키지 — lp_common
COPY common/lp_common /app/lp_common
COPY scheduled/app /app/app

# 비루트 실행
RUN useradd -r -u 10001 -m lprun && chown -R lprun /app
USER lprun

# ⑦ 3절 — 포트 없음. HTTP를 받지 않고 스케줄로만 돎.
# 살아 있는지는 종료 코드와 실행 기록으로 판정하므로 HEALTHCHECK도 두지 않음.
ENTRYPOINT ["python", "-m", "app.main"]
CMD ["bat"]
