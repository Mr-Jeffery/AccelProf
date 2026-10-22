#!/usr/bin/env python3
"""X1-follow section 2: the bisect table from eval/x1_follow/bisect/*.json (x1f_bisect.sh), as markdown.
Per candidate: what scalar-clock mode computes at that commit, the bfs wall and kernels finished in both
modes (600 s cap), and the time of Kernel2 launches 13 and 15 (kernel JSON write-time deltas, 1 s mtime
resolution) -- the launches that hold X1's bfs time."""
import json, os, subprocess
W = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../..")
B = f"{W}/eval/x1_follow/bisect"
CANDS = ("b7d463e 1a45653 6d843e3 07d2798 bc32a1f 3331d35 0b64d34 ebc464f 870dbb6 33a985c be82754 b3bfdf3 "
         "7849a70 de565c0 b6c9055 0a25f7d d67ed41 3c7eefd d3f1e98 ba99486").split()
TASK = {"b7d463e": "Sept-22 runtime (eval merge)", "1a45653": "T8", "6d843e3": "T5a", "07d2798": "T2",
        "bc32a1f": "T1a", "3331d35": "T1a review", "0b64d34": "T3b", "ebc464f": "T9", "870dbb6": "T3b×T9 fix",
        "33a985c": "T14", "be82754": "T10", "b3bfdf3": "T5b", "7849a70": "T12", "de565c0": "T15",
        "b6c9055": "T17", "0a25f7d": "T18", "d67ed41": "T4", "3c7eefd": "T19", "d3f1e98": "T16", "ba99486": "T20"}


def git(*a):
    return subprocess.run(["git", "-C", W, *a], capture_output=True, text=True).stdout.strip()


def has(c, pat):
    return subprocess.run(["git", "-C", W, "grep", "-q", pat, c, "--",
                           "sanalyzer/src/tools/pc_dependency_analysis.cpp"]).returncode == 0


def ktimes(d):
    out, prev = {}, 0.0
    for k in d["kernels"]:
        i = int(k["file"].split("_")[1].split(".")[0])
        out[i] = round(k["t"] - prev)
        prev = k["t"]
    return out


def cell(n):
    p = f"{B}/{n}.json"
    if not os.path.exists(p):
        return None
    return json.load(open(p))


def fmt(d):
    if d is None:
        return "—", "—", "—", "—"
    w = f"**{d['wall']:.1f} (cap)**" if d["timed_out"] else f"{d['wall']:.1f}"
    kt = ktimes(d)
    k13 = f"{kt[13]}" if 13 in kt else "not reached"
    k15 = f"{kt[15]}" if 15 in kt else "not reached"
    return w, f"{d['nkernels']}/24", k13, k15


def main():
    print("| # | commit | date | merge | scalar-clock mode at this commit | knobs | bfs SC wall (s) | SC kernels | SC Kernel2 #13 / #15 (s) | bfs VC wall (s) | VC kernels | VC Kernel2 #13 / #15 (s) |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    rows = [("installed", "d38d057 (= ba99486 build)", "2026-10-13", "installed runtime (X1)")] + \
           [(c, c, git("log", "-1", "--format=%ad", "--date=short", c), TASK[c]) for c in CANDS]
    for n, (c, label, date, task) in enumerate(rows):
        if c == "installed":
            knobs, scm = "MODE, DUMP=0, STATS", "sync instance online"
            sc, vc = cell("bfs-sc-installed"), cell("bfs-vc-installed")
        else:
            mode = has(c, "YOSEMITE_HB_MODE")
            dump = has(c, "YOSEMITE_HB_DUMP")
            knobs = ("MODE" if mode else "NO_ENGINE") + (", DUMP=0" if dump else ", dump") + \
                    (", STATS" if has(c, "YOSEMITE_HB_STATS") else "")
            scm = "sync instance online (T4)" if dump else "records dumped only (no HbClock)"
            sc, vc = cell(f"bfs-sc-{c}"), cell(f"bfs-vc-{c}")
        a, b, c13, c15 = fmt(sc)
        x, y, v13, v15 = fmt(vc)
        print(f"| {n} | `{label}` | {date} | {task} | {scm} | {knobs} | {a} | {b} | {c13} / {c15} | {x} | {y} | {v13} / {v15} |")
    ctl = cell("bfs-sc-installed-nostats")
    if ctl:
        a, b, c13, c15 = fmt(ctl)
        print(f"| — | `installed`, YOSEMITE_HB_STATS unset | | control | sync instance online | MODE, DUMP=0 | {a} | {b} | {c13} / {c15} | | | |")
    print()
    print("| nbody run | wall (s) | kernels finished | per-kernel time of the finished kernels (s) | µs / event of finished `accelerate_particles` launches |")
    print("|---|---|---|---|---|")
    for f in sorted(os.listdir(B)):
        if f.startswith("nbody-") and f.endswith(".json"):
            d = json.load(open(f"{B}/{f}"))
            kt = ktimes(d)
            # a capped dump run (pre-T4) is killed while it writes its last kernel JSON: a file whose record
            # count differs from that kernel's count in a complete run (nbody: 32,005,004 / 10,504 / 20,004 per
            # launch, X1) is a truncated write, not a finished kernel -- listed, never timed
            EXP = {0: 32005004, 1: 10504, 2: 20004}
            ok, bad = {}, []
            for j, i in enumerate(sorted(kt)):
                k = d["kernels"][j]
                ev = k.get("hb_events_count") or k.get("seq_records")
                (ok.__setitem__(i, (kt[i], ev)) if ev == EXP[i % 3] else bad.append((i, ev)))
            us = ", ".join(f"#{i}: {t / ev * 1e6:.2f}" for i, (t, ev) in sorted(ok.items()) if i % 3 == 0) or "none finished"
            tr = "; ".join(f"#{i} truncated at the kill ({ev:,} records)" for i, ev in bad)
            print(f"| {f[:-5]} | {d['wall']:.1f}{' (cap)' if d['timed_out'] else ''} | {len(ok)}{' + ' + tr if tr else ''} | "
                  f"{', '.join(f'#{i}: {t}' for i, (t, ev) in sorted(ok.items()))} | {us} |")


main()
