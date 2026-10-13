"""T18: per run of race_interblock_none-lock_rtraw (setup/t18_rtraw_schedules.sh), the reported
verdicts and hb_races records with their a2_uncertain flags, vector-clock mode."""
import glob, json, sys
sys.path.insert(0, "/home/fzheng4/wt-t18/python")
import sync_dominance as sd

root = sys.argv[1]
for rt in ("installed", "t15"):
    sigs = {}
    for k in range(1, 6):
        d = f"{root}/{rt}/{k}"
        trs = sorted(glob.glob(d + "/dependency_*/kernel_*.json"))
        dots = sorted(glob.glob(d + "/*_extracted_cubins/*.dot"))
        if not trs or not dots:
            print(rt, k, "NO TRACE"); continue
        t = json.load(open(trs[-1]))
        rep = None
        for dot in dots:
            try: rep = sd.analyze(dot, trs[-1]); break
            except sd.AlignmentError: pass
        rv = [(v["race_type"], v["verdict"], v["hb_class"], v["a2_uncertain"])
              for v in rep["verdicts"] if v["verdict"] != "ORDERED"]
        recs = [(r["kind"], r.get("class"), r.get("a2_uncertain"), r.get("count")) for r in t.get("hb_races", [])]
        lock_cas = [e for e in t["hb_events"] if "lanes" in e]
        sig = (tuple(rv), tuple(recs))
        sigs.setdefault(sig, []).append(k)
        print(f"{rt} run{k}: events={len(t['hb_events'])} reports={rv} hb_races={recs} tv={t.get('tv_violation')}")
    print(f"{rt}: {len(sigs)} distinct outcome(s): " + "; ".join(f"runs {v}" for v in sigs.values()))
