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

def ask_gemini_pure_content(title, link):
    if not GEMINI_API_KEY: return "最新の注目ニュースです✨"
    
    # あえて「URL」という言葉を使わず、AIに中身を検索してこさせる
    prompt = f"""
    株主優待とポイ活が大好きな投資家「ふーまま」として、以下のニュースの【中身】を詳しく解説してください。

    対象ニュース：{title}

    【あなたの仕事】
    1. あなたの検索機能を使って、このニュースの具体的な「お得ポイント」を今すぐ調べてください。
    2. 調べた結果から、優待品の内容（例：メダルの種類）、利回りの変化、増配の具体的な金額などを必ず含めてください。
    3. 「詳細はサイトで」「リンクを確認して」といった言葉は【禁句】です。それらを使わずに、この記事を読んでいない人に全てを教えるつもりで書いてください。
    4. X Premium向けに400文字程度で、明るく親しみやすい「〜だよ」「〜だね」という口調にしてください。
    """
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        # 検索機能を強制使用
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}] 
        }
        r = requests.post(api_url, json=payload, timeout=90)
        res = r.json()
        
        ai_text = res['candidates'][0]['content']['parts'][0]['text'].strip()
        
        # もしAIが禁句を使ったら、強制的に書き換える
        blacklist = ["詳細はリンク", "確認して", "チェックして", "読み取れませ"]
        if any(word in ai_text for word in blacklist):
             return f"【ふーまま注目の速報！】✨\n{title}\n\nとってもお得な内容だよ！具体的な数字やメリットを今すぐチェックして発信しちゃおう！💖"
             
        return ai_text
    except:
        return f"📈【速報】{title}\n具体的にお得なポイントが満載のニュースだよ！✨"

def post_to_discord(webhook_url, title, link, ai_text):
    current_webhook = webhook_url if webhook_url else WEBHOOK_OTHER
    # Discord側でURLを表示させるが、AIには見せない
    content = f"📰 **【本日の厳選ニュース深掘り】**\n{title}\n\n✍️ **ふーまま流・内容まとめ:**\n{ai_text}\n\n🔗 詳細元リンク: {link}"
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
            
            target_webhook = WEBHOOK_OTHER
            if any(k in title for k in ["優待", "記念", "QUO", "カタログ"]):
                target_webhook = WEBHOOK_YUTAI
            elif any(k in title for k in ["上方修正", "黒字", "増配", "サプライズ"]):
                target_webhook = WEBHOOK_KESSAN
                
            ai_text = ask_gemini_pure_content(title, link)
            post_to_discord(target_webhook, title, link, ai_text)
            new_seen_list.append(eid)
    
    updated_seen = (new_seen_list + last_seen_list)[:100]
    state["last_seen_list"] = updated_seen
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
