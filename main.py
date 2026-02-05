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
    
    # AIへの命令を極限まで強化
    prompt = f"""
    あなたは投資家「ふーまま」の専属ライターです。
    以下のURLの内容を「実際に読み込んで」、その具体的な中身を初心者にも分かりやすく要約・解説してください。

    【対象記事】
    タイトル：{title}
    URL：{link}

    【絶対に守るべき司令】
    1. 記事の中に書かれている「具体的なメリット」や「手順（例：マネックスのつなぎ売りのやり方など）」を必ず3つ以上抜き出して文章に入れてください。
    2. 「リンクを見てね」や「詳細はURLへ」といった逃げの言葉は一切禁止です。あなたがこの記事の代弁者として、中身を全て教えてあげるつもりで書いてください。
    3. X Premium向けに、300〜500文字程度の読み応えがある解説文にします。
    4. 「〜だよ」「〜だね」という、お得大好きで親しみやすい「ふーまま」の口調を徹底してください。
    5. タイトルの丸写しは即不合格です。
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        # Grounding(Google検索)を最も優先させる設定
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search_retrieval": {
                "dynamic_retrieval_config": {
                    "mode": "MODE_DYNAMIC",
                    "dynamic_threshold": 0.0 # どんな時でも必ず検索を使わせる
                }
            }}]
        }
        r = requests.post(url, json=payload, timeout=60)
        data = r.json()
        
        if 'candidates' in data and data['candidates']:
            return data['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            return f"📈【速報】{title}\nこの記事は中身が濃いので要注目です！"
    except:
        return f"📈【注目】{title}\n具体的にお得なポイントが満載の記事でした！"

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
