import os
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.sync_api import sync_playwright

# 記号（" や カッコ）を使わず、シンプルにスペース区切りで検索キーワードを指定
# OR検索は OR（大文字）でつなぎます
RAW_QUERY = 'キネコ OR キネコ国際映画祭 OR ワンダフルフィルムハーモニー チケット'

def send_email(subject, body):
    sender_email = os.environ.get("EMAIL_SENDER")
    sender_password = os.environ.get("EMAIL_PASSWORD")
    receiver_email = os.environ.get("EMAIL_RECEIVER")

    if not sender_email or not sender_password or not receiver_email:
        print("メール設定の環境変数が不足しています。")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("メールを送信しました。")
    except Exception as e:
        print(f"メール送信エラー: {e}")

def main():
    # 安全にURLエンコード（クエリ形式）
    encoded_query = urllib.parse.quote_plus(RAW_QUERY)
    search_url = f"https://x.com/search?q={encoded_query}&f=live"
    print(f"アクセス中: {search_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="ja-JP",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()

        try:
            # ページへ移動
            response = page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            
            # ステータスコードの確認
            if response:
                print(f"HTTP Status: {response.status}")

            # 描画待ち
            page.wait_for_timeout(8000)

            # ポスト要素（article）を取得
            articles = page.query_selector_all('article')
            print(f"取得したポスト件数: {len(articles)}件")

            if not articles:
                body_text = page.inner_text('body')
                if "ログイン" in body_text or "Log in" in body_text:
                    print("※ログイン要求画面が表示されています。")
                else:
                    print("※該当するポストが見つかりませんでした。")
                return

            found_posts = []
            for i, article in enumerate(articles[:5]):
                text = article.inner_text()
                links = article.query_selector_all('a')
                post_url = ""
                for link in links:
                    href = link.get_attribute('href')
                    if href and '/status/' in href:
                        post_url = f"https://x.com{href.split('?')[0]}"
                        break
                
                found_posts.append(f"【ポスト {i+1}】\n{text}\nURL: {post_url}\n{'-'*30}")

            if found_posts:
                body = "\n\n".join(found_posts)
                send_email("【Xチケット通知】新しいポストが見つかりました", body)

        except Exception as e:
            print(f"エラーが発生しました: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
