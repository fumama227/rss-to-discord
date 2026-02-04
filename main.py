import os
import feedparser
import requests

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
RSS_URL = os.environ["RSS_URL"]

def post_to_discord(title: str, link: str):
    data = {"content": f"📰 {title}\n{link}"}
    r = requests.post(WEBHOOK_URL, json=data, timeout=30)
    r.raise_for_status()

def main():
    feed = feedparser.parse(RSS_URL)
    # 最新から最大5件だけ送る（多すぎるなら 1 にしてOK）
    for entry in feed.entries[:5]:
        title = getattr(entry, "title", "No title")
        link = getattr(entry, "link", "")
        if link:
            post_to_discord(title, link)

if __name__ == "__main__":
    main()

