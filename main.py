import os
import json
from pathlib import Path
import feedparser
import requests

# 設定
WEBHOOK_OTHER = os.environ.get("DISCORD_WEBHOOK_URL")
WEBHOOK_YUTAI = os.environ.get("WEBHOOK_YUTAI")
WEBHOOK_KESSAN = os.environ.get("WEBHOOK_KESSAN")
RSS_URLS = [os.environ.get("RSS_URL"), os.environ.get("RSS_URL_2")]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def ask_gemini_with_link(title, link):
    if not GEMINI_API_KEY: return "最新の注目ニュースです✨"
    
    # リンク先の中身も含めてAIに丸投げするプロンプト
    prompt = f"""
    株主優待とポイ活が大好きな投資家「ふーまま」として、以下のニュースについてX（旧Twitter）向けの魅力的な長文紹介文を作成してください。
    
    【最重要：詳細リンクを確認してください】
    リンク先の記事内容を読み込み、何が「お得」で、どんな「メリット」があるのかを具体的に噛み砕いて解説してください。
    URL: {link}

    【投稿の構成】
    1. 【ワクワクする導入】（例：これ知ってる？すごいお得技見つけたよ！💖）
    2. 【記事内容の具体的な要約】（マネックス証券のつなぎ売りなど、具体的な手法や銘柄があれば詳しく）
    3. 【ふーまま流の活用アドバイス】（主婦や初心者目線で「こうするといいよ！」という一言）
    4. 【フォロワーへの問いかけ】（みんなはもう準備した？など）

    【ルール】
    ・X Premium向けなので、文字数は気にせず、読み応えのある内容にする。
    ・「〜だよ」「〜だね」といった明るく親しみやすい口調。
    ・タイトルの丸写しは厳禁。記事の「中身」を自分の言葉で語る。
    ・ハッシュタグを4〜5個つける。
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        # Google Search(Grounding)機能を有効にして、最新のリンク先を見に行かせる
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search_retrieval": {}}] 
        }
        r = requests.post(url, json=payload, timeout=60)
        return r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except:
        return f"📈【注目】{title}\n中身がすごく良い記事だったので、ぜひ詳細リンクからチェックしてみて！✨"

def post_to_discord(webhook_url, title, link, ai_text):
    current_webhook = webhook_url if webhook_url else WEBHOOK_OTHER
    content = f"📰 **【本日の特選ニュース】**\n{title}\n\n✍️ **AI深掘り解説（X Premium対応）:**\n{ai_text}\n\n🔗 **詳細リンク:** {link}"
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
                
            # タイトルだけでなく「リンク」も渡してAIに調べさせる
            ai_text = ask_gemini_with_link(title, link)
            post_to_discord(target_webhook, title, link, ai_text)
            new_seen_list.append(eid)
    
    updated_seen = (new_seen_list + last_seen_list)[:100]
    state["last_seen_list"] = updated_seen
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
