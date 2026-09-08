import os
import sys
import json
import logging
from datetime import datetime
import requests
import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 環境変数取得
FANZA_API_ID = os.environ.get("FANZA_API_ID")
FANZA_AFFILIATE_ID = os.environ.get("FANZA_AFFILIATE_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")

def get_gspread_client():
    creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(credentials)

def fetch_fanza_items(keyword="新着", hits=20):
    url = "https://api.dmm.com/affiliate/v3/ItemList"
    params = {
        "api_id": FANZA_API_ID,
        "affiliate_id": FANZA_AFFILIATE_ID,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "hits": hits,
        "sort": "date",
        "keyword": keyword,
        "output": "json"
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("result", {}).get("items", [])
    except Exception as e:
        logging.error(f"FANZA APIリクエストエラー: {e}")
        return []

def main():
    if not all([FANZA_API_ID, FANZA_AFFILIATE_ID, GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SHEET_ID]):
        logging.error("必要な環境変数が設定されていません。")
        sys.exit(1)

    gc = get_gspread_client()
    sheet = gc.open_by_key(GOOGLE_SHEET_ID).worksheet("candidates")
    existing_records = sheet.get_all_records()
    
    # 重複チェック用の既存IDセット
    existing_ids = {str(r.get("id")) for r in existing_records if r.get("id")}

    items = fetch_fanza_items()
    new_rows = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in items:
        content_id = item.get("content_id")
        if not content_id or str(content_id) in existing_ids:
            continue

        title = item.get("title", "")
        actresses = ", ".join([a.get("name") for a in item.get("iteminfo", {}).get("actress", [])])
        date = item.get("date", "")
        keywords = ", ".join([k.get("name") for k in item.get("iteminfo", {}).get("keyword", [])])
        product_url = item.get("URL", "")
        affiliate_url = item.get("affiliateURL", "")

        # サンプル動画URL取得
        sample_movie_url = ""
        sample_movie_info = item.get("sampleMovieURL", {})
        if sample_movie_info:
            # 高画質サイズを優先的に探索
            for size in ["size_720_480", "size_640_360", "size_476_306"]:
                if size in sample_movie_info:
                    sample_movie_url = sample_movie_info[size]
                    break

        # サンプル画像取得（最大4枚）
        sample_images = item.get("sampleImageURL", {}).get("sample_l", {}).get("image", [])
        img1 = sample_images[0] if len(sample_images) > 0 else ""
        img2 = sample_images[1] if len(sample_images) > 1 else ""
        img3 = sample_images[2] if len(sample_images) > 2 else ""
        img4 = sample_images[3] if len(sample_images) > 3 else ""

        # 紹介文自動生成
        intro_text = f"【新作情報】{title}\n出演: {actresses if actresses else '話題の女優'}\n配信開始日: {date}"

        row = [
            content_id, title, actresses, date, keywords, product_url, sample_movie_url,
            img1, img2, img3, img4, affiliate_url, intro_text, "未選定", now_str
        ]
        new_rows.append(row)

    if new_rows:
        sheet.append_rows(new_rows)
        logging.info(f"{len(new_rows)} 件の新規作品を candidates シートに追加しました。")
    else:
        logging.info("新規作品はありませんでした。")

if __name__ == "__main__":
    main()
