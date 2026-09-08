import os
import sys
import json
import random
import logging
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")

TIME_SLOTS = [
    ((7, 30), (8, 0)),
    ((17, 30), (18, 30)),
    ((22, 30), (23, 30))
]

def get_random_time(date_obj, start_hm, end_hm):
    start_dt = date_obj.replace(hour=start_hm[0], minute=start_hm[1], second=0)
    end_dt = date_obj.replace(hour=end_hm[0], minute=end_hm[1], second=0)
    
    delta_seconds = int((end_dt - start_dt).total_seconds())
    random_seconds = random.randint(0, delta_seconds)
    
    return start_dt + timedelta(seconds=random_seconds)

def main():
    if not all([GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SHEET_ID]):
        logging.error("必要な環境変数が設定されていません。")
        sys.exit(1)

    creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(credentials)
    
    sheet = gc.open_by_key(GOOGLE_SHEET_ID).worksheet("schedule")
    records = sheet.get_all_records()

    # 割り当て対象行の特定 (投稿予定日が空かつ未投稿)
    target_indices = []
    for i, row in enumerate(records, start=2):
        if str(row.get("投稿予定日")).strip() == "" and row.get("投稿ステータス") == "未投稿":
            target_indices.append(i)

    if not target_indices:
        logging.info("抽選対象のレコードが存在しません。")
        return

    # 最大3件選択
    selected_indices = target_indices[:3]
    today = datetime.now().date()

    for idx, row_idx in enumerate(selected_indices):
        slot = TIME_SLOTS[idx]
        scheduled_dt = get_random_time(datetime.combine(today, datetime.min.time()), slot[0], slot[1])
        
        date_str = scheduled_dt.strftime("%Y-%m-%d")
        time_str = scheduled_dt.strftime("%Y-%m-%d %H:%M:%S")

        sheet.update_cell(row_idx, 7, date_str)   # G列: 投稿予定日
        sheet.update_cell(row_idx, 8, time_str)   # H列: 抽選済み時刻
        logging.info(f"行 {row_idx}: 投稿日時を {time_str} に設定しました。")

if __name__ == "__main__":
    main()
