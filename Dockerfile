FROM python:3

WORKDIR /app
COPY pyproject.toml .
COPY poetry.lock .
RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev

COPY . .

CMD [ "python", "bot.py" ]

LABEL org.opencontainers.image.source=https://github.com/the-bwc/discordoperationsbot
LABEL org.opencontainers.image.authors="Patrick Pedersen <github-docker@patrickpedersen.tech> Black Widow Company <S-1@the-bwc.com>"