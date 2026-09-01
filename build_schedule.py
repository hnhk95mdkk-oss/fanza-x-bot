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
def is_available_now(item):

    now = datetime.now(JST)

    date_text = (
        item.get("date")
        or item.get("release_date")
        or item.get("deliveryStartDate")
    )

    # 日付情報がない場合は、とりあえず残す
    if not date_text:
        return True

    date_text = str(date_text).strip()

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]

    for fmt in formats:

        try:
            release = datetime.strptime(
                date_text,
                fmt
            )

            release = release.replace(
                tzinfo=JST
            )

            return release <= now

        except ValueError:
            continue

    # 日付形式が分からない場合は除外せず残す
    return True

# ==================================================
# 除外ワード読み込み
# ==================================================

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

            # 空行
            if not word:
                continue

            # コメント
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
# FANZA API
# ==================================================

def fetch_genre_items(genre_id):

    params = {
        "api_id": API_ID,
        "affiliate_id": AFFILIATE_ID,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "genre_id": genre_id,

        # 除外ワードで減ることを想定して多めに取得
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

    result = data.get(
        "result",
        {}
    )

    return result.get(
        "items",
        []
    )


# ==================================================
# 除外ワード判定
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
# 商品データを候補化
# ==================================================

def make_candidate(
    item,
    genre_id
):

    content_id = item.get(
        "content_id"
    )

    title = item.get(
        "title",
        ""
    )

    affiliate_url = item.get(
        "affiliateURL"
    )

    image_url = (
        item
        .get("imageURL", {})
        .get("large")
    )

    sample_movie = item.get(
        "sampleMovieURL"
    )

    sample_images = (
        item
        .get("sampleImageURL", {})
        .get("sample_s", {})
        .get("image", [])
    )
  

    # --------------------------
    # 必須データ
    # --------------------------

    if not content_id:
        return None

    if not title:
        return None

    if not affiliate_url:
        return None

    if not image_url:
        return None

    # サンプル動画なしは除外
    if not sample_movie:
        return None


    # --------------------------
    # 除外ワード
    # --------------------------

    excluded_word = (
        find_excluded_word(
            title
        )
    )

    if excluded_word:

        print(
            "除外 "
            f"[{excluded_word}] "
            f"{title}"
        )

        return None


    # --------------------------
    # 候補
    # --------------------------

    return {

        "content_id":
            content_id,

        "genre_id":
            str(genre_id),

        "title":
            title,

        "affiliate_url":
            affiliate_url,

        "image_url":
            image_url,

        "sample_images":
            sample_images,

        "sample_movie":
            sample_movie,
    }


# ==================================================
# 各ジャンルから候補取得
# ==================================================

candidates = []

used_ids = set()


for genre_id in GENRE_IDS:

    print("")
    print("====================")
    print(
        "ジャンル:",
        genre_id
    )
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


        content_id = (
            candidate[
                "content_id"
            ]
        )


        # --------------------------
        # 他ジャンルですでに採用済み
        # --------------------------

        if content_id in used_ids:
            continue


        candidates.append(
            candidate
        )

        used_ids.add(
            content_id
        )

        genre_count += 1


        if (
            genre_count
            >= POSTS_PER_GENRE
        ):
            break


    print(
        "採用作品数:",
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


# ==================================================
# ジャンルごとに分類
# ==================================================

by_genre = {}


for item in candidates:

    genre = item[
        "genre_id"
    ]

    if genre not in by_genre:

        by_genre[
            genre
        ] = []

    by_genre[
        genre
    ].append(
        item
    )


# 同ジャンル内の順番もランダム
for genre in by_genre:

    random.shuffle(
        by_genre[
            genre
        ]
    )


# ==================================================
# ジャンルを分散
# ==================================================

genre_ids_available = list(
    by_genre.keys()
)

mixed_candidates = []

previous_genre = None


while (
    len(mixed_candidates)
    < TOTAL_POSTS
):

    available = [

        genre
        for genre
        in genre_ids_available

        if by_genre[
            genre
        ]

    ]


    if not available:
        break


    # 直前ジャンル以外を優先
    different_genres = [

        genre
        for genre
        in available

        if genre
        != previous_genre

    ]


    if different_genres:

        genre = random.choice(
            different_genres
        )

    else:

        genre = random.choice(
            available
        )


    item = by_genre[
        genre
    ].pop(0)


    mixed_candidates.append(
        item
    )


    previous_genre = genre


# ==================================================
# 投稿時間帯
# ==================================================

TIME_WINDOWS = [

    # 朝
    ((7, 30), (8, 30)),

    # 夕
    ((17, 30), (18, 30)),

    # 夜
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


# ==================================================
# 10日 × 1日3投稿
# ==================================================

now = datetime.now(
    JST
)

start_date = (
    now
    + timedelta(days=1)
).date()


schedule = []

index = 0


for day in range(10):

    target_date = (
        start_date
        + timedelta(
            days=day
        )
    )


    for window in TIME_WINDOWS:

        if (
            index
            >= len(
                mixed_candidates
            )
        ):
            break


        scheduled_at = (
            random_time_for_date(
                target_date,
                window
            )
        )


        item = (
            mixed_candidates[
                index
            ]
        )


        schedule.append({

            "scheduled_at":
                scheduled_at
                .isoformat(),

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


# 念のため時刻順
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
print(
    "=== 投稿予定 ==="
)


for number, item in enumerate(
    schedule,
    start=1
):

    print(
        number,
        item[
            "scheduled_at"
        ],
        "genre:",
        item[
            "genre_id"
        ],
        item[
            "title"
        ]
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
        "⚠️ 30件に"
        "届きませんでした。"
    )

    print(
        "除外ワード、画像、"
        "サンプル動画などの条件で"
        "候補が不足しています。"
    )
