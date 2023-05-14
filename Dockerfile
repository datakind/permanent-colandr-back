FROM python:3.7-slim-buster

ENV COLANDR_APP_DIR /app
RUN mkdir -p ${COLANDR_APP_DIR}
WORKDIR ${COLANDR_APP_DIR}

RUN apt update && \
    apt install -y gcc \
    && rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install .[dev]

EXPOSE 5000

CMD ["python", "manage.py", "--config", "dev", "runserver", "--port", "5000"]
