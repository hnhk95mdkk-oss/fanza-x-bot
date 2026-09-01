import os
import json
import random
from datetime import datetime
from zoneinfo import ZoneInfo

import tweepy

SCHEDULE_FILE = "schedule.json"
JST = ZoneInfo("Asia/Tokyo")


# -----------------------------
# X API
# -----------------------------

client = tweepy.Client(
    consumer_key=os.environ["X_API_KEY"],
    consumer_secret=os.environ["X_API_SECRET"],
    access_token=os.environ["X_ACCESS_TOKEN"],
    access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
)


# -----------------------------
# 投稿文を作る
# -----------------------------

def make_post_text(item):

    title = item["title"]
    affiliate_url = item["affiliate_url"]

    genre_id = str(item.get("genre_id", ""))

    genre_names = {
        "1083": "幼なじみ",
        "4111": "寝取り・寝取られ・NTR",
        "4124": "マッサージ・リフレ",
        "4106": "騎乗位",
        "5067": "顔面騎乗",
    }

    genre_name = genre_names.get(
        genre_id,
        "おすすめ作品"
    )

    intros = [
        f"今日の気になる一本👀\n{genre_name}からピックアップ。",
        f"新しく見つけた作品はこちら✨\n今回は{genre_name}。",
        f"本日のおすすめ🎬\n{genre_name}好きならチェック。",
        f"今日のFANZAピックアップ👀\nジャンルは{genre_name}。",
    ]

    intro = random.choice(intros)

    # Xの文字数に余裕を持たせる
    max_title_length = 80

    if len(title) > max_title_length:
        title = title[:max_title_length] + "…"

    text = (
        f"{intro}\n\n"
        f"{title}\n\n"
        f"▶ 作品はこちら\n"
        f"{affiliate_url}\n\n"
        f"#PR #FANZA"
    )

    return text


# -----------------------------
# schedule.json 読み込み
# -----------------------------

with open(
    SCHEDULE_FILE,
    "r",
    encoding="utf-8"
) as f:
    schedule = json.load(f)


now = datetime.now(JST)

print("現在時刻:", now.isoformat())


# -----------------------------
# 投稿対象を探す
# -----------------------------

due_items = []

for index, item in enumerate(schedule):

    if item.get("status") != "pending":
        continue

    scheduled_at = datetime.fromisoformat(
        item["scheduled_at"]
    )

    if scheduled_at <= now:
        due_items.append(
            (scheduled_at, index, item)
        )


if not due_items:
    print("現在投稿する作品はありません。")
    raise SystemExit(0)


# 最も古い予定を1件だけ投稿
due_items.sort(
    key=lambda x: x[0]
)

scheduled_at, index, item = due_items[0]


print("")
print("=== 投稿対象 ===")
print("予定:", scheduled_at.isoformat())
print("タイトル:", item["title"])
print("genre:", item.get("genre_id"))


# -----------------------------
# Xに投稿
# -----------------------------

post_text = make_post_text(item)

response = client.create_tweet(
    text=post_text
)

tweet_id = response.data["id"]

print("")
print("投稿成功")
print("Tweet ID:", tweet_id)


# -----------------------------
# schedule.json 更新
# -----------------------------

schedule[index]["status"] = "posted"
schedule[index]["posted_at"] = now.isoformat()
schedule[index]["tweet_id"] = str(tweet_id)


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
