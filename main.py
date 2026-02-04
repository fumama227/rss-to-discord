import os
import feedparser
import requests

# GitHubのSettings > Secretsで設定した値を取得
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
RSS_URL = os.environ.get("RSS_URL")

def post_to_discord(title, link):
    """Discordにメッセージを送信する"""
    content = f"📰 **株探速報テスト**\n【タイトル】: {title}\n【リンク】: {link}"
    payload = {"content": content}
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
        response.raise_for_status()
        print(f"成功: {title}")
    except Exception as e:
        print(f"送信失敗: {e}")

def main():
    print(f"取得開始: {RSS_URL}")
    
    # RSSフィードを読み込み
    feed = feedparser.parse(RSS_URL)
    
    # ニュースが取得できているかチェック
    if not feed.entries:
        print("ニュースが見つかりませんでした。URLが正しいか確認してください。")
        # デバッグ用にDiscordへ直接メッセージを送ってみる
        post_to_discord("システム起動テスト", "RSSからニュースが取得できませんでした。URLを確認してください。")
        return

    # テストのため、既読チェックを無視して最新の5件を強制的に送信する
    print(f"{len(feed.entries)}件のニュースを発見。最新5件を送信します。")
    
    for entry in feed.entries[:5]:
        title = entry.get("title", "タイトルなし")
        link = entry.get("link", "")
        post_to_discord(title, link)

if __name__ == "__main__":
    main()
