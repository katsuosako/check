import os
import urllib.parse
import xml.etree.ElementTree as ET
import requests
import resend

# 検索クエリの設定
QUERY = 'ワンダフルフィルムハーモニー OR キネコ国際映画祭 OR キネコ チケット OR 譲 OR 譲渡'

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

def fetch_tweets_via_nitter(query):
    encoded_query = urllib.parse.quote(query)
    
    # 稼働状況の良い Nitter パブリックインスタンスのリストに更新
    nitter_instances = [
        "https://nitter.net",
        "https://nitter.cz",
        "https://nitter.it",
        "https://nitter.download",
        "https://nitter.projectsegfau.lt"
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for instance in nitter_instances:
        rss_url = f"{instance}/search/rss?f=tweets&q={encoded_query}"
        print(f"試行中: {rss_url}")
        
        try:
            response = requests.get(rss_url, headers=headers, timeout=10)
            if response.status_code == 200:
                print(f"取得成功 ({instance})")
                
                # RSS (XML) のパース
                root = ET.fromstring(response.content)
                items = root.findall('.//item')
                
                found_posts = []
                for item in items[:5]:  # 最新5件を取得
                    title = item.find('title').text if item.find('title') is not None else ""
                    link = item.find('link').text if item.find('link') is not None else ""
                    
                    # Nitterリンクを本家 x.com リンクに自動変換
                    x_link = link
                    for inst in nitter_instances:
                        x_link = x_link.replace(inst, "https://x.com")
                    
                    found_posts.append(f"【投稿内容】\n{title}\n\nURL: {x_link}\n{'-'*30}")
                
                return found_posts
            else:
                print(f"ステータスコード: {response.status_code}")
        except Exception as e:
            print(f"接続失敗 ({instance}): {e}")

    return []

def main():
    print(f"検索を開始します: {QUERY}")
    posts = fetch_tweets_via_nitter(QUERY)
    print(f"取得したポスト件数: {len(posts)}件")

    if posts:
        body = "\n\n".join(posts)
        send_email("【Xチケット通知】新しいポストが見つかりました", body)
    else:
        print("該当するポストは見つかりませんでした。")

if __name__ == "__main__":
    main()
