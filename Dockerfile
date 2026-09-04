# Turnout, as one container.
#
# It runs four processes: the web API, and one Agent-to-Agent server for each of the three
# departments. The peers listen on their own ports with their own AgentCards and their own stores,
# so the deployed demo negotiates mutual aid over real HTTP rather than in process. That is the
# claim the project makes, so the live demo should be the thing that proves it.

FROM public.ecr.aws/docker/library/python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src \
    TURNOUT_USE_A2A=1

WORKDIR /app

# Dependencies first, so a code change does not reinstall them.
COPY pyproject.toml README.md ./
COPY src/turnout/__init__.py src/turnout/__init__.py
RUN pip install --no-cache-dir "." && pip install --no-cache-dir "strands-agents[a2a]"

COPY src ./src
COPY web ./web
COPY data ./data
COPY docs ./docs
COPY LICENSE ./

# App Runner health checks this port.
EXPOSE 8080

COPY docker-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

CMD ["/usr/local/bin/entrypoint.sh"]
