# syntax=docker/dockerfile:1
FROM python:3.12-slim@sha256:7a8b475003c4fe15a2cd4e55e5cfc2f3560bdc9333d624f24cdd6d4340fd7a17

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/services/p3-conversation-closed-event/.venv/bin:${PATH}"

RUN groupadd --gid 10001 helpdesk \
    && useradd --uid 10001 --gid helpdesk --no-create-home --shell /usr/sbin/nologin helpdesk \
    && python -m pip install --no-cache-dir uv==0.8.19 \
    && mkdir -p /app /var/lib/help-desk /opt/help-desk-deploy \
    && chown -R helpdesk:helpdesk /var/lib/help-desk

WORKDIR /app
COPY common /app/common
COPY tools /app/tools
COPY services/p3-conversation-closed-event /app/services/p3-conversation-closed-event
COPY deploy/scripts /opt/help-desk-deploy/scripts
COPY deploy/secret_inventory.json /opt/help-desk-deploy/secret_inventory.json

RUN uv sync --frozen --no-dev --project /app/services/p3-conversation-closed-event \
    && chown -R helpdesk:helpdesk /app/services/p3-conversation-closed-event/.venv /opt/help-desk-deploy

USER 10001:10001
WORKDIR /app/services/p3-conversation-closed-event
EXPOSE 8082
ENTRYPOINT ["python", "/opt/help-desk-deploy/scripts/container_entrypoint.py", "p3"]
