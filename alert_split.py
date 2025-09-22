#!/data/data/com.termux/files/usr/bin/python3
import os, sys, json, argparse, time, hashlib

def key_of(rec):
    base = f"{rec.get('tag','')}|{rec.get('url','')}|{rec.get('page','')}"
    return hashlib.sha1(base.encode('utf-8')).hexdigest()

def load_seen(jsonl_path):
    seen=set()
    if os.path.exists(jsonl_path):
        with open(jsonl_path, 'r', encoding='utf-8', errors='ignore') as f:
            for ln in f:
                try:
                    rec=json.loads(ln)
                    seen.add(key_of(rec))
                except Exception:
                    pass
    return seen

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--alerts-dir", default="alerts")
    ap.add_argument("--min-priority", type=int, default=4)
    args=ap.parse_args()

    d=args.alerts_dir
    os.makedirs(d, exist_ok=True)
    src=os.path.join(d, "alerts.jsonl")
    dst_log=os.path.join(d, "high_priority.log")
    dst_jsonl=os.path.join(d, "high_priority.jsonl")

    if not os.path.exists(src):
        print(json.dumps({"ok":True, "message":"no alerts.jsonl yet"}))
        return

    seen = load_seen(dst_jsonl)
    added=0

    with open(src,'r',encoding='utf-8',errors='ignore') as f, \
         open(dst_log,'a',encoding='utf-8') as flog, \
         open(dst_jsonl,'a',encoding='utf-8') as fjson:
        for ln in f:
            try:
                rec=json.loads(ln)
            except Exception:
                continue
            if int(rec.get("priority",0)) < args.min_priority:
                continue
            k=key_of(rec)
            if k in seen:
                continue
            seen.add(k)
            ts=int(rec.get("ts", time.time()))
            ts_h=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
            line=f"[{ts_h}] PRIORITY {rec.get('priority')} | {rec.get('tag','')} | case={rec.get('case','')} | {rec.get('url','')} p.{rec.get('page','')} | {rec.get('query','')}\n"
            flog.write(line)
            fjson.write(json.dumps(rec, ensure_ascii=False)+"\n")
            added+=1

    print(json.dumps({"ok":True, "added":added, "log":dst_log, "jsonl":dst_jsonl}))
if __name__=="__main__":
    main()
