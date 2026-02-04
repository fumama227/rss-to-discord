import os
import json
from pathlib import Path
import feedparser
import requests

# 設定
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
RSS_URL = os.environ["RSS_URL"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
STATE_FILE = Path("state.json")

def ask_gemini(title):
    """GeminiにSNS投稿文を考えてもらう"""
    prompt = f"""
    以下の株ニュースのタイトルを元に、SNS（X）で主婦層や投資初心者向けに発信する「お得感」のある投稿文を作成してください。
    
    【ルール】
    ・「ふーまま」というキャラクターにふさわしい親しみやすい言葉遣い
    ・絵文字を適度に使用する
    ・「サプライズ」「増配」「優待」などの注目ポイントを強調する
    ・ハッシュタグを2〜3個つける
    ・140文字以内
    
    タイトル: {title}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return "（投稿文の自動作成に失敗しました）"

def post_to_discord(title, link, ai_text):
    """DiscordにニュースとAIの投稿案を送る"""
    content = (
        f"📰 **【最新速報】**\n{title}\n\n"
        f"✍️ **SNS投稿案:**\n{ai_text}\n\n"
        f"🔗 **詳細:** {link}\n"
        f"------------------------------------"
    )
    data = {"content": content}
    requests.post(WEBHOOK_URL, json=data, timeout=30)

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except:
            return {}
    return {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

def main():
    state = load_state()
    last_seen = state.get("last_seen", "")
    feed = feedparser.parse(RSS_URL)
    entries = list(reversed(feed.entries))

    new_items = []
    for e in entries:
        eid = getattr(e, "id", None) or getattr(e, "link", "")
        if last_seen and eid == last_seen:
            new_items = []
            continue
        new_items.append(e)

    # 最新3件までをAIで加工して送信
    for e in new_items[-3:]:
        title = getattr(e, "title", "No title")
        link = getattr(e, "link", "")
        if link:
            ai_text = ask_gemini(title)
            post_to_discord(title, link, ai_text)

    if feed.entries:
        state["last_seen"] = getattr(feed.entries[0], "id", None) or getattr(feed.entries[0], "link", "")
        save_state(state)

if __name__ == "__main__":
    main()
