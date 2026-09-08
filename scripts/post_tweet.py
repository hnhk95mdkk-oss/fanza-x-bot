import os
import sys
import json
import logging
import tempfile
from datetime import datetime
import requests
import tweepy
import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

X_API_KEY = os.environ.get("X_API_KEY")
X_API_SECRET = os.environ.get("X_API_SECRET")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET")
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")

def get_x_clients():
    # API v1.1 (メディアアップロード用)
    auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
    api_v1 = tweepy.API(auth)
    
    # API v2 (ツイート投稿用)
    client_v2 = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_SECRET
    )
    return api_v1, client_v2

def download_file(url, dest_path):
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

def process_post(row, api_v1, client_v2):
    intro_text = row.get("確定紹介文", "")
    drive_url = row.get("Drive動画URL", "")
    affiliate_url = row.get("アフィリエイトURL", "")
    img_urls = [
        row.get("サンプル画像URL1"),
        row.get("サンプル画像URL2"),
        row.get("サンプル画像URL3"),
        row.get("サンプル画像URL4")
    ]
    img_urls = [u for u in img_urls if u]

    # --- Tweet 1: 紹介文 + 動画 ---
    video_media_id = None
    if drive_url:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_video:
            tmp_video_path = tmp_video.name
        try:
            download_file(drive_url, tmp_video_path)
            media = api_v1.media_upload(filename=tmp_video_path, media_category="tweet_video")
            video_media_id = media.media_id_string
        finally:
            if os.path.exists(tmp_video_path):
                os.remove(tmp_video_path)

    tweet1_text = f"{intro_text}\n\n【PR】"
    kwargs1 = {"text": tweet1_text}
    if video_media_id:
        kwargs1["media_ids"] = [video_media_id]
        kwargs1["possibly_sensitive"] = True

    res1 = client_v2.create_tweet(**kwargs1)
    tweet1_id = res1.data["id"]

    # --- Tweet 2: リプライ (アフィリエイトリンク) ---
    tweet2_text = f"続きはこちら【PR】\n{affiliate_url}"
    res2 = client_v2.create_tweet(
        text=tweet2_text,
        in_reply_to_tweet_id=tweet1_id
    )
    tweet2_id = res2.data["id"]

    # --- Tweet 3: リプライ (サンプル画像) ---
    image_media_ids = []
    for img_url in img_urls:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_img:
            tmp_img_path = tmp_img.name
        try:
            download_file(img_url, tmp_img_path)
            media = api_v1.media_upload(filename=tmp_img_path)
            image_media_ids.append(media.media_id_string)
        finally:
            if os.path.exists(tmp_img_path):
                os.remove(tmp_img_path)

    tweet3_id = ""
    if image_media_ids:
        res3 = client_v2.create_tweet(
            text="サンプル画像",
            media_ids=image_media_ids,
            possibly_sensitive=True,
            in_reply_to_tweet_id=tweet2_id
        )
        tweet3_id = res3.data["id"]

    return tweet1_id, tweet2_id, tweet3_id

def main():
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET, GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SHEET_ID]):
        logging.error("必要な環境変数が設定されていません。")
        sys.exit(1)

    creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(credentials)
    
    sheet = gc.open_by_key(GOOGLE_SHEET_ID).worksheet("schedule")
    records = sheet.get_all_records()

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # 本日の投稿済み件数チェック (上限3件)
    posted_today_count = sum(
        1 for r in records 
        if r.get("投稿ステータス") == "投稿済み" and str(r.get("投稿予定日")) == today_str
    )

    if posted_today_count >= 3:
        logging.info("本日の投稿上限(3件)に達しているため実行を終了します。")
        return

    api_v1, client_v2 = get_x_clients()

    for i, row in enumerate(records, start=2):
        status = row.get("投稿ステータス")
        scheduled_time_str = str(row.get("抽選済み時刻")).strip()

        if status == "未投稿" and scheduled_time_str:
            try:
                scheduled_time = datetime.strptime(scheduled_time_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

            if now >= scheduled_time:
                logging.info(f"行 {i}: 投稿処理を開始します...")
                try:
                    t1_id, t2_id, t3_id = process_post(row, api_v1, client_v2)
                    
                    sheet.update_cell(i, 9, t1_id)       # I列: tweet1_id
                    sheet.update_cell(i, 10, t2_id)      # J列: tweet2_id
                    sheet.update_cell(i, 11, t3_id)      # K列: tweet3_id
                    sheet.update_cell(i, 12, "投稿済み") # L列: 投稿ステータス
                    sheet.update_cell(i, 13, "")         # M列: エラーログクリア
                    logging.info(f"行 {i}: 投稿が正常に完了しました。")
                    break  # 1回の実行で1件のみ処理
                except Exception as e:
                    logging.error(f"行 {i}: 投稿中にエラーが発生しました: {e}")
                    sheet.update_cell(i, 12, "失敗")
                    sheet.update_cell(i, 13, str(e))

if __name__ == "__main__":
    main()
