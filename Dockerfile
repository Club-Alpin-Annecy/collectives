FROM python:3.7

MAINTAINER Caf Annecy "digital@cafannecy.fr"

# Node packages
# RUN curl -sL https://deb.nodesource.com/setup_12.x | bash
# RUN apt-get install -y nodejs 
# RUN npm install -g less

# Python packages
#RUN pip install pipenv
#COPY Pipfile* /tmp/
#RUN cd /tmp && pipenv lock --requirements > requirements.txt
COPY requirement.txt /tmp/
RUN pip install -r /tmp/requirement.txt

WORKDIR /app

EXPOSE 5000

ENTRYPOINT [ "flask" ]

CMD [ "run", "--host=0.0.0.0" ]
