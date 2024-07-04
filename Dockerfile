FROM python:3

WORKDIR /app
COPY requirements.txt ./
COPY /requirements/ ./requirements/
RUN pip install -r requirements.txt

COPY . .

CMD [ "python", "bot.py" ]

LABEL org.opencontainers.image.source=https://github.com/the-bwc/discordoperationsbot
LABEL org.opencontainers.image.authors="Patrick Pedersen <github-docker@patrickpedersen.tech> Black Widow Company <S-1@the-bwc.com>"