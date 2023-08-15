FROM python:3.9-slim AS base

ENV COLANDR_APP_DIR /app
RUN mkdir -p ${COLANDR_APP_DIR}
WORKDIR ${COLANDR_APP_DIR}

RUN apt update \
    && apt install -y gcc \
    && apt clean \
    && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man

COPY requirements/ ./requirements/
RUN python -m pip install --upgrade pip wheel && python -m pip install -r requirements/prod.txt
RUN python -m textacy download lang_identifier --version 3.0 \
    && python -m spacy download en_core_web_md \
    && python -m spacy download es_core_news_md \
    && python -m spacy download fr_core_news_md

#####
FROM base AS dev

RUN python -m pip install -r requirements/dev.txt

COPY . .

EXPOSE 5000

CMD ["flask", "--app", "colandr.app:create_app()", "run", "--host", "0.0.0.0", "--port", "5000", "--debug"]

#####
FROM base AS prod

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--config", "./gunicorn.conf.py", "colandr.app:create_app()"]
