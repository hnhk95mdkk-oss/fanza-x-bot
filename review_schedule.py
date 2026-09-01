import json

with open("schedule.json", "r", encoding="utf-8") as f:
    schedule = json.load(f)

genre_names = {
    "1083": "幼なじみ",
    "4111": "NTR",
    "4124": "マッサージ・リフレ",
    "4106": "騎乗位",
    "5067": "顔面騎乗",
}

print("=== 投稿候補一覧 ===")

for i, item in enumerate(schedule, start=1):
    print("")
    print(f"{i}. {item.get('title')}")
    print("ジャンル:", genre_names.get(str(item.get("genre_id")), item.get("genre_id")))
    print("予定:", item.get("scheduled_at"))
    print("状態:", item.get("status"))
    print("作品URL:", item.get("affiliate_url"))
    print("画像:", item.get("image_url"))
    print("-" * 50)
