import os
import json
import smtplib
import requests
import feedparser
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 設定：Discord用 ---
WEBHOOK_OTHER = os.environ.get("DISCORD_WEBHOOK_URL")
WEBHOOK_YUTAI = os.environ.get("WEBHOOK_YUTAI")
WEBHOOK_KESSAN = os.environ.get("WEBHOOK_KESSAN")

# --- 設定：メール用 ---
MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
MAIL_TO = os.environ.get("MAIL_TO")

# --- RSS設定 ---
RSS_URLS = [os.environ.get("RSS_URL"), os.environ.get("RSS_URL_2")]

def post_to_discord(webhook_url, title, link):
    """Discordにリンクを通知する"""
    target_url = webhook_url if webhook_url else WEBHOOK_OTHER
    if not target_url:
        return
    
    content = f"📰 **【新着ニュース】**\n{title}\n{link}"
    try:
        requests.post(target_url, json={"content": content}, timeout=30)
    except Exception as e:
        print(f"Discord送信エラー: {e}")

def send_combined_email(news_items):
    """溜まったニュースを1通のメールにまとめて送る"""
    if not news_items or not MAIL_USERNAME or not MAIL_PASSWORD or not MAIL_TO:
        return

    msg = MIMEMultipart()
    msg['From'] = MAIL_USERNAME
    msg['To'] = MAIL_TO
    msg['Subject'] = f"【一括通知】新着株ニュース（{len(news_items)}件）"

    # メールの本文を作成
    body_intro = "新しいニュースが届きました！\n\n"
    body_items = ""
    for item in news_items:
        body_items += f"■カテゴリ: {item['category']}\n"
        body_items += f"■タイトル: {item['title']}\n"
        body_items += f"■リンク: {item['link']}\n"
        body_items += "---------------------------\n\n"

    body_footer = """
Geminiに「ニュース調査フォルダを見て」と言うと、
このメールを読み込んで分析できます。
"""
    full_body = body_intro + body_items + body_footer
    msg.attach(MIMEText(full_body, 'plain'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"メール一括送信成功: {len(news_items)}件のニュース")
    except Exception as e:
        print(f"メール送信エラー: {e}")

def main():
    state_path = Path("state.json")
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    last_seen_list = state.get("last_seen_list", [])
    new_seen_list = []
    
    # 送信用にニュースを溜めるリスト
    pending_news_for_email = []
    
    for url in RSS_URLS:
        if not url: continue
        feed = feedparser.parse(url)
        for e in reversed(feed.entries):
            eid = getattr(e, "id", None) or getattr(e, "link", "")
            if eid in last_seen_list: continue
            
            title = getattr(e, "title", "")
            link = getattr(e, "link", "")
            
            # カテゴリ判定
            category = "速報"
            target_webhook = WEBHOOK_OTHER
            
            if any(k in title for k in ["優待", "記念", "QUO", "カタログ"]):
                category = "優待"
                target_webhook = WEBHOOK_YUTAI
            elif any(k in title for k in ["上方修正", "黒字", "増配", "サプライズ"]):
                category = "決算"
                target_webhook = WEBHOOK_KESSAN
            
            # 1. Discordに送る（即座に通知）
            post_to_discord(target_webhook, title, link)
            
            # 2. メールのリストに追加
            pending_news_for_email.append({
                "title": title,
                "link": link,
                "category": category
            })
            
            new_seen_list.append(eid)
    
    # 最後にメールを1通だけ送る
    if pending_news_for_email:
        send_combined_email(pending_news_for_email)
    
    updated_seen = (new_seen_list + last_seen_list)[:100]
    state["last_seen_list"] = updated_seen
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
