import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

# --------------------------------
# ジャンルをなるべく均等に分散
# --------------------------------

by_genre = {}

for item in candidates:
    genre = item["genre_id"]
    by_genre.setdefault(genre, []).append(item)

# 各ジャンル内も少しランダム化
for genre in by_genre:
    random.shuffle(by_genre[genre])

genre_ids = list(by_genre.keys())

mixed_candidates = []

while len(mixed_candidates) < TOTAL_POSTS:

    # 毎周ジャンル順をシャッフル
    random.shuffle(genre_ids)

    added = False

    for genre in genre_ids:
        if by_genre[genre]:
            mixed_candidates.append(
                by_genre[genre].pop(0)
            )
            added = True

            if len(mixed_candidates) >= TOTAL_POSTS:
                break

    if not added:
        break


# --------------------------------
# 投稿時間帯
# --------------------------------

TIME_WINDOWS = [
    # 朝 07:30〜08:30
    ((7, 30), (8, 30)),

    # 夕 17:30〜18:30
    ((17, 30), (18, 30)),

    # 夜 22:30〜23:30
    ((22, 30), (23, 30)),
]


def random_time_for_date(date, window):

    (start_h, start_m), (end_h, end_m) = window

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
        (end - start).total_seconds()
    )

    random_seconds = random.randint(
        0,
        seconds_range
    )

    return start + timedelta(
        seconds=random_seconds
    )


# --------------------------------
# 10日 × 3投稿
# --------------------------------

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

            "status": "pending",
            "posted_at": None,

            **item,
        })

        index += 1


# 念のため時刻順に並べる
schedule.sort(
    key=lambda x: x["scheduled_at"]
)


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
