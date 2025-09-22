#!/data/data/com.termux/files/usr/bin/python3
import os, json, time, argparse, collections

def load_jsonl(path):
    items=[]
    if os.path.exists(path):
        with open(path,'r',encoding='utf-8',errors='ignore') as f:
            for ln in f:
                try: items.append(json.loads(ln))
                except: pass
    return items

def within_window(items, since_ts):
    return [x for x in items if int(x.get("ts",0)) >= since_ts]

def group(items):
    g=collections.defaultdict(list)
    for x in items:
        key=(x.get("tag",""), x.get("case",""))
        g[key].append(x)
    return g

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--alerts-dir", default="alerts")
    ap.add_argument("--hours", type=int, default=24)
    args=ap.parse_args()

    os.makedirs("reports", exist_ok=True)
    now=int(time.time())
    since=now - args.hours*3600

    base=os.path.join(args.alerts_dir, "alerts.jsonl")
    hi=os.path.join(args.alerts_dir, "high_priority.jsonl")

    items = load_jsonl(base)
    highs = load_jsonl(hi)
    items24 = within_window(items, since)
    highs24 = within_window(highs, since)

    # always include highs (dedup by (tag,url,page))
    seen=set()
    def key(x): return (x.get("tag",""), x.get("url",""), x.get("page",0))
    out=[]
    for x in items24 + highs24:
        k=key(x)
        if k in seen: continue
        seen.add(k)
        out.append(x)

    # group and format
    groups=group(out)
    date_str=time.strftime("%Y%m%d", time.localtime(now))
    md_path=f"reports/alert_digest_{date_str}.md"

    lines=[]
    lines.append(f"# Alert Digest — {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))}\n")
    if not out:
        lines.append("_No alerts in the last {}h._\n".format(args.hours))
    else:
        # highlight highs first
        highs_set={key(x) for x in highs24}
        if highs_set:
            lines.append("## High Priority (last {}h)\n".format(args.hours))
            for x in out:
                if key(x) in highs_set:
                    lines.append(f"- **[{x.get('tag','')}]** p.{x.get('page','')} — {x.get('url','')}\n  - case: _{x.get('case','')}_ | q: `{x.get('query','')}` | prio: **{x.get('priority',0)}**\n")
            lines.append("")

        # all groups
        for (tag, case), arr in sorted(groups.items(), key=lambda k:(k[0][0],k[0][1])):
            lines.append(f"## {tag or '(untagged)'}  —  _{case or 'no case'}_\n")
            for x in sorted(arr, key=lambda r:(-int(r.get('priority',0)), r.get('url',''), int(r.get('page',0)))):
                ts_h=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(x.get('ts',now))))
                lines.append(f"- [{ts_h}] prio **{x.get('priority',0)}** — p.{x.get('page','')} — {x.get('url','')}\n  - `{x.get('query','')}`\n")
            lines.append("")

    with open(md_path,"w",encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(json.dumps({"ok":True,"md":os.path.abspath(md_path),"items":len(out)}))

if __name__=="__main__":
    main()
