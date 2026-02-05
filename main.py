import os
import json
from pathlib import Path
import feedparser
import requests
import re

# 設定
WEBHOOK_OTHER = os.environ.get("DISCORD_WEBHOOK_URL")
WEBHOOK_YUTAI = os.environ.get("WEBHOOK_YUTAI")
WEBHOOK_KESSAN = os.environ.get("WEBHOOK_KESSAN")
RSS_URLS = [os.environ.get("RSS_URL"), os.environ.get("RSS_URL_2")]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def get_article_text(url):
    """記事の本文をざっくり取得してAIに渡すための補助関数"""
    try:
        r = requests.get(url, timeout=10)
        # HTMLからタグを除去してテキストだけ抽出
        text = re.sub('<[^<]+?>', '', r.text)
        return text[:2000] # 冒頭2000文字を抽出
    except:
        return ""

def ask_gemini_with_content(title, link):
    if not GEMINI_API_KEY: return "最新の注目ニュースです✨"
    
    # 記事の本文を直接取得
    content = get_article_text(link)
    
    prompt = f"""
    株主優待とポイ活が大好きな投資家「ふーまま」として、以下のニュースの具体的なメリットを解説してください。

    【ニュースタイトル】: {title}
    【記事の本文データ】: {content}

    【絶対に守るべきこと】
    1. 上記の本文データを読み、マネックス証券のつなぎ売りなどの「具体的なメリット」や「手順」を必ず3つ箇条書きで含めてください。
    2. 「詳細はリンクへ」や「中身が濃いので注目」といった中身のない感想は一切禁止です。
    3. この記事を読んでいない人でも、あなたの投稿を読むだけで「何がお得か」が完璧にわかるようにしてください。
    4. X Premium向けに400文字程度で、明るく親しみやすい「ふーまま」の口調（〜だよ、〜だね）で作成してください。
    """
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        # 検索機能も併用して精度を高める
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}]
        }
        r = requests.post(api_url, json=payload, timeout=60)
        res = r.json()
        return res['candidates'][0]['content']['parts'][0]['text'].strip()
    except:
        return f"📈【速報】{title}\nつなぎ売りのメリットが満載の記事でした！要チェックだよ✨"

def post_to_discord(webhook_url, title, link, ai_text):
    current_webhook = webhook_url if webhook_url else WEBHOOK_OTHER
    content = f"📰 **【本日の厳選ニュース深掘り】**\n{title}\n\n✍️ **ふーまま流・お得ポイントまとめ:**\n{ai_text}\n\n🔗 {link}"
    requests.post(current_webhook, json={"content": content}, timeout=30)

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
            
            if any(k in title for k in ["優待", "記念", "QUO", "カタログ"]):
                target_webhook = WEBHOOK_YUTAI
            elif any(k in title for k in ["上方修正", "黒字", "増配", "サプライズ"]):
                target_webhook = WEBHOOK_KESSAN
            else:
                target_webhook = WEBHOOK_OTHER
                
            ai_text = ask_gemini_with_content(title, link)
            post_to_discord(target_webhook, title, link, ai_text)
            new_seen_list.append(eid)
    
    updated_seen = (new_seen_list + last_seen_list)[:100]
    state["last_seen_list"] = updated_seen
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
