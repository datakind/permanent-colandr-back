FROM python:3.7-slim-buster

ENV COLANDR_APP_DIR /app
RUN mkdir -p ${COLANDR_APP_DIR}
WORKDIR ${COLANDR_APP_DIR}

RUN apt update \
    && apt install -y gcc \
    && apt clean \
    && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man

COPY requirements/ ./requirements/
RUN pip install -U pip && pip install -r requirements/prod.txt

COPY . .

EXPOSE 5000

# CMD ["python", "manage.py", "--config", "dev", "runserver", "--port", "5000"]
