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
    
    # 検索機能を強制し、記事の詳細を掴ませる強力な指示
    prompt = f"""
    株主優待とポイ活が大好きな投資家「ふーまま」として、以下のニュースの『中身』を詳しく解説するX（旧Twitter）投稿案を作ってください。

    【対象ニュース】
    タイトル：{title}
    URL：{link}

    【執筆のルール】
    1. Google検索機能を使って、このURL（{link}）の内容や、関連する具体的な「お得ポイント（つなぎ売りのメリットなど）」を必ず調べて含めてください。
    2. タイトルを繰り返すだけの文章は絶対にNGです。記事に何が書いてあるかを自分の言葉で説明してください。
    3. X Premium向けなので、200文字〜400文字程度の読み応えがある内容にします。
    4. 「〜だよ」「〜だね」といった、主婦や投資初心者に寄り添う明るい口調にしてください。
    5. 最後に、読者が「やってみたい！」と思うようなハッシュタグを5個付けてください。
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        # 最新のGoogle Search(Grounding)設定
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}] 
        }
        r = requests.post(url, json=payload, timeout=60)
        data = r.json()
        
        # 応答からテキストを安全に取り出す
        if 'candidates' in data and data['candidates']:
            return data['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            return f"📈【注目】{title}\nとてもお得な内容だったので、リンクから詳細をチェックしてみてね！✨"
    except Exception as e:
        print(f"エラー: {e}")
        return f"📈【速報】{title}\n注目ニュースが入りました！要チェックです！"

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
                
            ai_text = ask_gemini_with_link(title, link)
            post_to_discord(target_webhook, title, link, ai_text)
            new_seen_list.append(eid)
    
    updated_seen = (new_seen_list + last_seen_list)[:100]
    state["last_seen_list"] = updated_seen
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
