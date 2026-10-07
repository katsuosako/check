import os
import urllib.parse
import xml.etree.ElementTree as ET
import re
import requests
import resend

# =========================================================
# 検索設定（完全一致 ＋ 認証アカウント限定 ＋ リプライ除外）
# =========================================================
QUERIES = [
    '"小原好美" filter:verified -filter:replies',
    '#小原好美 filter:verified -filter:replies',
    '"加隈亜衣" filter:verified -filter:replies',
    '#加隈亜衣 filter:verified -filter:replies'
]

# 除外したいユーザーのIDリスト（@を含めずに記述）
EXCLUDE_USERS = [
    "MALMUNIA",
    "yukki_tcg"
]

# 判定キーワードリスト（以下のいずれかが本文に含まれている場合のみ通過）
ANNOUNCEMENT_KEYWORDS = [
    'サイン', '色紙', '直筆',          # サイン関連
    'お知らせ', '情報解禁', '解禁',     # 告知関連
    '出演', '決定', '開催', '発売',      # イベント・出演・リリース関連
    'プレゼント', 'キャンペーン', 'フォロー', 'RT', # 企画・抽選関連
    '公式', '特設', '配信', '放送'       # メディア・配信関連
]

HISTORY_FILE = "notified_person_ids_K.txt"

def extract_post_id(url):
    """URLから投稿ID（数字）を抽出して正規化"""
    match = re.search(r'/status/(\d+)', url)
    if match:
        return match.group(1)
    return url.split('?')[0].split('#')[0].rstrip('/')

def load_notified_ids():
    """過去に通知済みの投稿ID一覧を読み込む"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_notified_ids(new_ids):
    """新しい通知済みIDをファイルに追記する"""
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        for post_id in new_ids:
            f.write(f"{post_id}\n")

def is_official_announcement(title):
    """一般の日常投稿やリプライを除外し、告知・サイン関連ポストのみ通過させる"""
    text = title.strip()
    
    # 1. リプライ投稿の除外
    # Nitter形式（"R to @user:"）および 標準形式（"@user"）のどちらも除外する
    if text.startswith("@") or re.match(r'^R\s+to\s+@', text, re.IGNORECASE):
        return False
    
    # 2. 告知・サイン関連のキーワードが含まれているかチェック
    for kw in ANNOUNCEMENT_KEYWORDS:
        if kw in text:
            return True
            
    return False

def send_email(subject, body):
    api_key = os.environ.get("RESEND_API_KEY")
    to_email = os.environ.get("NOTIFICATION_EMAIL")

    if not api_key or not to_email:
        print("Resendの設定（RESEND_API_KEY / NOTIFICATION_EMAIL）が不足しています。")
        return

    resend.api_key = api_key

    try:
        resend.Emails.send({
            "from": "Official Person Monitor <onboarding@resend.dev>",
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
                    
                    # URLからユーザーIDを抽出して除外チェック（大文字小文字を区別せず判定）
                    url_match = re.search(r'https?://[^/]+/([^/]+)/status', link)
                    if url_match:
                        author_id = url_match.group(1).lower()
                        if author_id in [u.lower() for u in EXCLUDE_USERS]:
                            continue

                    # 告知・サイン関連ワードが含まれていないポスト、およびリプライは除外
                    if not is_official_announcement(title):
                        continue

                    x_link = link
                    for inst in nitter_instances:
                        x_link = x_link.replace(inst, "https://x.com")
                    
                    post_id = extract_post_id(x_link)
                    
                    posts.append({
                        "id": post_id,
                        "link": x_link,
                        "text": f"【公式・告知ポスト】\n{title}\n\nURL: {x_link}\n{'-'*30}"
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

    notified_ids = load_notified_ids()
    print(f"過去に通知済みの件数: {len(notified_ids)}件")

    new_posts = []
    new_ids = []
    seen_in_this_run = set()

    for query in QUERIES:
        print(f"検索中: {query}")
        posts = fetch_tweets_for_query(query, nitter_instances)
        
        for post in posts:
            post_id = post["id"]
            if post_id not in notified_ids and post_id not in seen_in_this_run:
                seen_in_this_run.add(post_id)
                new_ids.append(post_id)
                new_posts.append(post["text"])

    print(f"新規取得ポスト件数: {len(new_posts)}件")

    if new_posts:
        body = "\n\n".join(new_posts)
        send_email("【X公式・告知通知】サイン・お知らせポストが見つかりました", body)
        save_notified_ids(new_ids)
    else:
        print("新しい未通知のポストは見つかりませんでした。")

if __name__ == "__main__":
    main()
