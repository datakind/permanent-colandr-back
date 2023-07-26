FROM python:3.8-slim

ENV COLANDR_APP_DIR /app
RUN mkdir -p ${COLANDR_APP_DIR}
WORKDIR ${COLANDR_APP_DIR}

RUN apt update \
    && apt install -y gcc \
    && apt clean \
    && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man

COPY requirements/ ./requirements/
RUN python -m pip install -U pip wheel && python -m pip install -r requirements/prod.txt
RUN python -m textacy download lang_identifier --version 2.0 && python -m spacy download en_core_web_md

COPY . .

EXPOSE 5000

CMD ["flask", "run", "--host", "0.0.0.0", "--port", "5000"]
# CMD ["gunicorn", "--config", "./gunicorn_config.py", "colandr:create_app('dev')"]
