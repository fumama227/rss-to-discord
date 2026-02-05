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

def ask_gemini(title):
    if not GEMINI_API_KEY: return "最新の注目ニュースです✨"
    
    # X Premium向けの長文・詳細解説プロンプト
    prompt = f"""
    以下の株ニュースを元に、X（旧Twitter）向けの魅力的な紹介文を作成してください。
    投資家「ふーまま」として、主婦や投資初心者のフォロワーさんに喜ばれる内容にしてください。

    ニュース：{title}

    【投稿の構成案】
    1. 【驚きや喜びの導入】（例：えっ！すごいニュースきたよ！✨）
    2. 【ニュースの分かりやすい解説】（専門用語を避け、何が起きたか具体的に）
    3. 【ふーまま流の注目ポイント】（「家計が助かるね」「利回りが期待できそう」などのお得目線）
    4. 【フォロワーへの問いかけや締め】（例：みんなはどう思う？チェックしてみてね！）

    【ルール】
    ・明るく親しみやすい、丁寧な言葉遣い（「〜だよ」「〜だね」）にする。
    ・お得大好き（ポイ活・優待好き）な個性を出す。
    ・長文投稿が可能なので、100文字などの制限は気にせず、内容を充実させる。
    ・最後に適切なハッシュタグを3〜5個つける。
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        return r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except:
        return f"📈【速報】{title}\n注目ニュースが入りました！要チェックです！"

def post_to_discord(webhook_url, title, link, ai_text):
    current_webhook = webhook_url if webhook_url else WEBHOOK_OTHER
    # Discord側でも読みやすいように整形
    content = f"📰 **【最新ニュース速報】**\n{title}\n\n✍️ **AI作成のSNS投稿案（X Premium対応）:**\n{ai_text}\n\n🔗 **詳細リンク:** {link}"
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
            
            # カテゴリ判定
            if any(k in title for k in ["優待", "記念", "QUO", "カタログ"]):
                target_webhook = WEBHOOK_YUTAI
            elif any(k in title for k in ["上方修正", "黒字", "増配", "サプライズ"]):
                target_webhook = WEBHOOK_KESSAN
            else:
                target_webhook = WEBHOOK_OTHER
                
            ai_text = ask_gemini(title)
            post_to_discord(target_webhook, title, link, ai_text)
            new_seen_list.append(eid)
    
    # 既読リストを更新（最大100件）
    updated_seen = (new_seen_list + last_seen_list)[:100]
    state["last_seen_list"] = updated_seen
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
