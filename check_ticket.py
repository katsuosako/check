import os
import sys
from playwright.sync_api import sync_playwright
import resend

# 監視したいURLをリストで指定します
TARGET_URLS = [
    "https://kineko-invite.vercel.app/tickets/buy?screening_id=0d1e2b8c-6f4a-4e1b-9c7d-3a5b8e2f7c41&date=11/1",
    "https://kineko-invite.vercel.app/tickets/buy?screening_id=7b3c9d5e-2a81-4f6c-b0d4-9e1f6a8c3b52&date=11/1"
]

def check_ticket_status():
    available_urls = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        for url in TARGET_URLS:
            print(f"Navigating to {url}...")
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                
                # ログイン画面に飛ばされた場合
                if "ログイン" in page.title() or page.locator("text=招待管理ツール ログイン").is_visible():
                    print(f"[{url}] Status: ログイン画面へリダイレクトされました。")
                    continue

                sold_out_element = page.locator("text=売り切れ")
                disabled_button = page.locator("button[disabled]")
                
                is_sold_out = sold_out_element.is_visible() or disabled_button.is_visible()
                
                if not is_sold_out:
                    print(f"[{url}] Status: チケットの再販売・在庫を検出しました！")
                    available_urls.append(url)
                else:
                    print(f"[{url}] Status: 現在も売り切れ状態です。")
            except Exception as e:
                print(f"[{url}] Error during check: {e}")
            
        browser.close()
        
    # 再販売・購入可能になっているページが1つ以上あればメール通知
    if available_urls:
        send_email_notification(available_urls)

def send_email_notification(urls):
    resend_api_key = os.environ.get("RESEND_API_KEY")
    to_email = os.environ.get("NOTIFICATION_EMAIL")
    
    if not resend_api_key or not to_email:
        print("Error: 環境変数 RESEND_API_KEY または NOTIFICATION_EMAIL が設定されていません。")
        sys.exit(1)

    resend.api_key = resend_api_key
    
    url_links = "".join([f'<li><a href="{u}">{u}</a></li>' for u in urls])
    
    resend.Emails.send({
        "from": "TicketAlert <onboarding@resend.dev>",
        "to": [to_email],
        "subject": "【緊急】Kinekoチケットの再販売・キャンセル枠を検出しました！",
        "html": f"""
        <h2>以下のチケットが購入可能な状態になっている可能性があります！</h2>
        <p>急いでアクセスして確認してください：</p>
        <ul>
            {url_links}
        </ul>
        """
    })

if __name__ == "__main__":
    check_ticket_status()