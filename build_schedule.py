import os
import json
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

API_URL = "https://api.dmm.com/affiliate/v3/ItemList"

API_ID = os.environ["DMM_API_ID"].strip()
AFFILIATE_ID = os.environ["DMM_AFFILIATE_ID"].strip()

GENRE_IDS = [
    x.strip()
    for x in os.environ["DMM_GENRE_IDS"].split(",")
    if x.strip()
]

POSTS_PER_GENRE = 6
TOTAL_POSTS = 30

# 1日3回
POST_TIMES = [
    (8, 0),
    (18, 0),
    (23, 0),
]

JST = ZoneInfo("Asia/Tokyo")


def fetch_genre_items(genre_id):
    params = {
        "api_id": API_ID,
        "affiliate_id": AFFILIATE_ID,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "genre_id": genre_id,
        "hits": 50,
        "sort": "date",
        "output": "json",
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=30
    )

    print(
        f"genre_id={genre_id} "
        f"HTTP={response.status_code}"
    )

    if response.status_code != 200:
        print(response.text)
        return []

    data = response.json()

    return (
        data
        .get("result", {})
        .get("items", [])
    )


def make_candidate(item, genre_id):
    content_id = item.get("content_id")
    title = item.get("title")
    affiliate_url = item.get("affiliateURL")

    image_url = (
        item.get("imageURL", {})
        .get("large")
    )

    sample_movie = item.get("sampleMovieURL")

    sample_images = (
        item.get("sampleImageURL", {})
        .get("sample_s", {})
        .get("image", [])
    )

    # 投稿に最低限必要
    if not content_id:
        return None

    if not title:
        return None

    if not affiliate_url:
        return None

    if not image_url:
        return None

    # サンプル動画がある作品だけ採用
    if not sample_movie:
        return None

    return {
        "content_id": content_id,
        "genre_id": genre_id,
        "title": title,
        "affiliate_url": affiliate_url,
        "image_url": image_url,
        "sample_images": sample_images,
        "sample_movie": sample_movie,
    }


candidates = []
used_ids = set()

for genre_id in GENRE_IDS:

    print("")
    print("====================")
    print("ジャンル:", genre_id)
    print("====================")

    items = fetch_genre_items(genre_id)

    genre_count = 0

    for item in items:

        candidate = make_candidate(
            item,
            genre_id
        )

        if candidate is None:
            continue

        content_id = candidate["content_id"]

        # 同一作品の重複防止
        if content_id in used_ids:
            continue

        candidates.append(candidate)
        used_ids.add(content_id)

        genre_count += 1

        if genre_count >= POSTS_PER_GENRE:
            break

    print(
        f"採用作品数: {genre_count}/"
        f"{POSTS_PER_GENRE}"
    )


print("")
print("====================")
print("候補合計:", len(candidates))
print("====================")


# 30件まで
candidates = candidates[:TOTAL_POSTS]


# 明日から開始
now = datetime.now(JST)

start_date = (
    now + timedelta(days=1)
).date()


schedule = []

index = 0

for day in range(10):

    target_date = (
        start_date
        + timedelta(days=day)
    )

    for hour, minute in POST_TIMES:

        if index >= len(candidates):
            break

        scheduled_at = datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            hour,
            minute,
            tzinfo=JST,
        )

        item = candidates[index]

        schedule.append({
            "scheduled_at": scheduled_at.isoformat(),
            "status": "pending",
            "posted_at": None,
            **item,
        })

        index += 1


with open(
    "schedule.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        schedule,
        f,
        ensure_ascii=False,
        indent=2
    )


print("")
print("=== 投稿予定 ===")

for n, item in enumerate(
    schedule,
    start=1
):
    print(
        n,
        item["scheduled_at"],
        "genre:",
        item["genre_id"],
        item["title"]
    )


print("")
print(
    f"schedule.json に "
    f"{len(schedule)}件保存しました。"
)

if len(schedule) < TOTAL_POSTS:
    print("")
    print(
        "⚠️ 30作品に届きませんでした。"
    )
    print(
        "サンプル動画・画像あり作品が"
        "不足しているジャンルがあります。"
    )
