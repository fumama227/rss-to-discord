import os
import json
from pathlib import Path
import feedparser
import requests

# 設定の読み込み
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
RSS_URL = os.environ.get("RSS_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def ask_gemini(title):
    """GeminiにSNS投稿文を作ってもらう"""
    if not GEMINI_API_KEY:
        return "🚨【注目】最新の株ニュースが届きました✨\n詳細はリンクをチェック！"
    
    # AIへの超シンプルな指示
    prompt = f"「{title}」という株ニュースについて、SNS向けの明るい紹介文を100文字以内で作って。ハッシュタグも2つ付けて。"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        ans = r.json()['candidates'][0]['content']['parts'][0]['text']
        return ans.strip()
    except Exception as e:
        print(f"AIエラー詳細: {e}")
        # 失敗した時の予備の文章（これが出たらキーの設定ミス確定）
        return f"📈【速報】{title}\n注目ニュースが入りました！要チェックです！"

def post_to_discord(title, link, ai_text):
    content = f"📰 **【最新速報】**\n{title}\n\n✍️ **SNS投稿案:**\n{ai_text}\n\n🔗 **詳細:** {link}"
    requests.post(WEBHOOK_URL, json={"content": content}, timeout=30)

def main():
    state_path = Path("state.json")
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    
    last_seen = state.get("last_seen", "")
    feed = feedparser.parse(RSS_URL)
    
    # 逆順にして新しい順に処理
    for e in reversed(feed.entries):
        eid = getattr(e, "id", None) or getattr(e, "link", "")
        if eid == last_seen: break
        
        title = getattr(e, "title", "No title")
        link = getattr(e, "link", "")
        ai_text = ask_gemini(title)
        post_to_discord(title, link, ai_text)
        
        # 1件ずつ最新として保存
        state["last_seen"] = eid
        state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
