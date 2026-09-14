import logging, os, requests
from common import *

API="https://api.dmm.com/affiliate/v3/ItemList"
def text(v): return v if isinstance(v,str) else ""
def main():
    setup_logging(); ws=worksheet("candidates",CANDIDATE_HEADERS)
    seen={(str(r.get("id","")),r.get("商品ページURL","")) for _,r in records(ws)}
    params={"api_id":required("FANZA_API_ID"),"affiliate_id":required("FANZA_AFFILIATE_ID"),"site":"FANZA","service":"digital","floor":"videoa","hits":100,"output":"json","sort":"date"}
    if os.getenv("FANZA_QUERY"): params["keyword"]=os.environ["FANZA_QUERY"]
    if os.getenv("FANZA_ACTRESS_ID"): params["article"]="actress"; params["article_id"]=os.environ["FANZA_ACTRESS_ID"]
    data=requests.get(API,params=params,timeout=30); data.raise_for_status()
    items=data.json().get("result",{}).get("items",[]); added=0
    for item in items:
        cid=str(item.get("content_id",item.get("product_id",""))); url=text(item.get("URL"))
        if (cid,url) in seen or any(cid==a or (url and url==b) for a,b in seen): continue
        sample=item.get("sampleMovieURL") or {}; movie=text(sample.get("size_720_480") or sample.get("size_644_414") or sample.get("size_476_306") or sample.get("size_560_360"))
        imgs=(item.get("sampleImageURL",{}).get("sample_s",{}).get("image") or [])[:4]
        actress=[]
        for a in item.get("iteminfo",{}).get("actress",[]): actress.append(text(a.get("name")))
        title=text(item.get("title")); intro=f"{title}が配信開始！"+(f"{', '.join(filter(None,actress))}出演" if actress else "")
        row=[cid,title,", ".join(filter(None,actress)),text(item.get("date")),os.getenv("FANZA_QUERY",""),url,movie,*([text(x) for x in imgs]+[""]*4)[:4],text(item.get("affiliateURL")),intro,"未確認","未選定",now_jst().isoformat(timespec="seconds"),""]
        ws.append_row(row,value_input_option="RAW"); seen.add((cid,url)); added+=1
    logging.info("候補を %d 件追加しました",added)
if __name__=="__main__": main()

