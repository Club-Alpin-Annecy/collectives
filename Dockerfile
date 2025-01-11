FROM python:3.11

LABEL org.opencontainers.image.authors="CAF Annecy <digital@cafannecy.fr"

# Python packages

COPY deployment/docker /app/deployment/docker/
RUN chmod +x /app/deployment/docker/entrypoint.sh

COPY instance /app/instance/
COPY logs /app/logs/

COPY migrations /app/migrations/
COPY config.py logging.cfg requirements.txt /app/

RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt
RUN pip install waitress

COPY collectives /app/collectives/
COPY deployment/docker/logging.cfg /app/
COPY metadata.jso[n] /app/

WORKDIR /app

EXPOSE 5000
    
ENTRYPOINT [ "/app/deployment/docker/entrypoint.sh" ]

CMD [ "" ]
