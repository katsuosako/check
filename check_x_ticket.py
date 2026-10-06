import os
import urllib.parse
import xml.etree.ElementTree as ET
import requests
import resend

# 検索パターンの定義
QUERIES = [
    'ワンダフルフィルムハーモニー',
    'キネコ チケット',
    'キネコ 譲渡',
    'キネコ 譲'
]

HISTORY_FILE = "notified_ids.txt"

def load_notified_urls():
    """過去に通知済みのURL一覧を読み込む"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_notified_urls(new_urls):
    """新しい通知済みURLをファイルに追記する"""
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        for url in new_urls:
            f.write(f"{url}\n")

def send_email(subject, body):
    api_key = os.environ.get("RESEND_API_KEY")
    to_email = os.environ.get("NOTIFICATION_EMAIL")

    if not api_key or not to_email:
        print("Resendの設定（RESEND_API_KEY / NOTIFICATION_EMAIL）が不足しています。")
        return

    resend.api_key = api_key

    try:
        resend.Emails.send({
            "from": "Ticket Monitor <onboarding@resend.dev>",
            "to": [to_email],
            "subject": subject,
            "text": body,
        })
        print("メールを送信しました。")
    except Exception as e:
        print(f"メール送信エラー: {e}")

def fetch_tweets_for_query(query, nitter_instances):
    encoded_query = urllib.parse.quote(query)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for instance in nitter_instances:
        rss_url = f"{instance}/search/rss?f=tweets&q={encoded_query}"
        
        try:
            response = requests.get(rss_url, headers=headers, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                items = root.findall('.//item')
                
                posts = []
                for item in items[:5]:
                    title = item.find('title').text if item.find('title') is not None else ""
                    link = item.find('link').text if item.find('link') is not None else ""
                    
                    x_link = link
                    for inst in nitter_instances:
                        x_link = x_link.replace(inst, "https://x.com")
                    
                    posts.append({
                        "link": x_link,
                        "text": f"【投稿内容】\n{title}\n\nURL: {x_link}\n{'-'*30}"
                    })
                return posts
        except Exception:
            continue

    return []

def main():
    nitter_instances = [
        "https://nitter.net",
        "https://nitter.cz",
        "https://nitter.it",
        "https://nitter.download",
        "https://nitter.projectsegfau.lt"
    ]

    notified_urls = load_notified_urls()
    print(f"過去に通知済みの件数: {len(notified_urls)}件")

    new_posts = []
    new_urls = []
    seen_in_this_run = set()

    for query in QUERIES:
        print(f"検索中: {query}")
        posts = fetch_tweets_for_query(query, nitter_instances)
        
        for post in posts:
            url = post["link"]
            # 未通知 兼 今回の実行で未処理のものを抽出
            if url not in notified_urls and url not in seen_in_this_run:
                seen_in_this_run.add(url)
                new_urls.append(url)
                new_posts.append(post["text"])

    print(f"新規取得ポスト件数: {len(new_posts)}件")

    if new_posts:
        body = "\n\n".join(new_posts)
        send_email("【Xチケット通知】新しいポストが見つかりました", body)
        save_notified_urls(new_urls)
    else:
        print("新しい未通知のポストは見つかりませんでした。")

if __name__ == "__main__":
    main()
