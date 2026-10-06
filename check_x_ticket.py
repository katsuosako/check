import os
import urllib.parse
from playwright.sync_api import sync_playwright
import resend

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
NOTIFICATION_EMAIL = os.environ.get("NOTIFICATION_EMAIL")

# 検索条件の構築:
# 「キネコ国際映画祭」 AND (「ワンダフル フィルムハーモニー」 OR 「Wonderful Film Harmony」) AND (チケット OR 譲渡 OR 譲)
QUERY_TICKET = 'キネコ国際映画祭 ("ワンダフル フィルムハーモニー" OR "Wonderful Film Harmony") (チケット OR 譲渡 OR 譲) -filter:replies'
URL_TICKET = f"https://x.com/search?q={urllib.parse.quote(QUERY_TICKET)}&f=live"

def send_email_notification(tweets):
    if not RESEND_API_KEY or not NOTIFICATION_EMAIL:
        print("Error: RESEND_API_KEY または NOTIFICATION_EMAIL が設定されていません。")
        return

    resend.api_key = RESEND_API_KEY
    
    content = "【🎟️ キネコ国際映画祭（ワンダフル フィルムハーモニー）チケット譲渡ポスト検知】\n"
    content += "=========================================\n\n"
    for text in tweets:
        content += f"{text}\n-----------------------------------------\n"

    params = {
        "from": "onboarding@resend.dev",
        "to": [NOTIFICATION_EMAIL],
        "subject": "【X通知】キネコ国際映画祭 チケット譲渡の最新ポスト",
        "text": content,
    }

    try:
        response = resend.Emails.send(params)
        print(f"メール送信完了: {response}")
    except Exception as e:
        print(f"メール送信エラー: {e}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print(f"アクセス中: {URL_TICKET}")
        page.goto(URL_TICKET, wait_until="domcontentloaded")

        try:
            page.wait_for_selector("article", timeout=8000)
        except Exception:
            print("新規ポストが見つからないか、読み込みタイムアウトになりました。")
            browser.close()
            return

        articles = page.query_selector_all("article")
        tweets = []

        for article in articles[:5]:  # 最新5件を取得
            text = article.inner_text()
            cleaned_text = "\n".join([line.strip() for line in text.split("\n") if line.strip()])
            tweets.append(cleaned_text)

        browser.close()

        if tweets:
            print(f"検知結果: チケット譲渡関連ポスト {len(tweets)} 件")
            send_email_notification(tweets)
        else:
            print("該当する新しいポストは見つかりませんでした。")

if __name__ == "__main__":
    main()
