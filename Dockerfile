FROM python:3.6.11-buster
ARG REDDIT_CLIENT_ID
ARG REDDIT_SECRET
ARG DISCORD_BOT_TOKEN

RUN mkdir /CollectiveCardFetcher/
WORKDIR /CollectiveCardFetcher/

COPY requirements.txt /CollectiveCardFetcher/
RUN python3 -m pip install -r requirements.txt

COPY . /CollectiveCardFetcher/

ENV CID ${REDDIT_CLIENT_ID}
ENV CSECRET ${REDDIT_SECRET}
ENV BOT_TOKEN ${DISCORD_BOT_TOKEN}

ENTRYPOINT [ "python3", "bot.py" ]
