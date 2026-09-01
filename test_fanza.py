import os
import requests

API_URL = "https://api.dmm.com/affiliate/v3/ItemList"

api_id = os.environ["DMM_API_ID"]
affiliate_id = os.environ["DMM_AFFILIATE_ID"]

params = {
    "api_id": api_id,
    "affiliate_id": affiliate_id,
    "site": "FANZA",
    "service": "digital",
    "floor": "videoa",
    "hits": 1,
    "sort": "date",
    "output": "json",
}

response = requests.get(API_URL, params=params, timeout=30)

print("HTTP status:", response.status_code)

response.raise_for_status()

data = response.json()

result = data.get("result", {})

if result.get("status") != 200:
    print("API error:")
    print(data)
    raise SystemExit(1)

items = result.get("items", [])

if not items:
    print("商品が取得できませんでした。")
    raise SystemExit(1)

item = items[0]

title = item.get("title", "タイトル不明")
price = item.get("prices", {}).get("price", "価格不明")
affiliate_url = item.get("affiliateURL", "URLなし")
product_url = item.get("URL", "URLなし")
image_url = item.get("imageURL", {}).get("large", "画像なし")

print("")
print("=== FANZA API TEST ===")
print("タイトル:", title)
print("価格:", price)
print("商品URL:", product_url)
print("アフィリエイトURL:", affiliate_url)
print("画像URL:", image_url)
print("======================")
