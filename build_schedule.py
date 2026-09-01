import os
import json
import requests
from datetime import datetime, timedelta

API_URL = "https://api.dmm.com/affiliate/v3/ItemList"

api_id = os.environ["DMM_API_ID"].strip()
affiliate_id = os.environ["DMM_AFFILIATE_ID"].strip()
genre_id = os.environ.get("DMM_GENRE_ID", "").strip()

params = {
    "api_id": api_id,
    "affiliate_id": affiliate_id,
    "site": "FANZA",
    "service": "digital",
    "floor": "videoa",
    "hits": 50,
    "sort": "date",
    "output": "json",
}

if genre_id:
    params["genre_id"] = genre_id

response = requests.get(API_URL, params=params, timeout=30)

print("HTTP status:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise SystemExit("FANZA API request failed")

data = response.json()
items = data.get("result", {}).get("items", [])

print("取得件数:", len(items))

candidates = []

for item in items:
    title = item.get("title")
    content_id = item.get("content_id")
    affiliate_url = item.get("affiliateURL")
    image_url = item.get("imageURL", {}).get("large")

    sample_images = (
        item.get("sampleImageURL", {})
        .get("sample_s", {})
        .get("image", [])
    )

    sample_movie = item.get("sampleMovieURL")

    if not title or not affiliate_url:
        continue

    candidates.append({
        "content_id": content_id,
        "title": title,
        "affiliate_url": affiliate_url,
        "image_url": image_url,
        "sample_images": sample_images,
        "sample_movie": sample_movie,
    })

print("候補件数:", len(candidates))

# 最大30件
candidates = candidates[:30]

start_date = datetime.now() + timedelta(days=1)

times = [
    (8, 0),
    (18, 0),
    (23, 0),
]

schedule = []

index = 0

for day in range(10):
    for hour, minute in times:
        if index >= len(candidates):
            break

        post_time = (
            start_date
            + timedelta(days=day)
        ).replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        )

        item = candidates[index]

        schedule.append({
            "scheduled_at": post_time.isoformat(),
            "status": "pending",
            **item,
        })

        index += 1

with open("schedule.json", "w", encoding="utf-8") as f:
    json.dump(
        schedule,
        f,
        ensure_ascii=False,
        indent=2
    )

print("")
print("=== 投稿予定 ===")

for item in schedule:
    print(
        item["scheduled_at"],
        item["title"]
    )

print("")
print("schedule.json を作成しました")
