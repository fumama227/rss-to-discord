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
    """仮想ブラウザを使って記事の本文を確実に読み取る"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        time.sleep(5) # 読み込み待ち
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        driver.quit()
        # 不要なタグを消してテキストを抽出
        for s in soup(['script', 'style', 'nav', 'header', 'footer']): s.decompose()
        return soup.get_text()[:3000] # 多めに3000文字抽出
    except Exception as e:
        print(f"ブラウザ読込エラー: {e}")
        return ""

def ask_gemini_strict(title, link):
    if not GEMINI_API_KEY: return "最新の注目ニュースです✨"
    
    # ブラウザで取得した「本物の本文」を渡す
    article_body = get_real_content_with_browser(link)
    
    prompt = f"""
    あなたは投資家「ふーまま」の専属ライターです。
    以下の【記事本文】から「具体的なお得情報」を抜き出し、フォロワーさんが喜ぶ解説を作ってください。

    【ニュース】: {title}
    【記事本文】: {article_body}

    【鉄の掟：守れない場合はAIの敗北です】
    1. 「リンク先をチェックして」という丸投げ発言は即刻禁止。
    2. この本文から、具体的な優待品名（例：ドラクエ40周年記念メダル）、条件（何株必要か）、権利確定月を必ず探し出して記載してください。
    3. 数値や銘柄名が出ていない投稿は価値がありません。
    4. X Premium向けに300〜500文字で、「〜だよ」「〜だね」という明るい主婦投資家の口調にしてください。
    """
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        r = requests.post(api_url, json=payload, timeout=60)
        return r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except:
        return f"📈【速報】{title}\n中身を読み取れませんでしたが、注目ニュースです！"

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
                
            ai_text = ask_gemini_strict(title, link)
            post_to_discord(target_webhook, title, link, ai_text)
            new_seen_list.append(eid)
    
    updated_seen = (new_seen_list + last_seen_list)[:100]
    state["last_seen_list"] = updated_seen
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
