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

def ask_gemini_strict(title, link):
    if not GEMINI_API_KEY: return "最新の注目ニュースです✨"
    
    # AIへの指示を「中身を見ること」に全振り
    prompt = f"""
    あなたは投資家「ふーまま」の専属ライターです。
    今から渡すURLに「実際にアクセスして」、そこに書かれている具体的なメリットを抽出してください。

    【対象】
    ニュース：{title}
    URL：{link}

    【絶対に守るルール】
    1. リンク先の内容（手順、メリット、利回り、銘柄名など）を確認し、具体的な情報を3つ以上含めてください。
    2. タイトルを繰り返すだけ、あるいは「中身が濃いのでチェックして」と逃げるのは厳禁です。
    3. 記事の中身を知らない人でも、この投稿を読むだけで「何がお得か」が完璧に分かるように解説してください。
    4. X Premium向けに、200〜400文字程度の読み応えがある内容にします。
    5. 「〜だよ」「〜だね」という、お得大好きで親しみやすい口調で書いてください。
    """
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        # Grounding設定（しきい値を0にして、必ずネットを見に行かせる設定）
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search_retrieval": {
                "dynamic_retrieval_config": {
                    "mode": "MODE_DYNAMIC",
                    "dynamic_threshold": 0.0
                }
            }}]
        }
        r = requests.post(api_url, json=payload, timeout=60)
        res = r.json()
        
        if 'candidates' in res and res['candidates']:
            return res['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            return f"📈【注目】{title}\nこの記事は中身がすごく良いので、ぜひリンク先をチェックしてみてね！✨"
    except Exception as e:
        print(f"Error: {e}")
        return f"📈【速報】{title}\n注目ニュースが入りました！要チェックだよ！"

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
            
            # カテゴリ分け
            if any(k in title for k in ["優待", "記念", "QUO", "カタログ"]):
                target_webhook = WEBHOOK_YUTAI
            elif any(k in title for k in ["上方修正", "黒字", "増配", "サプライズ"]):
                target_webhook = WEBHOOK_KESSAN
            else:
                target_webhook = WEBHOOK_OTHER
                
            ai_text = ask_gemini_strict(title, link)
            post_to_discord(target_webhook, title, link, ai_text)
            new_seen_list.append(eid)
    
    updated_seen = (new_seen_list + last_seen_list)[:100]
    state["last_seen_list"] = updated_seen
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
