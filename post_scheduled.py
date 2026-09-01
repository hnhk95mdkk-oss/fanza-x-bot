import os
import json
import random
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

import requests
import tweepy


SCHEDULE_FILE = "schedule.json"
JST = ZoneInfo("Asia/Tokyo")


# ==================================================
# X 認証
# ==================================================

API_KEY = os.environ["X_API_KEY"]
API_SECRET = os.environ["X_API_SECRET"]
ACCESS_TOKEN = os.environ["X_ACCESS_TOKEN"]
ACCESS_TOKEN_SECRET = os.environ["X_ACCESS_TOKEN_SECRET"]


# v2 投稿用
client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET,
)


# Media Upload用 OAuth 1.0a
auth = tweepy.OAuth1UserHandler(
    API_KEY,
    API_SECRET,
    ACCESS_TOKEN,
    ACCESS_TOKEN_SECRET,
)

api = tweepy.API(auth)


# ==================================================
# ジャンル名
# ==================================================

GENRE_NAMES = {
    "1083": "幼なじみ",
    "4111": "寝取り・寝取られ・NTR",
    "4124": "マッサージ・リフレ",
    "4106": "騎乗位",
    "5067": "顔面騎乗",
}


# ==================================================
# 投稿文
# ==================================================

def make_post_text(item):

    title = item.get("title", "")
    affiliate_url = item.get("affiliate_url", "")

    genre_id = str(item.get("genre_id", ""))

    genre_name = GENRE_NAMES.get(
        genre_id,
        "おすすめ作品"
    )

    intros = [
        f"今日の気になる一本👀\n{genre_name}からピックアップ。",
        f"本日のFANZAピックアップ🎬\n今回は{genre_name}。",
        f"{genre_name}好きならチェック👀",
        f"今日見つけた一本✨\nジャンルは{genre_name}。",
        f"こんな一本はいかが？👀\n{genre_name}からセレクト。",
    ]

    intro = random.choice(intros)

    # 長すぎるタイトルをカット
    if len(title) > 80:
        title = title[:80] + "…"

    return (
    f"【PR】\n"
    f"{intro}\n\n"
    f"{title}\n\n"
    f"▶ 作品はこちら\n"
    f"{affiliate_url}\n\n"
    f"#FANZA")


# ==================================================
# sampleMovieURL から動画URLを探す
# ==================================================

def find_video_urls(value):

    urls = []

    if isinstance(value, str):

        if value.startswith(
            ("http://", "https://")
        ):
            urls.append(value)

    elif isinstance(value, dict):

        for child in value.values():
            urls.extend(
                find_video_urls(child)
            )

    elif isinstance(value, list):

        for child in value:
            urls.extend(
                find_video_urls(child)
            )

    return urls


def choose_video_url(sample_movie):

    urls = find_video_urls(sample_movie)

    if not urls:
        return None

    # mp4を最優先
    mp4_urls = [
        url for url in urls
        if ".mp4" in url.lower()
    ]

    if mp4_urls:
        # 後ろ側に高画質URLがある場合が多いので
        # 最後のものを使用
        return mp4_urls[-1]

    # MP4以外は今回は無理に加工しない
    return None


# ==================================================
# FANZAサンプル動画を取得
# ==================================================

def download_video(url):

    print("サンプル動画を取得します")

    response = requests.get(
        url,
        timeout=60,
        stream=True,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
    )

    response.raise_for_status()

    content_type = (
        response.headers
        .get("Content-Type", "")
        .lower()
    )

    print(
        "Content-Type:",
        content_type
    )

    # ファイル名は一時ファイル
    temp = tempfile.NamedTemporaryFile(
        suffix=".mp4",
        delete=False
    )

    total = 0

    with temp as f:

        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):

            if not chunk:
                continue

            f.write(chunk)

            total += len(chunk)

    print(
        "動画サイズ:",
        round(total / 1024 / 1024, 2),
        "MB"
    )

    return temp.name


# ==================================================
# Xへ動画アップロード
# ==================================================

def upload_video(filepath):

    print("Xへ動画をアップロードします")

    media = api.media_upload(
        filename=filepath,
        media_category="tweet_video",
        chunked=True,
    )

    print(
        "Media ID:",
        media.media_id_string
    )

    return media.media_id_string


# ==================================================
# schedule.json
# ==================================================

with open(
    SCHEDULE_FILE,
    "r",
    encoding="utf-8"
) as f:

    schedule = json.load(f)


now = datetime.now(JST)

print(
    "現在時刻:",
    now.isoformat()
)


# ==================================================
# 投稿対象
# ==================================================

due_items = []

for index, item in enumerate(schedule):

    if item.get("status") != "pending":
        continue

    scheduled_at = datetime.fromisoformat(
        item["scheduled_at"]
    )

    if scheduled_at <= now:

        due_items.append(
            (
                scheduled_at,
                index,
                item
            )
        )


if not due_items:

    print(
        "現在投稿する作品はありません。"
    )

    raise SystemExit(0)


# 最古の1件
due_items.sort(
    key=lambda x: x[0]
)

scheduled_at, index, item = (
    due_items[0]
)


print("")
print("=== 投稿対象 ===")
print(
    "予定:",
    scheduled_at.isoformat()
)
print(
    "タイトル:",
    item.get("title")
)
print(
    "genre:",
    item.get("genre_id")
)


# ==================================================
# 動画URL取得
# ==================================================

sample_movie = item.get(
    "sample_movie"
)
print("")
print("=== SAMPLE MOVIE DEBUG ===")
print(
    json.dumps(
        sample_movie,
        ensure_ascii=False,
        indent=2
    )
)
print("==========================")

video_url = choose_video_url(
    sample_movie
)

post_text = make_post_text(item)

media_id = None
video_path = None


# ==================================================
# 動画があれば取得・アップロード
# ==================================================

if video_url:

    print("")
    print(
        "サンプル動画URLを検出しました。"
    )

    try:

        video_path = download_video(
            video_url
        )

        media_id = upload_video(
            video_path
        )

    except Exception as e:

        print("")
        print(
            "⚠️ 動画処理に失敗しました。"
        )

        print(
            type(e).__name__,
            str(e)
        )

        print(
            "今回は動画なしで投稿します。"
        )

else:

    print("")
    print(
        "MP4サンプル動画がありません。"
    )

    print(
        "動画なしで投稿します。"
    )


# ==================================================
# X投稿
# ==================================================

if media_id:

    response = client.create_tweet(
        text=post_text,
        media_ids=[media_id],
    )

else:

    response = client.create_tweet(
        text=post_text
    )


tweet_id = response.data["id"]


print("")
print("✅ 投稿成功")
print(
    "Tweet ID:",
    tweet_id
)


# ==================================================
# schedule更新
# ==================================================

schedule[index]["status"] = "posted"

schedule[index]["posted_at"] = (
    now.isoformat()
)

schedule[index]["tweet_id"] = (
    str(tweet_id)
)
# ==================================================
# 投稿済み作品IDを保存
# ==================================================

POSTED_IDS_FILE = "posted_ids.json"

if os.path.exists(POSTED_IDS_FILE):

    with open(
        POSTED_IDS_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        posted_ids = json.load(f)

else:
    posted_ids = []


content_id = item.get("content_id")

if (
    content_id
    and content_id not in posted_ids
):
    posted_ids.append(content_id)


with open(
    POSTED_IDS_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        posted_ids,
        f,
        ensure_ascii=False,
        indent=2
    )


print(
    "posted_ids.json に"
    "投稿済み作品を記録しました。"
)
schedule[index][
    "video_attached"
] = bool(media_id)


with open(
    SCHEDULE_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        schedule,
        f,
        ensure_ascii=False,
        indent=2
    )


print(
    "schedule.json を"
    " posted に更新しました。"
)


# ==================================================
# 一時ファイル削除
# ==================================================

if video_path:

    try:
        os.remove(video_path)

    except OSError:
        pass
