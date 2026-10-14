#!/usr/bin/env python3
"""X2 (eval/FINAL_CERTAIN.md section 4): the cross-recording differences of the invariant run,
checked on ONE trace. The sweep's two legs are two recordings, so a pair one leg reports and the
other does not can be the policy or the schedule. Here every program of --ids is recorded REPS
times under each policy WITH the lossless dump (YOSEMITE_HB_DUMP=1, vector-clock mode, the
installed runtime, the harness's own extraction and environment), and every dump is replayed by
the specification (python/hb_oracle.py, frozen) under both policies:

  parity     HbClock's hb_races == the oracle's under the dump's own policy (T16's parity key:
             pc pair, kind, class, space, dist, async, count, a2_uncertain), sync pairs and
             hb_chain equal;
  invariant  on the same dump, oracle(certain) >= oracle(recorded) at the aggregate key with
             counts, equal sync pairs, and per key the same number of UNFLAGGED instances
             (so every instance the certain clock adds is a2_uncertain; CERTAIN_CLOCK.md
             section 1);
  schedule   per watched pc pair (--watch id:0xA-0xB, repeatable): in which recordings HbClock
             reports it, with its class, instances and flagged instances.

Run on a GPU node from the worktree root (ACCEL_PROF_HOME = the worktree):
  .env/bin/python eval/baselines/setup/x2_same_trace.py --out <dir> --reps 3 --ids a,b,c \
      [--watch P4-reduction-norace-small:0xa20-0x1680]
Writes <out>/same_trace.json and prints the tables.
"""
import argparse
import csv
import glob
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "eval" / "baselines"))
sys.path.insert(0, str(ROOT / "python"))
import blib  # noqa: E402
import hb_oracle  # noqa: E402
import sync_dominance as sd  # noqa: E402

VC = blib.hb_modes.VECTOR_CLOCK
KEY = lambda r: (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
                 r.get("async"), r.get("count"), r.get("a2_uncertain"))
AGG = lambda r: (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
                 r.get("async"))


def manifest_rows(ids):
    rows = {r["id"]: r for r in csv.DictReader(open(ROOT / "eval/baselines/manifest.csv"))}
    return [rows[i] for i in ids]


def record(m, out, policy, rep, cuda, cubindir, scope):
    exe = m["exe"]
    d = Path(out) / m["id"] / f"{policy}-{rep}"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    base = os.path.basename(exe)
    os.symlink(os.path.realpath(exe), d / base)
    args = [x for x in (m["args"] or "").split() if x]
    env = blib.base_env(cuda, hb_trace=True, hb_mode=VC, scope_file=scope or None)
    env["YOSEMITE_HB_DUMP"] = "1"                # lossless: the oracle replays hb_events
    env["YOSEMITE_HB_GATE_POLICY"] = policy
    env.pop("YOSEMITE_HB_STATS", None)
    wall, peak, rc, to = blib.run_timed(["accelprof", "-t", "pc_dependency_analysis", "-n", "1",
                                         f"./{base}", *args], env, str(d), 1200, poll_mem=True,
                                        stdin_path=m["stdin"] or None,
                                        stderr_path=str(d / "stderr.txt"))
    deps = sorted(glob.glob(f"{d}/dependency_{base}_*"), key=os.path.getmtime)
    kjs = sorted(glob.glob(f"{deps[-1]}/kernel_*.json")) if deps else []
    return kjs, dict(wall=wall, rc=rc, timed_out=to, kernels=len(kjs))


def oracle(dots, kj, **kw):
    for dot in dots:
        try:
            return hb_oracle.analyze(str(dot), str(kj), **kw)
        except sd.AlignmentError:
            continue
    return None


def agg(races):
    c, u = Counter(), Counter()
    for r in races:
        c[AGG(r)] += r.get("count", 1)
        u[AGG(r)] += r.get("count", 1) - r.get("a2_uncertain", 0)
    return c, u


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--ids", required=True)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--watch", action="append", default=[])
    a = ap.parse_args()
    cuda = blib.resolve_cuda_home()
    watch = {}
    for w in a.watch:
        pid, pair = w.split(":")
        x, y = (int(v, 16) for v in pair.split("-"))
        watch.setdefault(pid, []).append(tuple(sorted((x, y))))
    res, bad = [], 0
    for m in manifest_rows(a.ids.split(",")):
        cubindir = f"{a.out}/{m['id']}/cubins"
        shutil.rmtree(cubindir, ignore_errors=True)
        nenv = blib.base_env(cuda)
        scope, _ = blib.extract(os.path.realpath(m["exe"]), cubindir, nenv)
        dots = sorted(Path(cubindir).glob("*.dot"))
        for rep in range(1, a.reps + 1):
            for policy in ("recorded", "certain"):
                kjs, info = record(m, a.out, policy, rep, cuda, cubindir, scope)
                row = dict(id=m["id"], policy=policy, rep=rep, **info, parity=0, parity_bad=0,
                           invariant_bad=0, rec_inst=0, cer_inst=0, unflagged_rec=0,
                           unflagged_cer=0, watched={})
                for kj in kjs:
                    t = json.load(open(kj))
                    own = oracle(dots, kj)
                    if own is None:
                        row["parity_bad"] += 1
                        continue
                    ok = (t.get("hb_gate_policy") == policy == own["gate_policy"]
                          and {KEY(r) for r in t.get("hb_races", [])} == {KEY(r) for r in own["races"]}
                          and t.get("hb_races_sync_only") == own["races_sync_only"]
                          and t.get("hb_chain") == own["chain"])
                    row["parity"] += ok
                    row["parity_bad"] += not ok
                    rec = own if policy == "recorded" else oracle(dots, kj, gate_policy="recorded")
                    cer = own if policy == "certain" else oracle(dots, kj, gate_policy="certain")
                    (cr, ur), (cc, uc) = agg(rec["races"]), agg(cer["races"])
                    sup = all(cc.get(k, 0) >= n for k, n in cr.items()) and \
                        rec["races_sync_only"] == cer["races_sync_only"]
                    same_unfl = all(uc.get(k, 0) == n for k, n in ur.items() if n) and \
                        all(ur.get(k, 0) == n for k, n in uc.items() if n)
                    row["invariant_bad"] += not (sup and same_unfl)
                    row["rec_inst"] += sum(cr.values())
                    row["cer_inst"] += sum(cc.values())
                    row["unflagged_rec"] += sum(ur.values())
                    row["unflagged_cer"] += sum(uc.values())
                    for r in t.get("hb_races", []):    # HbClock's pairs in this recording
                        if r.get("a_pc") is None:
                            continue
                        pk = "-".join(hex(p) for p in sorted((r["a_pc"], r["b_pc"])))
                        x = row.setdefault("pairs", {}).setdefault(pk, [0, 0])
                        x[0] += r.get("count", 1)
                        x[1] += r.get("count", 1) - r.get("a2_uncertain", 0)
                    for pr in watch.get(m["id"], ()):
                        for r in t.get("hb_races", []):
                            if tuple(sorted((r.get("a_pc"), r.get("b_pc")))) == pr:
                                w = row["watched"].setdefault(f"{hex(pr[0])}-{hex(pr[1])}",
                                                              dict(count=0, a2=0, cls=set()))
                                w["count"] += r.get("count", 1)
                                w["a2"] += r.get("a2_uncertain", 0)
                                w["cls"].add(r.get("class"))
                bad += row["parity_bad"] + row["invariant_bad"] + (not kjs)
                for w in row["watched"].values():
                    w["cls"] = sorted(w["cls"])
                res.append(row)
                print(f"{m['id']:40} {policy:8} rep{rep} kernels={info['kernels']} rc={info['rc']} "
                      f"to={info['timed_out']} parity {row['parity']}/{row['parity'] + row['parity_bad']} "
                      f"invariant_bad={row['invariant_bad']} inst rec->cer {row['rec_inst']}->{row['cer_inst']} "
                      f"unflagged {row['unflagged_rec']}->{row['unflagged_cer']} watched={row['watched']}",
                      flush=True)
    Path(a.out, "same_trace.json").write_text(json.dumps(res, indent=1))
    # schedule: per program and policy, how many distinct HbClock pair sets (pairs with their
    # unflagged instance counts) the REPS recordings produced
    for pid in dict.fromkeys(r["id"] for r in res):
        for pol in ("recorded", "certain"):
            sets = {json.dumps(sorted((k, v[1]) for k, v in (r.get("pairs") or {}).items()))
                    for r in res if r["id"] == pid and r["policy"] == pol}
            pairs = {json.dumps(sorted((r.get("pairs") or {}))) for r in res
                     if r["id"] == pid and r["policy"] == pol}
            print(f"schedule {pid:40} {pol:8} distinct pair sets {len(pairs)}, "
                  f"distinct (pair, unflagged) sets {len(sets)} over {a.reps} recordings")
    print(f"== {len(res)} recordings, {bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
