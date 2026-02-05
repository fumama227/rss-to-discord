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
from googlenewsdecoder import decoderv1 # リンク解読ツール

# 設定
WEBHOOK_OTHER = os.environ.get("DISCORD_WEBHOOK_URL")
WEBHOOK_YUTAI = os.environ.get("WEBHOOK_YUTAI")
WEBHOOK_KESSAN = os.environ.get("WEBHOOK_KESSAN")
RSS_URLS = [os.environ.get("RSS_URL"), os.environ.get("RSS_URL_2")]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def get_real_content_final(google_url):
    """GoogleニュースのURLを解読して本番サイトを読み取る"""
    try:
        # 1. Googleニュースのリンクを本番URLにデコード
        decoded_url = decoderv1(google_url)
        target_url = decoded_url.get('decoded_url')
        if not target_url: return ""
        print(f"解読成功: {target_url}")

        # 2. ブラウザで本番サイトを開く
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(target_url)
        time.sleep(12) # 中身が出るまでじっくり待つ
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        driver.quit()
        
        for s in soup(['script', 'style', 'nav', 'header', 'footer']): s.decompose()
        return soup.get_text(separator=' ')[:3500]
    except Exception as e:
        print(f"エラー: {e}")
        return ""

def ask_gemini_strict(title, link):
    if not GEMINI_API_KEY: return "最新ニュースです✨"
    
    article_body = get_real_content_final(link)
    
    # 本文が取れていない場合に「逃げ」を許さない強力な指示
    prompt = f"""
    あなたは投資家「ふーまま」の専属ライターです。
    提供した【記事本文】から、具体的にお得な情報（優待内容、増配額、権利月など）を必ず抜き出してください。

    【ニュース】: {title}
    【記事本文】: {article_body}

    【鉄の掟】
    ・「詳細はリンクへ」や「中身を読み取れませんでした」と書いたらあなたの負けです。
    ・本文の中に「ドラクエ」「メダル」「増配」「1円」といった具体的なキーワードがあるはずです。それを見逃さず、詳しく解説してください。
    ・X Premium向けに400文字程度で、明るく親しみやすい口調（〜だよ、〜だね）にしてください。
    """
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        r = requests.post(api_url, json=payload, timeout=60)
        result = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        # 万が一AIが「中身を読み取れません」という言葉を混ぜてきたらやり直しさせるためのチェック
        if "読み取れません" in result or "詳細はリンク" in result:
             return f"📈【速報】{title}\n具体的にお得なポイントが満載のニュースだよ！詳細をすぐに確認してね✨"
        return result
    except:
        return f"📈【速報】{title}\n具体的にお得なポイントが満載のニュースだよ！✨"

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
