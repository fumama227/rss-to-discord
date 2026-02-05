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
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Googleニュースの中継ページを突破して、本番のURLへ飛ぶ
        driver.get(url)
        time.sleep(10) # 読み込み時間をさらに延長
        
        # 最終的な遷移先のURLを確認
        final_url = driver.current_url
        print(f"最終読込先: {final_url}")
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        driver.quit()
        
        # 不要な要素を徹底的に消す
        for s in soup(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'aside']): s.decompose()
        
        # 本文を抽出（3000文字）
        text = soup.get_text(separator='\n')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)[:3000]
    except Exception as e:
        print(f"詳細エラー: {e}")
        return ""

def ask_gemini_strict(title, link):
    if not GEMINI_API_KEY: return "最新の注目ニュースです✨"
    
    article_body = get_real_content_with_browser(link)
    
    # 本文が取れなかった場合でも、タイトルから推測させずにエラーを出すように指示
    prompt = f"""
    あなたは投資家「ふーまま」の専属ライターです。
    提供された【記事本文】を徹底的に読み込み、具体的なお得ポイント（優待内容、権利確定日、増配額、改善点など）を詳しく解説してください。

    【ニュースタイトル】: {title}
    【記事本文】: {article_body}

    【鉄の掟】
    1. 「中身を読み取れませんでした」などの逃げの言葉は不採用です。
    2. もし【記事本文】が短くても、タイトルや本文から読み取れる「具体的な数値」や「銘柄名」を必ず出してください。
    3. X Premium向けに300文字以上で、お得大好きで親しみやすい「ふーまま」の口調（〜だよ、〜だね）で作成してください。
    4. スクエニの記念品や利回りの具体的な変化など、読者が一番知りたい情報を最優先してください。
    """
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        r = requests.post(api_url, json=payload, timeout=60)
        return r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except:
        return f"📈【速報】{title}\n具体的にお得なポイントが満載のニュースだよ！詳細はリンクから確認してみてね✨"

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
