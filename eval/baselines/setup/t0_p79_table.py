#!/usr/bin/env python3
"""Markdown table of the P7/P9 rows of a T0 store sweep next to the node-local
diagnose run of eval/BASELINES.md section 1b (dump_mb at the 20-minute cap).

  python3 eval/baselines/setup/t0_p79_table.py eval/results/full-2026-09-22 eval/BASELINES.md
"""
import csv
import glob
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "python"))
import hb_modes  # noqa: E402


def main():
    resdir, baselines = sys.argv[1], sys.argv[2]
    prev = {}   # (program, mode) -> (verdict, dump_mb, peak_mb, cause)
    for line in open(baselines):
        m = re.match(r"\| (P[79]) \| ([^|]+) \| ([a-z-]+) \| ([A-Z]*) \| ([^|]*) \| [^|]* \| [^|]* \| ([^|]*) \| ([^|]*) \|", line)
        if m and hb_modes.canon(m.group(3), baselines) in hb_modes.MODES:
            prev[(m.group(2).strip(), hb_modes.canon(m.group(3), baselines))] = (m.group(4).strip(), m.group(6).strip(), m.group(7).strip(), m.group(5).strip())
    rows = []
    for f in sorted(glob.glob(f"{resdir}/*.csv")):
        for r in csv.DictReader(open(f, newline="")):
            if r["id"].startswith(("P7-", "P9-")):
                r["mode"] = hb_modes.canon(r["mode"], f)
                rows.append(r)
    print("| program | mode | T0 verdict (wall s, peak RSS GB) | T0 dump at cap / saved (MB) | node-local run of §1b: verdict, dump (MB), peak GB, cause |")
    print("|---|---|---|---|---|")
    for r in sorted(rows, key=lambda r: (r["id"], r["mode"])):
        prog = r["id"].split("-", 1)[1]
        notes = r["notes"]
        dm = re.search(r"dump_mb=([0-9.]+)", notes)
        ev = re.search(r"events=([^;]+)", notes)
        dump = dm.group(1) if dm else (f"saved, events={ev.group(1)}" if ev else "—")
        if "native_rc" in notes:
            dump = "native failure: " + re.search(r"native_err=([^|;]*)", notes).group(1)[:60]
        elif notes.startswith("no-kernel-json"):
            dump = "collector died (rc=1)"
        elif "partial(rc" in notes:
            dump += " (prefix dump: app died under the tool)"
        peak = float(r["peak_mb"] or 0) / 1000
        p = prev.get((prog, r["mode"]))
        pv = f"{p[0]}, {p[1] or '—'}, {float(p[2])/1000:.0f}, {p[3]}" if p and p[2] else (f"{p[0] or '—'}, {p[1] or '—'}, —, {p[3]}" if p else "—")
        print(f"| {prog} | {r['mode']} | {r['verdict']} ({float(r['wall_s']):.0f} s, {peak:.0f}) | {dump} | {pv} |")


if __name__ == "__main__":
    main()
