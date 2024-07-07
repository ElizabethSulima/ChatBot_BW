FROM python:3.10-alpine

WORKDIR /usr/src/app/

COPY ./pyproject.toml .
COPY ./poetry.lock .
COPY . /usr/src/app/

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi

COPY bot.py /usr/src/app/bot.py

CMD ["python", "bot.py"]
