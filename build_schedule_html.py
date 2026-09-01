import json
from datetime import datetime
from html import escape

SCHEDULE_FILE = "schedule.json"
OUTPUT_FILE = "schedule.html"

GENRE_NAMES = {
    "1083": "幼なじみ",
    "4111": "NTR",
    "4124": "マッサージ・リフレ",
    "4106": "騎乗位",
    "5067": "顔面騎乗",
}

with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
    schedule = json.load(f)

days = {}

for item in schedule:
    dt = datetime.fromisoformat(item["scheduled_at"])

    date_key = dt.strftime("%Y-%m-%d")
    time_text = dt.strftime("%H:%M:%S")

    if dt.hour < 12:
        slot = "朝"
    elif dt.hour < 21:
        slot = "夕"
    else:
        slot = "夜"

    days.setdefault(date_key, [])

    days[date_key].append({
        "slot": slot,
        "time": time_text,
        "title": item.get("title", ""),
        "genre_id": str(item.get("genre_id", "")),
        "status": item.get("status", ""),
        "affiliate_url": item.get("affiliate_url", ""),
        "image_url": item.get("image_url", ""),
    })

sections = []

for date_key in sorted(days.keys()):

    dt = datetime.strptime(date_key, "%Y-%m-%d")

    date_display = dt.strftime("%m/%d")

    cards = []

    for item in sorted(
        days[date_key],
        key=lambda x: x["time"]
    ):

        genre_name = GENRE_NAMES.get(
            item["genre_id"],
            item["genre_id"]
        )

        status = item["status"]

        status_class = (
            "posted"
            if status == "posted"
            else "pending"
        )

        image_html = ""

        if item["image_url"]:
            image_html = f"""
            <img
                src="{escape(item['image_url'])}"
                loading="lazy"
            >
            """

        link_html = ""

        if item["affiliate_url"]:
            link_html = f"""
            <a
                href="{escape(item['affiliate_url'])}"
                target="_blank"
                rel="noopener noreferrer"
            >
                FANZAで確認
            </a>
            """

        cards.append(
            f"""
            <div class="slot">

                <div class="slot-head">
                    <span class="slot-name">
                        {escape(item["slot"])}
                    </span>

                    <span class="time">
                        {escape(item["time"])}
                    </span>

                    <span class="status {status_class}">
                        {escape(status)}
                    </span>
                </div>

                {image_html}

                <div class="body">

                    <div class="genre">
                        {escape(genre_name)}
                    </div>

                    <div class="title">
                        {escape(item["title"])}
                    </div>

                    {link_html}

                </div>

            </div>
            """
        )

    sections.append(
        f"""
        <section class="day">

            <h2>
                {date_display}
            </h2>

            <div class="slots">
                {''.join(cards)}
            </div>

        </section>
        """
    )

html = f"""
<!doctype html>

<html lang="ja">

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>FANZA 投稿スケジュール</title>

<style>

body {{
    margin: 0;
    padding: 16px;
    background: #f4f4f4;
    color: #222;
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Helvetica Neue",
        Arial,
        sans-serif;
}}

h1 {{
    margin: 0 0 20px;
    font-size: 26px;
}}

.day {{
    margin-bottom: 26px;
}}

.day h2 {{
    font-size: 20px;
    margin: 0 0 10px;
}}

.slots {{
    display: grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(260px, 1fr)
        );
    gap: 12px;
}}

.slot {{
    background: white;
    border-radius: 14px;
    overflow: hidden;
    box-shadow:
        0 2px 8px rgba(0,0,0,0.08);
}}

.slot-head {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    background: #111;
    color: white;
}}

.slot-name {{
    font-weight: bold;
}}

.time {{
    font-variant-numeric: tabular-nums;
}}

.status {{
    margin-left: auto;
    font-size: 12px;
    padding: 3px 7px;
    border-radius: 999px;
}}

.pending {{
    background: #666;
}}

.posted {{
    background: #2d7;
    color: #111;
}}

.slot img {{
    width: 100%;
    display: block;
    aspect-ratio: 4 / 3;
    object-fit: cover;
}}

.body {{
    padding: 12px;
}}

.genre {{
    font-size: 13px;
    color: #777;
    margin-bottom: 6px;
}}

.title {{
    font-size: 15px;
    line-height: 1.45;
    margin-bottom: 12px;
}}

.body a {{
    display: block;
    text-align: center;
    text-decoration: none;
    background: #111;
    color: white;
    padding: 10px;
    border-radius: 10px;
    font-weight: bold;
}}

</style>

</head>

<body>

<h1>
FANZA 投稿スケジュール
</h1>

{''.join(sections)}

</body>

</html>
"""

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:
    f.write(html)

print(f"{OUTPUT_FILE} を作成しました。")
