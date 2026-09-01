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

HITS_PER_PAGE = 100
MAX_PAGES_PER_GENRE = 10

JST = ZoneInfo("Asia/Tokyo")

EXCLUDE_FILE = "exclude_words.txt"


# ==================================================
# 除外ワード読み込み
# ==================================================

def load_exclude_words():
    if not os.path.exists(EXCLUDE_FILE):
        print("exclude_words.txt がありません。")
        return []

    words = []

    with open(EXCLUDE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            word = line.strip()

            if not word:
                continue

            if word.startswith("#"):
                continue

            words.append(word)

    return words


EXCLUDE_WORDS = load_exclude_words()

print("")
print("=== 除外ワード ===")

if EXCLUDE_WORDS:
    for word in EXCLUDE_WORDS:
        print("-", word)
else:
    print("なし")

print("==================")


# ==================================================
# 日付判定
# ==================================================

def parse_release_date(item):
    date_text = item.get("date")

    if not date_text:
        return None

    date_text = str(date_text).strip()

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_text, fmt)
            return dt.replace(tzinfo=JST)
        except ValueError:
            continue

    return None


def is_available_now(item):
    release_date = parse_release_date(item)

    if release_date is None:
        # 判定不能なものは今回は採用しない
        return False

    now = datetime.now(JST)

    return release_date <= now


# ==================================================
# FANZA API
# ==================================================

def fetch_genre_items(genre_id, offset):
    params = {
        "api_id": API_ID,
        "affiliate_id": AFFILIATE_ID,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",

        # ジャンル指定
        "article": "genre",
        "article_id": genre_id,

        "hits": HITS_PER_PAGE,
        "offset": offset,
        "sort": "date",
        "output": "json",
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=30
    )

    print(
        f"genre={genre_id} "
        f"offset={offset} "
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


# ==================================================
# 除外ワード
# ==================================================

def find_excluded_word(text):
    if not text:
        return None

    text_lower = text.lower()

    for word in EXCLUDE_WORDS:
        if word.lower() in text_lower:
            return word

    return None


# ==================================================
# 商品候補化
# ==================================================

def make_candidate(item, genre_id):
    content_id = item.get("content_id")
    title = item.get("title", "")
    affiliate_url = item.get("affiliateURL")

    image_url = (
        item
        .get("imageURL", {})
        .get("large")
    )

    sample_movie = item.get("sampleMovieURL")

    sample_images = (
        item
        .get("sampleImageURL", {})
        .get("sample_s", {})
        .get("image", [])
    )

    release_date = parse_release_date(item)

    # -----------------------------
    # 予約・未来日作品を除外
    # -----------------------------

    if not is_available_now(item):
        print(
            "予約・未配信 除外:",
            item.get("date"),
            title
        )
        return None

    # -----------------------------
    # 必須条件
    # -----------------------------

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
    # 除外ワード
    # -----------------------------

    excluded_word = find_excluded_word(title)

    if excluded_word:
        print(
            f"除外 [{excluded_word}] "
            f"{title}"
        )
        return None

    return {
        "content_id": content_id,
        "genre_id": str(genre_id),
        "title": title,
        "release_date": (
            release_date.isoformat()
            if release_date
            else None
        ),
        "affiliate_url": affiliate_url,
        "image_url": image_url,
        "sample_images": sample_images,
        "sample_movie": sample_movie,
    }


# ==================================================
# 各ジャンルから6本確保
# ==================================================

candidates = []
used_ids = set()

for genre_id in GENRE_IDS:

    print("")
    print("========================")
    print("ジャンル:", genre_id)
    print("========================")

    genre_candidates = []

    for page in range(MAX_PAGES_PER_GENRE):

        if len(genre_candidates) >= POSTS_PER_GENRE:
            break

        offset = (
            page * HITS_PER_PAGE
        ) + 1

        print(
            f"ページ {page + 1} "
            f"(offset={offset})"
        )

        items = fetch_genre_items(
            genre_id,
            offset
        )

        if not items:
            print("商品がなくなりました。")
            break

        for item in items:

            candidate = make_candidate(
                item,
                genre_id
            )

            if candidate is None:
                continue

            content_id = candidate["content_id"]

            if content_id in used_ids:
                continue

            genre_candidates.append(candidate)
            used_ids.add(content_id)

            print(
                "✅ 採用:",
                candidate["release_date"],
                candidate["title"]
            )

            if len(genre_candidates) >= POSTS_PER_GENRE:
                break

    print(
        "ジャンル採用:",
        len(genre_candidates),
        "/",
        POSTS_PER_GENRE
    )

    candidates.extend(
        genre_candidates
    )


print("")
print("========================")
print(
    "候補合計:",
    len(candidates)
)
print("========================")


# ==================================================
# ジャンル分散
# ==================================================

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


mixed_candidates = []
previous_genre = None

while len(mixed_candidates) < TOTAL_POSTS:

    available = [
        genre
        for genre, items
        in by_genre.items()
        if items
    ]

    if not available:
        break

    different_genres = [
        genre
        for genre in available
        if genre != previous_genre
    ]

    if different_genres:
        selected_genre = random.choice(
            different_genres
        )
    else:
        selected_genre = random.choice(
            available
        )

    item = by_genre[
        selected_genre
    ].pop(0)

    mixed_candidates.append(item)

    previous_genre = selected_genre


# ==================================================
# 投稿時間帯
# ==================================================

TIME_WINDOWS = [
    ((7, 30), (8, 30)),
    ((17, 30), (18, 30)),
    ((22, 30), (23, 30)),
]


def random_time_for_date(
    target_date,
    window
):

    (
        start_hour,
        start_minute
    ), (
        end_hour,
        end_minute
    ) = window

    start = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        start_hour,
        start_minute,
        0,
        tzinfo=JST,
    )

    end = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        end_hour,
        end_minute,
        59,
        tzinfo=JST,
    )

    seconds_range = int(
        (end - start).total_seconds()
    )

    random_seconds = random.randint(
        0,
        seconds_range
    )

    return start + timedelta(
        seconds=random_seconds
    )


# ==================================================
# 10日 × 1日3回
# ==================================================

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

    for window in TIME_WINDOWS:

        if index >= len(mixed_candidates):
            break

        scheduled_at = random_time_for_date(
            target_date,
            window
        )

        item = mixed_candidates[index]

        schedule.append({
            "scheduled_at":
                scheduled_at.isoformat(),

            "status":
                "pending",

            "posted_at":
                None,

            "tweet_id":
                None,

            "video_attached":
                False,

            **item,
        })

        index += 1


schedule.sort(
    key=lambda x:
        x["scheduled_at"]
)


# ==================================================
# schedule.json 保存
# ==================================================

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


# ==================================================
# ログ
# ==================================================

print("")
print("=== 投稿予定 ===")

for number, item in enumerate(
    schedule,
    start=1
):

    print(
        number,
        item["scheduled_at"],
        "配信:",
        item["release_date"],
        "genre:",
        item["genre_id"],
        item["title"]
    )


print("")
print(
    "schedule.json に",
    len(schedule),
    "件保存しました。"
)


if len(schedule) < TOTAL_POSTS:

    print("")
    print(
        "⚠️ 30件に届きませんでした。"
    )

    print(
        "予約除外・除外ワード・"
        "画像・サンプル動画条件で"
        "候補が不足しています。"
    )
