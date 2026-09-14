import io, logging, os, tempfile, time, requests
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from requests_oauthlib import OAuth1
from common import *

def auth(): return OAuth1(required("X_API_KEY"),required("X_API_SECRET"),required("X_ACCESS_TOKEN"),required("X_ACCESS_SECRET"))
def xpost(path,json):
    r=requests.post("https://api.x.com"+path,json=json,auth=auth(),timeout=60); r.raise_for_status(); return r.json()["data"]
def upload_media(path,category):
    url=os.getenv("X_MEDIA_UPLOAD_URL","https://api.x.com/2/media/upload"); total=os.path.getsize(path)
    init=requests.post(url,data={"command":"INIT","total_bytes":total,"media_type":"video/mp4" if category=="tweet_video" else "image/jpeg","media_category":category},auth=auth(),timeout=60); init.raise_for_status(); mid=str(init.json()["data"]["id"])
    with open(path,"rb") as f:
        seg=0
        while chunk:=f.read(4*1024*1024):
            r=requests.post(url,data={"command":"APPEND","media_id":mid,"segment_index":seg},files={"media":chunk},auth=auth(),timeout=120); r.raise_for_status(); seg+=1
    fin=requests.post(url,data={"command":"FINALIZE","media_id":mid},auth=auth(),timeout=60); fin.raise_for_status(); info=fin.json().get("data",{}).get("processing_info")
    while info and info.get("state") in {"pending","in_progress"}:
        time.sleep(min(int(info.get("check_after_secs",2)),10)); st=requests.get(url,params={"command":"STATUS","media_id":mid},auth=auth(),timeout=30); st.raise_for_status(); info=st.json().get("data",{}).get("processing_info")
    if info and info.get("state")=="failed": raise RuntimeError(f"X media processing failed: {info}")
    return mid
def drive_download(file_id,path):
    svc=build("drive","v3",credentials=Credentials.from_service_account_info(service_account_info(),scopes=["https://www.googleapis.com/auth/drive.readonly"])); req=svc.files().get_media(fileId=file_id)
    with open(path,"wb") as f:
        dl=MediaIoBaseDownload(f,req)
        done=False
        while not done: _,done=dl.next_chunk()
def image_download(url,path):
    r=requests.get(url,timeout=60); r.raise_for_status()
    if not r.headers.get("Content-Type","").startswith("image/"): raise ValueError("画像URLが画像を返しません")
    open(path,"wb").write(r.content)
def due(value):
    if not value:return False
    return datetime.fromisoformat(value).astimezone(JST)<=now_jst()
def main():
    setup_logging(); ws=worksheet("schedule",SCHEDULE_HEADERS); all_rows=records(ws)
    today=now_jst().date().isoformat()
    posted_today=sum(1 for _,r in all_rows if r.get("投稿予定日")==today and r.get("tweet1_id"))
    for rowno,row in all_rows:
        if row.get("投稿ステータス") not in {"未投稿","動画投稿済み","失敗"} or row.get("処理中"): continue
        paths=[]
        try:
            update_fields(ws,rowno,{"処理中":"yes"})
            if not row.get("tweet1_id") and due(row.get("抽選済み時刻")):
                if posted_today>=3:
                    logging.warning("1日3作品の上限に達したため %s を延期",row.get("id")); update_fields(ws,rowno,{"処理中":""}); continue
                f=tempfile.NamedTemporaryFile(delete=False,suffix=".mp4"); f.close(); paths.append(f.name); drive_download(str(row["Drive動画FileID"]),f.name)
                mid=upload_media(f.name,"tweet_video"); t1=xpost("/2/tweets",{"text":f"{row['確定紹介文']}\n【PR】","media":{"media_ids":[mid]},"possibly_sensitive":True})
                t2=xpost("/2/tweets",{"text":f"続きはこちら【PR】\n{row['アフィリエイトURL']}","reply":{"in_reply_to_tweet_id":t1["id"]}})
                update_fields(ws,rowno,{"tweet1_id":t1["id"],"tweet2_id":t2["id"],"投稿ステータス":"動画投稿済み","retry_count":"0","エラーログ":""}); row["tweet2_id"]=t2["id"]; posted_today+=1
            if row.get("tweet2_id") and not row.get("tweet3_id") and due(row.get("tweet3予定時刻")):
                mids=[]
                for i in range(1,5):
                    if not row.get(f"サンプル画像URL{i}"): continue
                    f=tempfile.NamedTemporaryFile(delete=False,suffix=".jpg"); f.close(); paths.append(f.name); image_download(row[f"サンプル画像URL{i}"],f.name); mids.append(upload_media(f.name,"tweet_image"))
                payload={"text":"サンプル画像はこちら","reply":{"in_reply_to_tweet_id":str(row["tweet2_id"])},"possibly_sensitive":True}
                if mids: payload["media"]={"media_ids":mids}
                t3=xpost("/2/tweets",payload); update_fields(ws,rowno,{"tweet3_id":t3["id"],"投稿ステータス":"投稿済み","処理中":"","retry_count":"0","エラーログ":""})
            else: update_fields(ws,rowno,{"処理中":""})
        except Exception as e:
            logging.exception("投稿処理失敗: %s",row.get("id")); retries=int(row.get("retry_count") or 0)+1; update_fields(ws,rowno,{"投稿ステータス":"失敗","retry_count":retries,"処理中":"","エラーログ":str(e)[:1000]})
        finally:
            for p in paths:
                try: os.unlink(p)
                except OSError: pass
if __name__=="__main__": main()
