import os
import json
from pathlib import Path
import feedparser
import requests

# 設定（GitHubのSecretsにGOOGLE_CHAT_WEBHOOKを追加してください）
WEBHOOK_OTHER = os.environ.get("DISCORD_WEBHOOK_URL")
WEBHOOK_YUTAI = os.environ.get("WEBHOOK_YUTAI")
WEBHOOK_KESSAN = os.environ.get("WEBHOOK_KESSAN")
GOOGLE_CHAT_WEBHOOK = os.environ.get("GOOGLE_CHAT_WEBHOOK") # ここがGeminiへの入り口
RSS_URLS = [os.environ.get("RSS_URL"), os.environ.get("RSS_URL_2")]

def post_to_services(webhook_url, title, link):
    # 1. Discordへ送信
    discord_webhook = webhook_url if webhook_url else WEBHOOK_OTHER
    content = f"📰 **【新着速報】**\n{title}\n\n🔗 {link}"
    requests.post(discord_webhook, json={"content": content}, timeout=30)
    
    # 2. Google Chat (Gemini)へ送信
    if GOOGLE_CHAT_WEBHOOK:
        # Geminiが読みやすい形式で飛ばす
        gchat_content = f"調査依頼：{title}\nURL：{link}\nふーままとしてお得度を判定して投稿案を作って。"
        requests.post(GOOGLE_CHAT_WEBHOOK, json={"text": gchat_content}, timeout=30)

def main():
    state_path = Path("state.json")
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    last_seen_list = state.get("last_seen_list", [])
    new_seen_list = []
    
    for url in RSS_URLS:
        if not url: continue
        feed = feedparser.parse(url)
        for e in reversed(feed.entries):
            eid = getattr(e, "id", None) or getattr(e, "link", "")
            if eid in last_seen_list: continue
            
            title = getattr(e, "title", "")
            link = getattr(e, "link", "")
            
            target_webhook = WEBHOOK_OTHER
            if any(k in title for k in ["優待", "記念", "QUO", "カタログ"]):
                target_webhook = WEBHOOK_YUTAI
            elif any(k in title for k in ["上方修正", "黒字", "増配", "サプライズ"]):
                target_webhook = WEBHOOK_KESSAN
                
            post_to_services(target_webhook, title, link)
            new_seen_list.append(eid)
    
    updated_seen = (new_seen_list + last_seen_list)[:100]
    state["last_seen_list"] = updated_seen
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
