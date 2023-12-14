FROM python:3.11

MAINTAINER Caf Annecy "digital@cafannecy.fr"

# Python packages
COPY collectives /app/collectives/
COPY deployment/docker /app/deployment/docker/
COPY instance /app/instance/
COPY logs /app/logs/
COPY migrations /app/migrations/
COPY config.py logging.cfg requirements.txt /app/
COPY deployment/docker/logging.cfg /app/

RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt
RUN pip install waitress
RUN chmod +x /app/deployment/docker/entrypoint.sh

WORKDIR /app

EXPOSE 5000
    
ENTRYPOINT [ "/app/deployment/docker/entrypoint.sh" ]

CMD [ "" ]
