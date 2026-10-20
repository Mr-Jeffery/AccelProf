#!/usr/bin/env python3
"""T21a step 6: eval/realworld/manifest.csv, one row per (target, variant) of every target whose status.json says `built`.
    mk_manifest.py [--out eval/realworld/manifest.csv]          (login node; asks `rw.sh <id> info` for the facts)

Format: the columns `eval/baselines/parallel.py` consumes (id,pset,program,build,input,exe,args,stdin,shared_mem,label,
arrays_to_wrap,monitored_kernels,reps,timeout; blib.read_manifest is a csv.DictReader, extra columns are ignored) plus
target,variant,wave,route,kernel,expected_class,oracle,cmd,needs_wrapper.

parallel.py `run`/`collect` runs `accelprof -t pc_dependency_analysis -n 1 ./<exe basename> <args>` in a scratch work dir
holding a symlink to `exe`; it supports neither a working directory nor environment variables, and it extracts the CUDA
ELFs of `exe` only. needs_wrapper=1 marks the rows that need more (a command that is not `<exe> <args>`, environment, a
library holding the kernels): for those T21b uses eval/realworld/run_target.py, a thin wrapper that applies `cmd`'s
environment/cwd and the library cubins before calling the same run_one() of run_cuvein.py.
"""
import argparse, csv, json, os, re, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
RW = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(RW, "manifest.csv"))
    a = ap.parse_args()
    T = {}
    for l in open(os.path.join(RW, "targets.jsonl")):
        t = json.loads(l)
        T[t["id"]] = t
    cols = ["id", "pset", "program", "build", "input", "exe", "args", "stdin", "shared_mem", "label", "arrays_to_wrap",
            "monitored_kernels", "reps", "timeout", "target", "variant", "wave", "route", "kernel", "expected_class", "oracle",
            "cmd", "needs_wrapper"]
    rows = []
    for d in sorted(os.listdir(os.path.join(RW, "targets"))):
        sp = os.path.join(RW, "targets", d, "status.json")
        if not os.path.exists(sp):
            continue
        st = json.load(open(sp))
        if st.get("status") != "built":
            continue
        orp = os.path.join(RW, "oracle", d + ".json")
        orc = json.load(open(orp)) if os.path.exists(orp) else {}
        out = subprocess.run([os.path.join(HERE, "rw.sh"), d, "info"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            f = line.split("\t")
            if f[0] != "ROW":
                continue
            _, tid, v, route, kernel, space, rc, exe, cmd, sha = f[:10]
            t = T[tid]
            argv = cmd.split()
            plain = argv and argv[0] == exe and not re.search(r"[;&|<>$`]|^\w+=", cmd[len(exe):])
            fixed_clean = (orc.get("fixed") or {}).get("expected") == "absent"
            label = "RACE" if v == "buggy" else ("CLEAN" if fixed_clean else "RESIDUAL")
            rows.append({
                "id": "%s-%s" % (tid, v), "pset": "RW", "program": tid, "build": v, "input": (st.get("input") or "")[:120],
                "exe": exe, "args": " ".join(argv[1:]) if plain else "", "stdin": "", "shared_mem": 1 if space == "shared" else 0,
                "label": label, "arrays_to_wrap": "", "monitored_kernels": kernel, "reps": 3, "timeout": 1200,
                "target": tid, "variant": v, "wave": t.get("wave", ""), "route": st.get("route", route), "kernel": kernel,
                "expected_class": t.get("expected_class", ""), "oracle": "eval/realworld/oracle/%s.json" % tid,
                "cmd": cmd, "needs_wrapper": 0 if plain else 1})
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print("wrote %s: %d rows (%d need the wrapper)" % (a.out, len(rows), sum(r["needs_wrapper"] for r in rows)))


main()
