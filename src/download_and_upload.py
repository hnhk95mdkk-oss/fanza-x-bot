import io, logging, mimetypes, os, tempfile, requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from common import *

MIN_BYTES=int(os.getenv("MIN_VIDEO_BYTES","100000"))
def drive(): return build("drive","v3",credentials=Credentials.from_service_account_info(service_account_info(),scopes=["https://www.googleapis.com/auth/drive"]))
def main():
    setup_logging(); cws=worksheet("candidates",CANDIDATE_HEADERS); sws=worksheet("schedule",SCHEDULE_HEADERS); svc=drive()
    scheduled={str(r.get("id")) for _,r in records(sws)}
    for rowno,row in records(cws):
        if row.get("ステータス")!="選定済み" or row.get("利用許可確認")!="確認済み" or str(row.get("id")) in scheduled: continue
        path=None
        try:
            url=row.get("サンプル動画URL");
            if not url: raise ValueError("サンプル動画URLが空です")
            with requests.get(url,stream=True,timeout=(15,120),headers={"User-Agent":"Mozilla/5.0"}) as res:
                res.raise_for_status(); ctype=res.headers.get("Content-Type","").split(";")[0].lower()
                if not ctype.startswith("video/"): raise ValueError(f"動画ではないContent-Type: {ctype}")
                suffix=mimetypes.guess_extension(ctype) or ".mp4"; f=tempfile.NamedTemporaryFile(delete=False,suffix=suffix); path=f.name
                with f:
                    for chunk in res.iter_content(1024*1024):
                        if chunk: f.write(chunk)
            if os.path.getsize(path)<MIN_BYTES: raise ValueError(f"動画が小さすぎます: {os.path.getsize(path)} bytes")
            meta={"name":f"{row['id']}{suffix}","parents":[required("GOOGLE_DRIVE_FOLDER_ID")]}
            file=svc.files().create(body=meta,media_body=MediaFileUpload(path,mimetype=ctype,resumable=True),fields="id,webViewLink").execute()
            sws.append_row([row.get("id"),row.get("作品名"),file["id"],file.get("webViewLink","")]+[row.get(f"サンプル画像URL{i}","") for i in range(1,5)]+[row.get("アフィリエイトURL",""),row.get("自動生成紹介文",""),"","","","","","","未投稿","0","",""] ,value_input_option="RAW")
            update_fields(cws,rowno,{"ステータス":"投稿待ち","エラーログ":""}); logging.info("%s をDriveへ保存",row.get("id"))
        except Exception as e:
            logging.exception("%s の取得・保存に失敗",row.get("id")); update_fields(cws,rowno,{"エラーログ":str(e)[:1000]})
        finally:
            if path and os.path.exists(path): os.unlink(path)
if __name__=="__main__": main()

