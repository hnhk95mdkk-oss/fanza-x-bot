import logging, random
from datetime import datetime, timedelta, time
from common import *

SLOTS=[(time(7,30),time(8,0)),(time(17,30),time(18,30)),(time(22,30),time(23,30))]
def random_time(day,start,end):
    a=datetime.combine(day,start,JST); b=datetime.combine(day,end,JST)
    return a+timedelta(seconds=random.randint(0,int((b-a).total_seconds())))
def main():
    setup_logging(); ws=worksheet("schedule",SCHEDULE_HEADERS); rows=records(ws); today=now_jst().date()
    counts={d:sum(1 for _,r in rows if r.get("投稿予定日")==d.isoformat()) for d in (today,today+timedelta(days=1))}
    for rowno,row in rows:
        if row.get("投稿ステータス")!="未投稿" or row.get("投稿予定日"): continue
        day=next((d for d in counts if counts[d]<3),None)
        if not day: break
        slot=SLOTS[counts[day]]; scheduled=random_time(day,*slot); tweet3=scheduled+timedelta(minutes=random.choice([60,75,90]))
        update_fields(ws,rowno,{"投稿予定日":day.isoformat(),"抽選済み時刻":scheduled.isoformat(timespec="minutes"),"tweet3予定時刻":tweet3.isoformat(timespec="minutes")}); counts[day]+=1
        logging.info("%s を %s に割当",row.get("id"),scheduled)
if __name__=="__main__": main()

