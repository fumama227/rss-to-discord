import os
import json
from pathlib import Path
import feedparser
import requests

# 設定（3つのチャンネル分）
WEBHOOK_OTHER = os.environ.get("DISCORD_WEBHOOK_URL")
WEBHOOK_YUTAI = os.environ.get("WEBHOOK_YUTAI")
WEBHOOK_KESSAN = os.environ.get("WEBHOOK_KESSAN")
RSS_URL = os.environ.get("RSS_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def ask_gemini(title):
    if not GEMINI_API_KEY: return "最新の株ニュースです✨"
    
    # ふーままさんらしい親しみやすい指示
    prompt = f"「{title}」という株ニュースを、主婦層や初心者に刺さるお得感のあるSNS投稿文にして（100文字以内）。絵文字も使ってね。"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        return r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except:
        return f"📈【速報】{title}\n注目ニュースが入りました！"

def post_to_discord(webhook_url, title, link, ai_text):
    # 登録漏れがあった時のための予備
    current_webhook = webhook_url if webhook_url else WEBHOOK_OTHER
    content = f"📰 **【速報】**\n{title}\n\n✍️ **SNS案:**\n{ai_text}\n\n🔗 {link}"
    requests.post(current_webhook, json={"content": content}, timeout=30)

def main():
    state_path = Path("state.json")
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    last_seen = state.get("last_seen", "")
    feed = feedparser.parse(RSS_URL)
    
    for e in reversed(feed.entries):
        eid = getattr(e, "id", None) or getattr(e, "link", "")
        if eid == last_seen: break
        
        title = getattr(e, "title", "")
        link = getattr(e, "link", "")
        
        # 振り分け：ふーままさんの好きな「お得」と「爆益」で分類
        target_webhook = WEBHOOK_OTHER
        if any(k in title for k in ["優待", "記念", "QUO", "カタログ"]):
            target_webhook = WEBHOOK_YUTAI
        elif any(k in title for k in ["上方修正", "黒字", "増配", "サプライズ"]):
            target_webhook = WEBHOOK_KESSAN
            
        ai_text = ask_gemini(title)
        post_to_discord(target_webhook, title, link, ai_text)
        
        state["last_seen"] = eid
        state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
