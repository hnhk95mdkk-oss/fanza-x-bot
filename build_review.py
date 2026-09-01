import os
import json
import random
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

JST = ZoneInfo("Asia/Tokyo")

EXCLUDE_FILE = "exclude_words.txt"


# =====================================
# 除外ワード読み込み
# =====================================

def load_exclude_words():

    if not os.path.exists(EXCLUDE_FILE):
        print("exclude_words.txt がありません。")
        return []

    words = []

    with open(
        EXCLUDE_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            word = line.strip()

            # 空行は無視
            if not word:
                continue

            # # で始まる行はコメント扱い
            if word.startswith("#"):
                continue

            words.append(word)

    return words


EXCLUDE_WORDS = load_exclude_words()

print("")
print("=== 除外ワード ===")

for word in EXCLUDE_WORDS:
    print("-", word)

print("==================")


# =====================================
# FANZA商品取得
# =====================================

def fetch_genre_items(genre_id):

    params = {
        "api_id": API_ID,
        "affiliate_id": AFFILIATE_ID,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "genre_id": genre_id,
        "hits": 100,
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


# =====================================
# 除外判定
# =====================================

def contains_excluded_word(text):

    if not text:
        return None

    text_lower = text.lower()

    for word in EXCLUDE_WORDS:

        if word.lower() in text_lower:
            return word

    return None


# =====================================
# 商品候補化
# =====================================

def make_candidate(item, genre_id):

    content_id = item.get("content_id")
    title = item.get("title", "")
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

    if not content_id:
        return None

    if not title:
        return None

    if not affiliate_url:
        return None

    if not image_url:
        return None

    if not sample_movie:
        return None

    # -----------------------------
    # 除外ワード判定
    # -----------------------------

    matched_word = contains_excluded_word(
        title
    )

    if matched_word:

        print(
            f"除外 [{matched_word}]: "
            f"{title}"
        )

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


# =====================================
# 各ジャンルから候補取得
# =====================================

candidates = []
used_ids = set()

for genre_id in GENRE_IDS:

    print("")
    print("====================")
    print("ジャンル:", genre_id)
    print("====================")

    items = fetch_genre_items(
        genre_id
    )

    genre_count = 0

    for item in items:

        candidate = make_candidate(
            item,
            genre_id
        )

        if candidate is None:
            continue

        content_id = candidate[
            "content_id"
        ]

        # 同じ作品の重複防止
        if content_id in used_ids:
            continue

        candidates.append(
            candidate
        )

        used_ids.add(
            content_id
        )

        genre_count += 1

        if genre_count >= POSTS_PER_GENRE:
            break

    print(
        f"採用作品数: "
        f"{genre_count}/"
        f"{POSTS_PER_GENRE}"
    )


print("")
print("====================")
print(
    "候補合計:",
    len(candidates)
)
print("====================")


# =====================================
# ジャンル分散
# =====================================

by_genre = {}

for item in candidates:

    genre = item["genre_id"]

    by_genre.setdefault(
        genre,
        []
    ).append(item)


for genre in by_genre:
    random.shuffle(
        by_genre[genre]
    )


genre_ids = list(
    by_genre.keys()
)

mixed_candidates = []


while len(
    mixed_candidates
) < TOTAL_POSTS:

    random.shuffle(
        genre_ids
    )

    added = False

    for genre in genre_ids:

        if by_genre[genre]:

            mixed_candidates.append(
                by_genre[genre].pop(0)
            )

            added = True

            if len(
                mixed_candidates
            ) >= TOTAL_POSTS:
                break

    if not added:
        break


# =====================================
# 投稿時間帯
# =====================================

TIME_WINDOWS = [

    # 朝
    ((7, 30), (8, 30)),

    # 夕
    ((17, 30), (18, 30)),

    # 夜
    ((22, 30), (23, 30)),
]


def random_time_for_date(
    date,
    window
):

    (start_h, start_m), (
        end_h,
        end_m
    ) = window

    start = datetime(
        date.year,
        date.month,
        date.day,
        start_h,
        start_m,
        0,
        tzinfo=JST,
    )

    end = datetime(
        date.year,
        date.month,
        date.day,
        end_h,
        end_m,
        59,
        tzinfo=JST,
    )

    seconds_range = int(
        (
            end - start
        ).total_seconds()
    )

    random_seconds = (
        random.randint(
            0,
            seconds_range
        )
    )

    return (
        start
        + timedelta(
            seconds=random_seconds
        )
    )


# =====================================
# 10日 × 3投稿
# =====================================

now = datetime.now(JST)

start_date = (
    now
    + timedelta(days=1)
).date()

schedule = []

index = 0


for day in range(10):

    target_date = (
        start_date
        + timedelta(days=day)
    )

    for window in TIME_WINDOWS:

        if index >= len(
            mixed_candidates
        ):
            break

        scheduled_at = (
            random_time_for_date(
                target_date,
                window
            )
        )

        item = (
            mixed_candidates[index]
        )

        schedule.append({
            "scheduled_at":
                scheduled_at.isoformat(),

            "status":
                "pending",

            "posted_at":
                None,

            **item,
        })

        index += 1


schedule.sort(
    key=lambda x:
        x["scheduled_at"]
)


# =====================================
# 保存
# =====================================

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
        "⚠️ 30作品に"
        "届きませんでした。"
    )

    print(
        "除外ワードや"
        "サンプル動画条件によって"
        "候補が不足しています。"
    )
