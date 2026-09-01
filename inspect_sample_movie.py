import json

SCHEDULE_FILE = "schedule.json"

with open(
    SCHEDULE_FILE,
    "r",
    encoding="utf-8"
) as f:
    schedule = json.load(f)

print("=== sampleMovieURL 確認 ===")

count = 0

for item in schedule:

    sample_movie = item.get("sample_movie")

    if not sample_movie:
        continue

    print("")
    print("タイトル:")
    print(item.get("title"))

    print("")
    print("content_id:")
    print(item.get("content_id"))

    print("")
    print("sample_movie:")
    print(
        json.dumps(
            sample_movie,
            ensure_ascii=False,
            indent=2
        )
    )

    print("")
    print("====================")

    count += 1

    # とりあえず3作品だけ確認
    if count >= 3:
        break

if count == 0:
    print("サンプル動画あり作品が見つかりませんでした。")
