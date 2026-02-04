import feedparser
import requests
import time
import os

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
RSS_URL = os.environ["RSS_URL"]

posted = set()

while True:
    feed = feedparser.parse(RSS_URL)
    for entry in feed.entries[:5]:
        link = entry.link
        title = entry.title

        if link not in posted:
            data = {
                "content": f"📰 {title}\n{link}"
            }
            requests.post(WEBHOOK_URL, json=data)
            posted.add(link)

    time.sleep(900)  # 15分ごと
