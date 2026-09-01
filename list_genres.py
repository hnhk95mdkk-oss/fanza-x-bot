import os
import requests

API_URL = "https://api.dmm.com/affiliate/v3/GenreSearch"

api_id = os.environ["DMM_API_ID"].strip()
affiliate_id = os.environ["DMM_AFFILIATE_ID"].strip()

params = {
    "api_id": api_id,
    "affiliate_id": affiliate_id,
    "floor_id": 43,
    "hits": 500,
    "offset": 1,
    "output": "json",
}

response = requests.get(API_URL, params=params, timeout=30)

print("HTTP status:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise SystemExit("GenreSearch failed")

data = response.json()

genres = data.get("result", {}).get("genre", [])

print("")
print("=== FANZA ジャンル一覧 ===")

for genre in genres:
    print(
        genre.get("genre_id"),
        ":",
        genre.get("name")
    )
