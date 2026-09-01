import os
import json
import random
import math
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ==================================================
# 基本設定
# ==================================================

API_URL = "https://api.dmm.com/affiliate/v3/ItemList"

API_ID = os.environ["DMM_API_ID"].strip()
AFFILIATE_ID = os.environ["DMM_AFFILIATE_ID"].strip()

GENRE_IDS = [
    x.strip()
    for x in os.environ["DMM_GENRE_IDS"].split(",")
    if x.strip()
]

SCHEDULE_FILE = "schedule.json"
POSTED_IDS_FILE = "posted_ids.json"
EXCLUDE_FILE = "exclude_words.txt"

JST = ZoneInfo("Asia/Tokyo")

# pending がこの件数以下になったら補充
REFILL_THRESHOLD = 10

# 補充後にこの件数を目指す
TARGET_STOCK = 30

# FANZA API
HITS_PER_PAGE = 100
MAX_PAGES_PER_GENRE = 10


# 投稿時間帯
TIME_WINDOWS = [
    # 朝 07:30〜08:30
    ((7, 30), (8, 30)),

    # 夕 17:30〜18:30
    ((17, 30), (18, 30)),

    # 夜 22:30〜23:30
    ((22, 30), (23, 30)),
]


# ==================================================
# JSON読み込み
# ==================================================

def load_json_file(path, default):

    if not os.path.exists(path):
        return default

    try:
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception as e:
        print(
            f"⚠️ {path} の読み込み失敗:",
            str(e)
        )
        return default


# ==================================================
# 現在のスケジュール
# ==================================================

current_schedule = load_json_file(
    SCHEDULE_FILE,
    []
)

# pendingだけ残す
pending_items = [
    item
    for item in current_schedule
    if item.get("status") == "pending"
]


print("")
print("==========================")
print("現在のpending:", len(pending_items))
print("==========================")


# ==================================================
# 在庫が十分なら終了
# ==================================================

if len(pending_items) > REFILL_THRESHOLD:

    print("")
    print(
        f"✅ まだ {len(pending_items)}件 "
        "残っています。"
    )

    print(
        f"{REFILL_THRESHOLD}件以下に"
        "なるまで補充しません。"
    )

    raise SystemExit(0)


# ==================================================
# 必要な補充件数
# ==================================================

needed = (
    TARGET_STOCK
    - len(pending_items)
)


if needed <= 0:

    print(
        "在庫は十分あります。"
    )

    raise SystemExit(0)


print("")
print(
    f"📦 {needed}件を"
    "新しく補充します。"
)


# ==================================================
# 投稿済みID読み込み
# ==================================================

posted_ids_list = load_json_file(
    POSTED_IDS_FILE,
    []
)

posted_ids = set(
    str(x)
    for x in posted_ids_list
)


print(
    "過去投稿済みID:",
    len(posted_ids)
)


# ==================================================
# 現在予約中のID
# ==================================================

scheduled_ids = set()

for item in pending_items:

    content_id = item.get(
        "content_id"
    )

    if content_id:
        scheduled_ids.add(
            str(content_id)
        )


print(
    "現在予約中ID:",
    len(scheduled_ids)
)


# ==================================================
# 除外ワード
# ==================================================

def load_exclude_words():

    if not os.path.exists(
        EXCLUDE_FILE
    ):
        return []

    words = []

    with open(
        EXCLUDE_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            word = line.strip()

            if not word:
                continue

            if word.startswith("#"):
                continue

            words.append(word)

    return words


EXCLUDE_WORDS = (
    load_exclude_words()
)


print("")
print("=== 除外ワード ===")

if EXCLUDE_WORDS:

    for word in EXCLUDE_WORDS:
        print("-", word)

else:
    print("なし")

print("==================")


# ==================================================
# 除外ワード判定
# ==================================================

def find_excluded_word(text):

    if not text:
        return None

    text_lower = text.lower()

    for word in EXCLUDE_WORDS:

        if (
            word.lower()
            in text_lower
        ):
            return word

    return None


# ==================================================
# 配信開始日
# ==================================================

def parse_release_date(item):

    date_text = item.get("date")

    if not date_text:
        return None

    date_text = str(
        date_text
    ).strip()

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
    ]

    for fmt in formats:

        try:

            result = (
                datetime.strptime(
                    date_text,
                    fmt
                )
            )

            return result.replace(
                tzinfo=JST
            )

        except ValueError:
            continue

    return None


# ==================================================
# 今すぐ視聴可能か
# ==================================================

def is_available_now(item):

    release_date = (
        parse_release_date(item)
    )

    # 日付不明は今回は採用しない
    if release_date is None:
        return False

    return (
        release_date
        <= datetime.now(JST)
    )


# ==================================================
# FANZA API
# ==================================================

def fetch_genre_items(
    genre_id,
    offset
):

    params = {
        "api_id":
            API_ID,

        "affiliate_id":
            AFFILIATE_ID,

        "site":
            "FANZA",

        "service":
            "digital",

        "floor":
            "videoa",

        # ジャンル
        "article":
            "genre",

        "article_id":
            genre_id,

        "hits":
            HITS_PER_PAGE,

        "offset":
            offset,

        "sort":
            "date",

        "output":
            "json",
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


    if (
        response.status_code
        != 200
    ):

        print(
            response.text
        )

        return []


    data = response.json()


    return (
        data
        .get("result", {})
        .get("items", [])
    )


# ==================================================
# 商品候補化
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

    release_date = (
        parse_release_date(item)
    )


    # ------------------------------
    # 基本項目
    # ------------------------------

    if not content_id:
        return None

    content_id = str(
        content_id
    )

    if not title:
        return None

    if not affiliate_url:
        return None

    if not image_url:
        return None

    # サンプル動画必須
    if not sample_movie:
        return None


    # ------------------------------
    # 予約・未配信除外
    # ------------------------------

    if not is_available_now(item):

        print(
            "予約・未配信 除外:",
            item.get("date"),
            title
        )

        return None


    # ------------------------------
    # 過去投稿済み
    # ------------------------------

    if content_id in posted_ids:

        print(
            "過去投稿済み 除外:",
            title
        )

        return None


    # ------------------------------
    # 現在scheduleにある
    # ------------------------------

    if content_id in scheduled_ids:

        print(
            "予約済み 除外:",
            title
        )

        return None


    # ------------------------------
    # 除外ワード
    # ------------------------------

    excluded_word = (
        find_excluded_word(
            title
        )
    )


    if excluded_word:

        print(
            f"除外 [{excluded_word}] "
            f"{title}"
        )

        return None


    # ------------------------------
    # 採用可能
    # ------------------------------

    return {

        "content_id":
            content_id,

        "genre_id":
            str(genre_id),

        "title":
            title,

        "release_date":
            (
                release_date.isoformat()
                if release_date
                else None
            ),

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
# 新規候補収集
# ==================================================

new_candidates = []

new_candidate_ids = set()


# 必要本数をジャンル数で均等配分
per_genre_target = math.ceil(
    needed
    / len(GENRE_IDS)
)


print("")
print(
    "1ジャンルあたり目安:",
    per_genre_target
)


for genre_id in GENRE_IDS:

    print("")
    print("========================")
    print("ジャンル:", genre_id)
    print("========================")

    genre_candidates = []


    for page in range(
        MAX_PAGES_PER_GENRE
    ):

        if (
            len(genre_candidates)
            >= per_genre_target
        ):
            break


        offset = (
            page
            * HITS_PER_PAGE
            + 1
        )


        items = fetch_genre_items(
            genre_id,
            offset
        )


        if not items:
            break


        for item in items:

            candidate = (
                make_candidate(
                    item,
                    genre_id
                )
            )


            if candidate is None:
                continue


            content_id = (
                candidate[
                    "content_id"
                ]
            )


            # 今回の補充内で重複
            if (
                content_id
                in new_candidate_ids
            ):
                continue


            genre_candidates.append(
                candidate
            )

            new_candidates.append(
                candidate
            )

            new_candidate_ids.add(
                content_id
            )

            # 以降の別ジャンル検索でも除外
            scheduled_ids.add(
                content_id
            )


            print(
                "✅ 新規採用:",
                candidate[
                    "release_date"
                ],
                candidate[
                    "title"
                ]
            )


            if (
                len(genre_candidates)
                >= per_genre_target
            ):
                break


    print(
        "このジャンル:",
        len(genre_candidates),
        "件"
    )


# ==================================================
# 必要数を超えたら調整
# ==================================================

random.shuffle(
    new_candidates
)

new_candidates = (
    new_candidates[:needed]
)


print("")
print(
    "新規候補合計:",
    len(new_candidates)
)


# ==================================================
# ジャンル分散
# ==================================================

by_genre = {}


for item in new_candidates:

    genre = item[
        "genre_id"
    ]

    by_genre.setdefault(
        genre,
        []
    ).append(
        item
    )


for genre in by_genre:

    random.shuffle(
        by_genre[
            genre
        ]
    )


mixed_candidates = []

previous_genre = None


while (
    len(mixed_candidates)
    < len(new_candidates)
):

    available = [
        genre
        for genre, items
        in by_genre.items()
        if items
    ]


    if not available:
        break


    different = [
        genre
        for genre in available
        if genre != previous_genre
    ]


    if different:

        selected_genre = (
            random.choice(
                different
            )
        )

    else:

        selected_genre = (
            random.choice(
                available
            )
        )


    item = by_genre[
        selected_genre
    ].pop(0)


    mixed_candidates.append(
        item
    )


    previous_genre = (
        selected_genre
    )


# ==================================================
# ランダム投稿時刻
# ==================================================

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


    seconds = random.randint(
        0,
        seconds_range
    )


    return (
        start
        + timedelta(
            seconds=seconds
        )
    )


# ==================================================
# 新規予約の開始日
# ==================================================

if pending_items:

    last_scheduled = max(
        datetime.fromisoformat(
            item["scheduled_at"]
        )
        for item in pending_items
    )

    # 現在の最後の予約の翌日から
    start_date = (
        last_scheduled
        + timedelta(days=1)
    ).date()

else:

    # ストック0なら明日から
    start_date = (
        datetime.now(JST)
        + timedelta(days=1)
    ).date()


print("")
print(
    "新規予約開始日:",
    start_date
)


# ==================================================
# 新規スケジュール作成
# ==================================================

new_schedule = []

index = 0
day = 0


while (
    index
    < len(mixed_candidates)
):

    target_date = (
        start_date
        + timedelta(days=day)
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


        new_schedule.append({

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


    day += 1


# ==================================================
# 既存pending + 新規を結合
# ==================================================

final_schedule = (
    pending_items
    + new_schedule
)


final_schedule.sort(
    key=lambda x:
        x["scheduled_at"]
)


# ==================================================
# schedule.json保存
# ==================================================

with open(
    SCHEDULE_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        final_schedule,
        f,
        ensure_ascii=False,
        indent=2
    )


# ==================================================
# 結果
# ==================================================

print("")
print("==========================")
print("📦 補充完了")
print("==========================")

print(
    "補充前:",
    len(pending_items)
)

print(
    "追加:",
    len(new_schedule)
)

print(
    "補充後:",
    len(final_schedule)
)


print("")
print("=== 新しく追加した予定 ===")


for number, item in enumerate(
    new_schedule,
    start=1
):

    print(
        number,
        item["scheduled_at"],
        "genre:",
        item["genre_id"],
        item["title"]
    )


if (
    len(final_schedule)
    < TARGET_STOCK
):

    print("")
    print(
        "⚠️ 30件まで"
        "補充できませんでした。"
    )

    print(
        "条件に合う新規作品が"
        "不足しています。"
    )
