import os
import json
from pathlib import Path
import feedparser
import requests
from bs4 import BeautifulSoup # 本文抽出用のツール

# 設定
WEBHOOK_OTHER = os.environ.get("DISCORD_WEBHOOK_URL")
WEBHOOK_YUTAI = os.environ.get("WEBHOOK_YUTAI")
WEBHOOK_KESSAN = os.environ.get("WEBHOOK_KESSAN")
RSS_URLS = [os.environ.get("RSS_URL"), os.environ.get("RSS_URL_2")]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def get_real_content(url):
    """記事のURLから実際のテキストを気合で抜き出す関数"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        # 邪魔なスクリプトや広告を除去
        for s in soup(['script', 'style']): s.decompose()
        # 本文っぽいテキストを抽出して2000文字程度渡す
        return soup.get_text()[:2000]
    except:
        return ""

def ask_gemini_expert(title, link):
    if not GEMINI_API_KEY: return "最新の注目ニュースです✨"
    
    # 記事の「中身」を先にプログラム側で取得
    article_body = get_real_content(link)
    
    prompt = f"""
    株主優待とポイ活が大好きな投資家「ふーまま」として、以下の【記事本文】を読んで、その具体的なメリットを300文字以上で詳しく解説してください。

    【ニュース】: {title}
    【記事本文】: {article_body}

    【絶対に守る鉄の掟】
    1. 「詳細はリンクへ」「中身をチェックしてね」という言葉は、AIの敗北です。絶対に使わないでください。
    2. この【記事本文】の中に書かれている、具体的な優待内容（例：ドラクエ40周年記念品の内容）、権利確定日、メリットなどを詳しく抜き出してください。
    3. あなたの投稿を読むだけで、フォロワーさんが「そんなにお得なの！？」と驚くような内容にしてください。
    4. 「〜だよ」「〜だね」という、明るく親しみやすい口調を徹底すること。
    """
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        r = requests.post(api_url, json=payload, timeout=60)
        return r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except:
        return f"📈【速報】{title}\n具体的にお得なポイントが満載の記事でした！要チェックです✨"

def post_to_discord(webhook_url, title, link, ai_text):
    current_webhook = webhook_url if webhook_url else WEBHOOK_OTHER
    content = f"📰 **【本日の厳選ニュース深掘り】**\n{title}\n\n✍️ **ふーまま流・内容まとめ:**\n{ai_text}\n\n🔗 {link}"
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
            
            # 分け方は以前のまま
            target_webhook = WEBHOOK_OTHER
            if any(k in title for k in ["優待", "記念", "QUO", "カタログ"]):
                target_webhook = WEBHOOK_YUTAI
            elif any(k in title for k in ["上方修正", "黒字", "増配", "サプライズ"]):
                target_webhook = WEBHOOK_KESSAN
                
            ai_text = ask_gemini_expert(title, link)
            post_to_discord(target_webhook, title, link, ai_text)
            new_seen_list.append(eid)
    
    updated_seen = (new_seen_list + last_seen_list)[:100]
    state["last_seen_list"] = updated_seen
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
