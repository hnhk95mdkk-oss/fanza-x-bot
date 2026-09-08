import os
import sys
import json
import logging
import tempfile
import requests
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")
GOOGLE_DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")

def get_google_services():
    creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(credentials)
    drive_service = build("drive", "v3", credentials=credentials)
    return gc, drive_service

def download_video(url, dest_path):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(url, stream=True, headers=headers, timeout=30)
    
    content_type = response.headers.get("Content-Type", "")
    if "text/html" in content_type:
        logging.error(f"地域制限エラーの可能性があります (Content-Type: {content_type})")
        return False

    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    file_size = os.path.getsize(dest_path)
    # 1MB未満の場合は地域制限ページ等のエラーレスポンスとみなす
    if file_size < 1024 * 1024:
        logging.error(f"ファイルサイズが小さすぎます: {file_size} bytes")
        return False

    return True

def upload_to_drive(drive_service, file_path, file_name):
    file_metadata = {
        "name": file_name,
        "parents": [GOOGLE_DRIVE_FOLDER_ID]
    }
    media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    file_id = file.get("id")

    # 閲覧権限の設定
    user_permission = {"type": "anyone", "role": "reader"}
    drive_service.permissions().create(fileId=file_id, body=user_permission).execute()

    return f"https://drive.google.com/uc?id={file_id}&export=download"

def main():
    if not all([GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SHEET_ID, GOOGLE_DRIVE_FOLDER_ID]):
        logging.error("必要な環境変数が設定されていません。")
        sys.exit(1)

    gc, drive_service = get_google_services()
    spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)
    cand_sheet = spreadsheet.worksheet("candidates")
    sched_sheet = spreadsheet.worksheet("schedule")

    candidates = cand_sheet.get_all_records()

    for i, row in enumerate(candidates, start=2):  # 1行目はヘッダー
        if row.get("ステータス") == "選定済み":
            video_url = row.get("サンプル動画URL")
            content_id = str(row.get("id"))

            if not video_url:
                logging.warning(f"ID {content_id}: サンプル動画URLが存在しません。スキップします。")
                continue

            logging.info(f"ID {content_id} の動画ダウンロード処理を開始します...")
            
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            try:
                if download_video(video_url, tmp_path):
                    drive_url = upload_to_drive(drive_service, tmp_path, f"{content_id}.mp4")
                    
                    # scheduleシートへ書込
                    sched_row = [
                        content_id,
                        row.get("作品名"),
                        drive_url,
                        row.get("サンプル画像URL1"),
                        row.get("サンプル画像URL2"),
                        row.get("サンプル画像URL3"),
                        row.get("サンプル画像URL4"),
                        row.get("アフィリエイトURL"),
                        row.get("自動生成紹介文"),
                        "", "", "", "", "", "未投稿", ""
                    ]
                    sched_sheet.append_row(sched_row)
                    
                    # candidatesシートのステータス更新
                    cand_sheet.update_cell(i, 14, "処理完了")
                    logging.info(f"ID {content_id}: アップロード・スケジュール追加が完了しました。")
                else:
                    logging.error(f"ID {content_id}: 動画ダウンロードに失敗しました。")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

if __name__ == "__main__":
    main()
