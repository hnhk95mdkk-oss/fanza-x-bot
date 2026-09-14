import json, logging, os
from datetime import datetime
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials

JST = ZoneInfo("Asia/Tokyo")
CANDIDATE_HEADERS = ["id","作品名","女優名","発売日","キーワード","商品ページURL","サンプル動画URL","サンプル画像URL1","サンプル画像URL2","サンプル画像URL3","サンプル画像URL4","アフィリエイトURL","自動生成紹介文","利用許可確認","ステータス","収集日時","エラーログ"]
SCHEDULE_HEADERS = ["id","作品名","Drive動画FileID","Drive動画URL","サンプル画像URL1","サンプル画像URL2","サンプル画像URL3","サンプル画像URL4","アフィリエイトURL","確定紹介文","投稿予定日","抽選済み時刻","tweet3予定時刻","tweet1_id","tweet2_id","tweet3_id","投稿ステータス","retry_count","処理中","エラーログ"]

def now_jst(): return datetime.now(JST)
def required(name):
    value=os.getenv(name)
    if not value: raise RuntimeError(f"環境変数 {name} が未設定です")
    return value
def service_account_info():
    raw=required("GOOGLE_SERVICE_ACCOUNT_JSON")
    try: return json.loads(raw)
    except json.JSONDecodeError: return json.load(open(raw, encoding="utf-8"))
def sheets_client():
    scopes=["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    return gspread.authorize(Credentials.from_service_account_info(service_account_info(), scopes=scopes))
def worksheet(name, headers):
    book=sheets_client().open_by_key(required("GOOGLE_SHEET_ID"))
    try: ws=book.worksheet(name)
    except gspread.WorksheetNotFound: ws=book.add_worksheet(name, rows=1000, cols=max(26,len(headers)))
    first=ws.row_values(1)
    if not first: ws.append_row(headers, value_input_option="RAW")
    elif first != headers: raise RuntimeError(f"{name} の列がREADME記載の構成と一致しません: {first}")
    return ws
def records(ws):
    return [(i+2,row) for i,row in enumerate(ws.get_all_records())]
def update_fields(ws,row_number,fields):
    header=ws.row_values(1); cells=[]
    for key,value in fields.items():
        if key not in header: raise KeyError(key)
        cells.append(gspread.Cell(row_number,header.index(key)+1,"" if value is None else str(value)))
    if cells: ws.update_cells(cells, value_input_option="RAW")
def setup_logging(): logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")

