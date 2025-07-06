FROM python:3.11

LABEL org.opencontainers.image.authors="CAF Annecy <digital@cafannecy.fr"

# UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY deployment/docker /app/deployment/docker/
RUN chmod +x /app/deployment/docker/entrypoint.sh

COPY instance /app/instance/
COPY logs /app/logs/

COPY migrations /app/migrations/
COPY config.py pyproject.toml .python-version uv.lock /app/

COPY collectives /app/collectives/
COPY deployment/docker/logging.cfg /app/
COPY metadata.jso[n] /app/

RUN cd /app; uv sync --locked
RUN cd /app; uv tool install waitress

WORKDIR /app

EXPOSE 5000
    
ENTRYPOINT [ "/app/deployment/docker/entrypoint.sh" ]

CMD [ "" ]
