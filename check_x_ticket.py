import os
import urllib.parse
import xml.etree.ElementTree as ET
import requests
import resend

# 複数の検索パターンを定義（Nitter側で確実に処理させるため個別定義）
QUERIES = [
    'ワンダフルフィルムハーモニー',
    'キネコ チケット',
    'キネコ 譲渡',
    'キネコ 譲'
]

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

    all_posts = []
    seen_links = set()

    for query in QUERIES:
        print(f"検索中: {query}")
        posts = fetch_tweets_for_query(query, nitter_instances)
        
        # 重複する投稿を除外しながら追加
        for post in posts:
            if post["link"] not in seen_links:
                seen_links.add(post["link"])
                all_posts.append(post["text"])

    print(f"取得したユニークポスト件数: {len(all_posts)}件")

    if all_posts:
        body = "\n\n".join(all_posts)
        send_email("【Xチケット通知】新しいポストが見つかりました", body)
    else:
        print("該当するポストは見つかりませんでした。")

if __name__ == "__main__":
    main()
