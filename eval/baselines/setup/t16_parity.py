#!/usr/bin/env python3
"""T16 (eval/CERTAIN_CLOCK.md): HbClock == specification under both chain-edge policies, on
binaries recorded twice with the worktree runtime -- YOSEMITE_HB_GATE_POLICY=recorded and
=certain -- through getall.sh (CFG dots, sidecar, YOSEMITE_HB_TRACE=1 vector-clock run).
Per kernel dump:
  1. HbClock's hb_races (parity key: pc pair, kind, class, space, dist, async, count,
     a2_uncertain) == hb_oracle.py's under the dump's own policy, and hb_races_sync_only equal;
  2. the dump's hb_gate_policy and every record's gate_policy name the policy it ran under;
  3. HbClock's hb_chain counters == the oracle's summary.chain;
  4. on the RECORDED dump, the oracle under `certain` reports a superset of the oracle under
     `recorded` (Rep_certain >= Rep_recorded at the aggregate key, counts included) and the same
     sync pairs -- the invariant of the brief, on real traces.
Usage (from the worktree root, on a GPU node, ACCEL_PROF_HOME = the worktree via getall.sh):
    .env/bin/python eval/baselines/setup/t16_parity.py --out <dir> <binary>...
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python"))
import hb_oracle  # noqa: E402
import sync_dominance as sd  # noqa: E402

KEY = lambda r: (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
                 r.get("async"), r.get("count"), r.get("a2_uncertain"))
AGG = lambda r: (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
                 r.get("async"))


def record(binary, out, policy):
    d = Path(out) / Path(binary).name / policy
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    exe = d / Path(binary).name
    shutil.copy2(binary, exe)
    env = dict(os.environ, YOSEMITE_HB_GATE_POLICY=policy)
    for k in ("YOSEMITE_HB_MODE", "YOSEMITE_HB_NO_ENGINE", "YOSEMITE_HB_DUMP", "YOSEMITE_HB_STATS"):
        env.pop(k, None)
    r = subprocess.run(["bash", str(ROOT / "getall.sh"), str(exe)], cwd=ROOT, env=env,
                       capture_output=True, timeout=1800)
    dots = sorted((d / f"{exe.name}_extracted_cubins").glob("*.dot"))
    deps = sorted(d.glob(f"dependency_{exe.name}_*"))
    traces = sorted(deps[-1].glob("kernel_*.json")) if deps else []
    return dots, traces, r.returncode


def oracle(dots, trace, **kw):
    for dot in dots:
        try:
            return hb_oracle.analyze(str(dot), str(trace), **kw)
        except sd.AlignmentError:
            continue
    return None


def agg(races):
    c = Counter()
    for r in races:
        c[AGG(r)] += r.get("count", 1)
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("binaries", nargs="+")
    a = ap.parse_args()
    bad = 0
    rows = []
    for b in a.binaries:
        dumps = {}
        for policy in ("recorded", "certain"):
            dots, traces, rc = record(b, a.out, policy)
            if not traces:
                print(f"{Path(b).name} {policy}: NO TRACE (rc={rc})")
                bad += 1
                continue
            for tr in traces:
                t = json.loads(tr.read_text())
                kn = t["kernel"]["kernel_name"].split("(")[0]
                dumps.setdefault(kn, {})[policy] = (dots, tr, t)
        for kn, per in sorted(dumps.items()):
            for policy, (dots, tr, t) in sorted(per.items()):
                rep = oracle(dots, tr)      # the dump's own policy (hb_gate_policy)
                if rep is None:
                    print(f"{Path(b).name} {kn} {policy}: no CFG aligns"); bad += 1; continue
                ok_pol = t.get("hb_gate_policy") == policy == rep["gate_policy"] and \
                    all(r.get("gate_policy") == policy for r in t.get("hb_races", []))
                ok_races = {KEY(r) for r in t.get("hb_races", [])} == {KEY(r) for r in rep["races"]}
                ok_sync = t.get("hb_races_sync_only") == rep["races_sync_only"]
                ok_chain = t.get("hb_chain") == rep["chain"]
                ok = ok_pol and ok_races and ok_sync and ok_chain
                bad += not ok
                rows.append((Path(b).name, kn, policy, len(t.get("hb_races", [])),
                             sum(r["count"] for r in t.get("hb_races", [])),
                             sum(r["a2_uncertain"] for r in t.get("hb_races", [])),
                             t.get("hb_chain"), "ok" if ok else
                             f"MISMATCH pol={ok_pol} races={ok_races} sync={ok_sync} chain={ok_chain}"))
            if "recorded" in per:            # 4. the invariant on the recorded dump
                dots, tr, t = per["recorded"]
                rec = oracle(dots, tr, gate_policy="recorded")
                cer = oracle(dots, tr, gate_policy="certain")
                if rec is None or cer is None:
                    continue
                ar, ac = agg(rec["races"]), agg(cer["races"])
                sup = all(ac.get(k, 0) >= n for k, n in ar.items()) and \
                    rec["races_sync_only"] == cer["races_sync_only"]
                unf_r = sum(r["count"] - r["a2_uncertain"] for r in rec["races"])
                unf_c = sum(r["count"] - r["a2_uncertain"] for r in cer["races"])
                bad += not sup
                rows.append((Path(b).name, kn, "rec->cert", f"{sum(ar.values())}->{sum(ac.values())}",
                             f"unflagged {unf_r}->{unf_c}", "", cer["chain"],
                             "superset ok" if sup else "INVARIANT VIOLATED"))
    print(f"{'binary':44} {'kernel':28} {'policy':9} {'rec':>5} {'inst':>7} {'a2':>7}  chain / status")
    for r in rows:
        print(f"{r[0][:44]:44} {r[1][:28]:28} {r[2]:9} {str(r[3]):>5} {str(r[4]):>7} {str(r[5]):>7}  {r[6]} {r[7]}")
    print(f"== {len(rows)} rows, {bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
