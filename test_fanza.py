import os
import requests

API_URL = "https://api.dmm.com/affiliate/v3/ItemList"

api_id = os.environ["DMM_API_ID"].strip()
affiliate_id = os.environ["DMM_AFFILIATE_ID"].strip()

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

response = requests.get(
    API_URL,
    params=params,
    timeout=30
)

print("HTTP status:", response.status_code)
print("")
print("=== RESPONSE ===")
print(response.text)
print("================")
print("")

if response.status_code != 200:
    raise SystemExit("FANZA API request failed")

data = response.json()

items = data.get("result", {}).get("items", [])

if not items:
    print("商品が取得できませんでした。")
    raise SystemExit(1)

item = items[0]

print("=== FANZA ITEM ===")
print("タイトル:", item.get("title"))
print("価格:", item.get("prices", {}).get("price"))
print("商品URL:", item.get("URL"))
print("アフィリエイトURL:", item.get("affiliateURL"))
print("画像URL:", item.get("imageURL", {}).get("large"))
