#!/usr/bin/env python3
"""X1-follow Part 4: the partial-run rule in X1's result rows. A run killed by OOM or by the time
limit keeps every verdict it produced; its row's notes start with
    partial: <OOM|TIMEOUT> after <N> of <M> kernels, <wall> s, cap=<s>;
No verdict, report or other field changes (the rows are rewritten field for field; only `notes`
gains the prefix; a re-run replaces an earlier prefix, e.g. once M is known).
  kind TIMEOUT  the rep timed out (verdict TIMEOUT, rc 124, meta `timed_out`)
  kind OOM      the rep did not complete, did not time out, and its accelprof stderr (meta `err` or
                the log tail) shows the app SIGKILLed ("Killed"; the harness makes the traced app the
                kernel OOM killer's first victim, blib._prefer_oom_victim)
  N  kernel JSONs on disk when the run ended (the row's nkernels=)
  M  kernel JSONs of a COMPLETE rep of the same program in any X1 store and mode ("?" when no X1 run
     of the program completed; listed)
Reads the shard CSVs of eval/results/{final,final-long,final-long-sc,final-24h-vc,final-24h-sc}/ and
the meta extraction of x1f_extract.py; --skip names shard files still being written (running tasks).
  x1f_partial_notes.py --meta eval/x1_follow/x1_meta.json --list eval/x1_follow/partial_rows.csv [--apply]
"""
import argparse
import csv
import glob
import json
import os
import re

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../results")
DIRS = {"final": "final-2026-10", "final-long": "final-2026-10-long", "final-long-sc": "final-2026-10-long-sc",
        "final-24h-vc": "final-2026-10-24h-vc", "final-24h-sc": "final-2026-10-24h-sc"}
PREFIX = "partial: "


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", required=True)
    ap.add_argument("--list", required=True)
    ap.add_argument("--skip", default="", help="comma list of shard CSV basenames not to touch")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    X = json.load(open(a.meta))
    reps = {(p["store"], p["id"], p["mode"], int(p["rep"])): p for p in X["partial"]}
    full = {i: v for i, v in X["complete_nkernels"].items()}
    skip = set(x for x in a.skip.split(",") if x)
    out, touched, files = [], 0, 0
    for d, store in DIRS.items():
        for f in sorted(glob.glob(f"{RES}/{d}/baselines-cuvein-shard*.csv")):
            if os.path.basename(f) in skip:
                print(f"skip (still being written): {d}/{os.path.basename(f)}")
                continue
            with open(f, newline="") as fh:
                rd = csv.DictReader(fh)
                cols, rows = rd.fieldnames, list(rd)
            changed = False
            for r in rows:
                notes = r["notes"] or ""
                p = reps.get((store, r["id"], r["mode"], int(r["rep"] or 0)))
                to = r["verdict"] == "TIMEOUT"
                if not to and p is None:
                    continue            # a complete rep
                if p is None:
                    kind, ev = "?", "no meta record"
                elif p.get("timed_out"):
                    kind, ev = "TIMEOUT", f"timed_out rc={p.get('rc')}"
                elif "Killed" in ((p.get("err") or "") + (p.get("log_tail") or "")):
                    kind, ev = "OOM", (f"rc={p.get('rc')} (native rc {p.get('native_rc')}), 'Killed' in the accelprof stderr, "
                                       f"peak {p.get('peak_mb')} MB of {p.get('mem_total_gb')} GB")
                else:
                    kind, ev = "other", f"rc={p.get('rc')} complete={p.get('complete')}: {(p.get('err') or '')[-160:]}"
                if to and kind not in ("TIMEOUT", "?"):
                    kind, ev = "?", f"verdict TIMEOUT but meta says {ev}"
                nk = re.search(r"nkernels=(\d+)", notes)
                n = nk.group(1) if nk else (str(p.get("nkernels")) if p else "?")
                ms = full.get(r["id"], [])
                m = str(ms[0]) if len(ms) == 1 else ("?" if not ms else "/".join(map(str, ms)))
                capm = re.search(r"cap=(\d+)", notes)
                cap = capm.group(1) if capm else (str(p.get("cap")) if p else "?")
                note = f"{PREFIX}{kind} after {n} of {m} kernels, {float(r['wall_s']):.0f} s, cap={cap}"
                base = notes.split(";", 1)[1] if notes.startswith(PREFIX) else notes   # re-application
                done = notes == f"{note};{base}"
                act = kind in ("TIMEOUT", "OOM") and not done
                if act:
                    r["notes"] = f"{note};{base}"
                    changed = True
                    touched += 1
                out.append(dict(results=f"{d}/{os.path.basename(f)}", id=r["id"], mode=r["mode"], rep=r["rep"],
                                verdict=r["verdict"], kind=kind, n=n, m=m, wall_s=r["wall_s"], cap=cap,
                                peak_mb=r["peak_mb"], rc=r["rc"], evidence=ev,
                                action="annotated" if act else ("already" if done else "not annotated"),
                                note=note))
            if changed and a.apply:
                tmp = f + ".tmp"
                with open(tmp, "w", newline="") as fh:
                    w = csv.DictWriter(fh, fieldnames=cols)
                    w.writeheader()
                    w.writerows(rows)
                os.replace(tmp, f)
                files += 1
    with open(a.list, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()) if out else ["results"])
        w.writeheader()
        w.writerows(out)
    by = {}
    for o in out:
        by[(o["kind"], o["action"])] = by.get((o["kind"], o["action"]), 0) + 1
    print(f"{len(out)} partial rows listed -> {a.list}; {'annotated' if a.apply else 'would annotate'} {touched} "
          f"in {files if a.apply else '-'} files; by (kind, action): {by}")


if __name__ == "__main__":
    main()
