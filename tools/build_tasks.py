#!/usr/bin/env python3
"""なおの勉強手帳のデータ（ArtifactData で保存した JSON）から、さくせんボード用の keikaku/tasks.json を作る。

使い方: python3 -I tools/build_tasks.py <items_dir> <config.json> <出力 tasks.json> [YYYY-MM-DD(今日)]
  items_dir : collection "items" を out_dir で保存したフォルダ（<id>.json が並ぶ）
  config.json: collection "config" doc "main" の data 部分（または {"data":...} 全体）
公開されるので、名前などの個人情報は入れない（教科・宿題名・内容・日付のみ）。
"""
import json, os, sys, datetime as dt

def load(p):
    with open(p, encoding="utf-8") as f:
        j = json.load(f)
    return j.get("data", j) if isinstance(j, dict) and "data" in j and isinstance(j["data"], dict) else j

def d(s): return dt.date.fromisoformat(s)
def iso(x): return x.isoformat()
def jsdow(x): return (x.weekday() + 1) % 7  # 0=日..6=土

def main():
    items_dir, cfg_path, out = sys.argv[1:4]
    today = d(sys.argv[4]) if len(sys.argv) > 4 else dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    cfg = load(cfg_path)
    items = {}
    for fn in os.listdir(items_dir):
        if fn.endswith(".json"):
            it = load(os.path.join(items_dir, fn))
            it["id"] = fn[:-5]
            items[it["id"]] = it
    off = {it["due"] for it in items.values() if it.get("type") == "event" and it.get("off") and it.get("due")}
    lo, hi = today - dt.timedelta(days=14), today + dt.timedelta(days=14)

    # 手帳がまだ作っていない定例（genThrough より後）を、同じ id で補う
    gt = d(cfg["genThrough"]) if cfg.get("genThrough") else today - dt.timedelta(days=1)
    x = gt + dt.timedelta(days=1)
    while x <= hi:
        ds = x.strftime("%Y%m%d")
        for r in cfg.get("routines", []):
            if not r.get("on"): continue
            if r.get("kind") == "study":
                if jsdow(x) in [int(w) for w in r.get("wds", [])]:
                    i = f"h_{r['id']}_{ds}"
                    items.setdefault(i, {"id": i, "type": "study", "habit": True, "src": r.get("src"), "subj": r.get("subj"),
                                         "title": r.get("title"), "assigned": iso(x), "due": "", "plan": iso(x), "done": False})
            elif iso(x) not in off and int(r.get("wd", -1)) == jsdow(x):
                i = f"r_{r['id']}_{ds}"
                plan = ""
                pw = r.get("planWd")
                if pw not in ("", None):
                    for k in range(1, 8):
                        y = x + dt.timedelta(days=k)
                        if jsdow(y) == int(pw): plan = iso(y); break
                items.setdefault(i, {"id": i, "type": "hw", "src": r.get("src"), "subj": r.get("subj"), "title": r.get("title"),
                                     "assigned": iso(x), "due": iso(x + dt.timedelta(days=int(r.get("dueDays") or 7))), "plan": plan, "done": False})
        x += dt.timedelta(days=1)

    tasks, tests, events = [], [], []
    for it in items.values():
        t = it.get("type")
        if t in ("hw", "study"):
            habit = bool(it.get("habit"))
            key = it.get("plan") if habit else (it.get("assigned") or it.get("plan") or it.get("due"))
            if not key: continue
            k = d(key)
            if habit and not (today - dt.timedelta(days=7) <= k <= hi): continue
            if not habit and not (lo <= k <= hi) and not (it.get("due") and lo <= d(it["due"]) <= hi): continue
            tasks.append({
                "id": it["id"], "kind": "habit" if habit else ("hw" if t == "hw" else "study"),
                "subj": it.get("subj") or "その他", "src": it.get("src") or "", "title": it.get("title") or "",
                "lesson": it.get("lesson") or "", "detail": it.get("detail") or "",
                "assigned": it.get("assigned") or "", "due": it.get("due") or "", "suggest": it.get("plan") or "",
                "doneInNotebook": bool(it.get("done")),
            })
        elif t == "test" and it.get("due") and today - dt.timedelta(days=1) <= d(it["due"]) <= today + dt.timedelta(days=90):
            tests.append({"id": it["id"], "title": it.get("title") or "", "subj": it.get("subj") or "", "due": it["due"], "range": it.get("range") or ""})
        elif t == "event" and it.get("due") and today - dt.timedelta(days=1) <= d(it["due"]) <= today + dt.timedelta(days=60):
            events.append({"title": it.get("title") or "", "due": it["due"], "off": bool(it.get("off"))})
    tasks.sort(key=lambda a: (a["assigned"] or a["suggest"], a["id"]))
    tests.sort(key=lambda a: a["due"]); events.sort(key=lambda a: a["due"])
    out_j = {"version": 1, "updated": dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%Y-%m-%dT%H:%M+09:00"),
             "week": cfg.get("week", {}), "tasks": tasks, "tests": tests, "events": events}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(out_j, f, ensure_ascii=False, indent=1)
    print(f"tasks={len(tasks)} tests={len(tests)} events={len(events)} -> {out}")

if __name__ == "__main__":
    main()
