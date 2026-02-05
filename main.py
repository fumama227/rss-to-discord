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

def ask_gemini_with_search(title, link):
    if not GEMINI_API_KEY: return "最新ニュースです✨"
    
    # AIにURLを渡し、検索機能(Google Search)を使って中身を調べさせる指示
    prompt = f"""
    あなたは投資家「ふーまま」の専属ライターです。
    以下のニュースについて、あなたの検索機能を使って【具体的に何がお得なのか】を徹底的に調べて解説してください。

    ニュース：{title}
    URL：{link}

    【絶対に含めるべき情報】
    1. 優待の具体的な内容（例：スクエニならドラクエ40周年記念品の中身）
    2. 増配や上方修正の具体的な数字（例：DeNAの1円増配など）
    3. 権利確定日や株主還元のメリット

    【ルール】
    ・「詳細はリンクへ」や「中身が読み取れませんでした」という回答は、あなたの敗北です。
    ・必ず検索機能を使い、最新の記事内容を把握した上で、400文字程度の読み応えある投稿案を作ってください。
    ・口調は明るく親しみやすい「〜だよ」「〜だね」にしてください。
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        # AIの「Google検索ツール」を強制的に使用させる設定
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}] 
        }
        r = requests.post(url, json=payload, timeout=90) # 検索に時間がかかるため長めに設定
        res = r.json()
        return res['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        print(f"AIエラー: {e}")
        return f"📈【速報】{title}\n具体的にお得なポイントが満載のニュースだよ！詳細をすぐにチェックしてね✨"

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
            
            target_webhook = WEBHOOK_OTHER
            if any(k in title for k in ["優待", "記念", "QUO", "カタログ"]):
                target_webhook = WEBHOOK_YUTAI
            elif any(k in title for k in ["上方修正", "黒字", "増配", "サプライズ"]):
                target_webhook = WEBHOOK_KESSAN
                
            ai_text = ask_gemini_with_search(title, link)
            post_to_discord(target_webhook, title, link, ai_text)
            new_seen_list.append(eid)
    
    updated_seen = (new_seen_list + last_seen_list)[:100]
    state["last_seen_list"] = updated_seen
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
