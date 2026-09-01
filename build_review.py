import json
from html import escape

SCHEDULE_FILE = "schedule.json"
OUTPUT_FILE = "review.html"

GENRE_NAMES = {
    "1083": "幼なじみ",
    "4111": "NTR",
    "4124": "マッサージ・リフレ",
    "4106": "騎乗位",
    "5067": "顔面騎乗",
}

with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
    schedule = json.load(f)

cards = []

for i, item in enumerate(schedule, start=1):

    title = escape(item.get("title", ""))
    genre_id = str(item.get("genre_id", ""))
    genre_name = escape(
        GENRE_NAMES.get(genre_id, genre_id)
    )

    scheduled_at = escape(
        item.get("scheduled_at", "")
    )

    status = escape(
        item.get("status", "")
    )

    affiliate_url = item.get(
        "affiliate_url", ""
    )

    image_url = item.get(
        "image_url", ""
    )

    image_html = ""

    if image_url:
        image_html = f"""
        <img
            src="{escape(image_url)}"
            alt="{title}"
            loading="lazy"
        >
        """

    link_html = ""

    if affiliate_url:
        link_html = f"""
        <a
            class="button"
            href="{escape(affiliate_url)}"
            target="_blank"
            rel="noopener noreferrer"
        >
            FANZAで確認
        </a>
        """

    cards.append(
        f"""
        <article class="card">

            <div class="number">
                #{i}
            </div>

            {image_html}

            <div class="content">

                <div class="meta">
                    <span>{genre_name}</span>
                    <span>{status}</span>
                </div>

                <h2>{title}</h2>

                <p class="time">
                    {scheduled_at}
                </p>

                {link_html}

            </div>

        </article>
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

<title>
FANZA 投稿候補レビュー
</title>

<style>

body {{
    margin: 0;
    padding: 16px;
    background: #f5f5f5;
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Helvetica Neue",
        Arial,
        sans-serif;
    color: #222;
}}

h1 {{
    font-size: 24px;
    margin: 0 0 8px;
}}

.summary {{
    color: #666;
    margin-bottom: 20px;
}}

.grid {{
    display: grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(280px, 1fr)
        );
    gap: 16px;
}}

.card {{
    background: white;
    border-radius: 14px;
    overflow: hidden;
    position: relative;
    box-shadow:
        0 2px 10px
        rgba(0, 0, 0, 0.08);
}}

.card img {{
    width: 100%;
    display: block;
    aspect-ratio: 4 / 3;
    object-fit: cover;
    background: #ddd;
}}

.content {{
    padding: 14px;
}}

.number {{
    position: absolute;
    top: 8px;
    left: 8px;
    background:
        rgba(0, 0, 0, 0.75);
    color: white;
    padding: 4px 8px;
    border-radius: 8px;
    font-size: 13px;
}}

.meta {{
    display: flex;
    justify-content:
        space-between;
    gap: 8px;
    font-size: 13px;
    color: #666;
}}

h2 {{
    font-size: 16px;
    line-height: 1.45;
}}

.time {{
    font-size: 13px;
    color: #555;
}}

.button {{
    display: block;
    text-align: center;
    text-decoration: none;
    background: #111;
    color: white;
    padding: 12px;
    border-radius: 10px;
    margin-top: 12px;
    font-weight: bold;
}}

</style>

</head>

<body>

<h1>
FANZA 投稿候補レビュー
</h1>

<div class="summary">
候補 {len(schedule)}件
</div>

<div class="grid">

{''.join(cards)}

</div>

</body>

</html>
"""


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(html)


print(
    f"{OUTPUT_FILE} を作成しました。"
)

print(
    f"候補件数: {len(schedule)}"
)
