# 합성 데이터 생성기 — 배포 단위가 아님(⑦ 2절 표에 없음). 로컬 시드 전용.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir asyncpg==0.30.0
COPY common /app/common
COPY synth /app/synth
CMD ["python", "-m", "synth.generate"]
