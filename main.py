import os
import json
import time
from pathlib import Path
import feedparser
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 設定
WEBHOOK_OTHER = os.environ.get("DISCORD_WEBHOOK_URL")
WEBHOOK_YUTAI = os.environ.get("WEBHOOK_YUTAI")
WEBHOOK_KESSAN = os.environ.get("WEBHOOK_KESSAN")
RSS_URLS = [os.environ.get("RSS_URL"), os.environ.get("RSS_URL_2")]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def get_real_content_with_browser(url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--lang=ja-JP')
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        time.sleep(8) # 読み込み時間を少し長めに
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        driver.quit()
        for s in soup(['script', 'style', 'nav', 'header', 'footer']): s.decompose()
        return soup.get_text()[:4000] # 文字数制限も少し増やしました
    except Exception as e:
        print(f"詳細エラー: {e}")
        return ""

def ask_gemini_strict(title, link):
    if not GEMINI_API_KEY: return "最新の注目ニュースです✨"
    article_body = get_real_content_with_browser(link)
    
    prompt = f"""
    あなたは投資家「ふーまま」の専属ライターです。
    以下の【記事本文】から、具体的なお得ポイント（優待内容、権利月、数値など）を必ず抜き出して解説してください。

    【ニュース】: {title}
    【記事本文】: {article_body}

    【ルール】
    1. 「中身を読み取れませんでした」や「詳細はリンクへ」といった逃げの言葉は厳禁です。
    2. 本文からドラクエ記念品の内容や利回り、増配額などを具体的に探してください。
    3. X Premium向けに300文字以上で、親しみやすい主婦投資家の口調にしてください。
    """
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        r = requests.post(api_url, json=payload, timeout=60)
        return r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except:
        return f"📈【速報】{title}\n注目ニュースです！"

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
                
            ai_text = ask_gemini_strict(title, link)
            post_to_discord(target_webhook, title, link, ai_text)
            new_seen_list.append(eid)
    
    updated_seen = (new_seen_list + last_seen_list)[:100]
    state["last_seen_list"] = updated_seen
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

def post_to_discord(webhook_url, title, link, ai_text):
    current_webhook = webhook_url if webhook_url else WEBHOOK_OTHER
    content = f"📰 **【本日の厳選ニュース深掘り】**\n{title}\n\n✍️ **ふーまま流・内容まとめ:**\n{ai_text}\n\n🔗 {link}"
    requests.post(current_webhook, json={"content": content}, timeout=30)

if __name__ == "__main__":
    main()
