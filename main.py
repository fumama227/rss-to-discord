import os
import json
from pathlib import Path
import feedparser
import requests

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
RSS_URL = os.environ["RSS_URL"]
STATE_FILE = Path("state.json")

def post_to_discord(title: str, link: str):
    data = {"content": f"📰 {title}\n{link}"}
    r = requests.post(WEBHOOK_URL, json=data, timeout=30)
    r.raise_for_status()

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

def entry_id(entry):
    return getattr(entry, "id", None) or getattr(entry, "guid", None) or getattr(entry, "link", "")

def main():
    state = load_state()
    last_seen = state.get("last_seen", "")
    feed = feedparser.parse(RSS_URL)
    entries = list(reversed(feed.entries))

    new_items = []
    for e in entries:
        eid = entry_id(e)
        if not eid: continue
        if last_seen and eid == last_seen:
            new_items = [] 
            continue
        new_items.append(e)

    for e in new_items[-10:]:
        title = getattr(e, "title", "No title")
        link = getattr(e, "link", "")
        if link:
            post_to_discord(title, link)

    if feed.entries:
        state["last_seen"] = entry_id(feed.entries[0])
        save_state(state)

if __name__ == "__main__":
    main()
