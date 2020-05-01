FROM python:3.7

MAINTAINER Caf Annecy "digital@cafannecy.fr"

# Python packages
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

WORKDIR /app

EXPOSE 5000
    
ENTRYPOINT [ "flask" ]

CMD [ "run", "--host=0.0.0.0" ]
