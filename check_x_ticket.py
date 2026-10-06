import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 検索クエリの設定
RAW_QUERY = 'キネコ OR キネコ国際映画祭 OR "ワンダフル フィルムハーモニー" チケット'

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

def get_guest_token(session):
    """Xのゲストトークンを直接発行取得する"""
    headers = {
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA'
    }
    try:
        res = session.post('https://api.x.com/1.1/guest/activate.json', headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json().get('guest_token')
        print(f"ゲストトークン取得失敗: HTTP {res.status_code}")
    except Exception as e:
        print(f"ゲストトークン取得エラー: {e}")
    return None

def search_x_tweets(query):
    session = requests.Session()
    guest_token = get_guest_token(session)
    
    if not guest_token:
        print("ゲストトークンが取得できなかったため検索をスキップします。")
        return []

    headers = {
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
        'x-guest-token': guest_token,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }

    params = {
        'q': query,
        'tweet_search_mode': 'live',
        'count': 10,
        'query_source': 'typed_query'
    }

    url = 'https://x.com/i/api/2/search/adaptive.json'
    try:
        res = session.get(url, headers=headers, params=params, timeout=15)
        print(f"API Response Status: {res.status_code}")
        
        if res.status_code != 200:
            return []

        data = res.json()
        tweets_dict = data.get('globalObjects', {}).get('tweets', {})
        users_dict = data.get('globalObjects', {}).get('users', {})

        found_posts = []
        for tweet_id, tweet in tweets_dict.items():
            user_id = tweet.get('user_id_str')
            user_info = users_dict.get(user_id, {})
            screen_name = user_info.get('screen_name', 'unknown')
            text = tweet.get('full_text', '')
            
            post_url = f"https://x.com/{screen_name}/status/{tweet_id}"
            found_posts.append(f"【@{screen_name}】\n{text}\nURL: {post_url}\n{'-'*30}")

        return found_posts
    except Exception as e:
        print(f"検索リクエストエラー: {e}")
        return []

def main():
    print(f"検索を開始します: {RAW_QUERY}")
    posts = search_x_tweets(RAW_QUERY)
    print(f"取得したポスト件数: {len(posts)}件")

    if posts:
        body = "\n\n".join(posts[:5])  # 最新5件を送信
        send_email("【Xチケット通知】新しいポストが見つかりました", body)
    else:
        print("該当するポストは見つかりませんでした。")

if __name__ == "__main__":
    main()
