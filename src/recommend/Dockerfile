# ⑦ 2절 — 런타임 이미지. **비밀값을 이미지에 굽지 않음**(⑦ 4-3 위반 1번).
# 키·접속정보는 전부 실행 시 환경변수로 주입되며 빌드 인자로 받지 않음.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements-base.txt /app/requirements-base.txt
COPY recommend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 공용 패키지 — lp_common
COPY common/lp_common /app/lp_common
COPY recommend/app /app/app

# 비루트 실행
RUN useradd -r -u 10001 -m lprun && chown -R lprun /app
USER lprun

EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=12 \
  CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=2).status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
