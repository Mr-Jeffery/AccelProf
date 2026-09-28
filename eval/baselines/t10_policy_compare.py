#!/usr/bin/env python3
"""T10: the verdicts of one set of kept dumps under two strength policies, same trace.

For every (dot dir, kernel dump) given, per policy (default: the pre-T10 `generic` and the
T10 `token`): the vector-clock view -- the dump with `hb_races` / `hb_races_sync_only`
replaced by hb_oracle.py's output under that policy (what an engine fed that policy's
sidecar writes, by the parity invariant) -- and the scalar-clock view (the engine keys
stripped), both through sync_dominance.analyze under the same policy. Prints one row per
program with RACE / SC / ORDERED counts and the pc pairs whose verdict moved.

    python eval/baselines/t10_policy_compare.py <artifact-dir>... [--json out.json]
  an artifact dir holds *.dot (any depth) and kernel_*.json (any depth; the last
  dependency_* dir wins when there are several, as the tests pick them).
"""
import argparse
import copy
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))
import hb_oracle as ho  # noqa: E402
import sync_dominance as sd  # noqa: E402


def artifacts(d):
    """(dots, kernel dumps) of a getall.sh artifact dir or a harness store dir (<id>/dots,
    <id>/vector-clock: the scalar-clock view is that dump without the engine's keys)."""
    d = Path(d)
    dots = sorted(d.rglob("*.dot"))
    deps = sorted(d.glob("**/dependency_*"))
    if (d / "vector-clock").is_dir():
        traces = sorted((d / "vector-clock").glob("kernel_*.json"))
    elif deps:
        traces = sorted(deps[-1].glob("kernel_*.json"))
    else:
        traces = sorted(d.rglob("kernel_*.json"))
    return dots, traces


def aligned(fn, dots, *args, **kw):
    for dot in dots:
        try:
            return dot, fn(dot, *args, **kw)
        except sd.AlignmentError as e:
            if str(e).startswith("TV-"):
                raise
            continue
    return None, None


TV_SEEN = {}                            # trace path -> the oracle's trace-validity message


def views(dots, trace_path, policy, tmp):
    """-> (vector-clock report, scalar-clock report) under policy. A trace-validity violation
    is re-run with YOSEMITE_HB_STRICT=0, as the engine records it and continues."""
    t = json.loads(Path(trace_path).read_text())
    try:
        dot, orc = aligned(ho.analyze, dots, trace_path, strong_ldst=policy)
    except sd.AlignmentError as e:
        TV_SEEN[str(trace_path)] = str(e)[:200]
        os.environ["YOSEMITE_HB_STRICT"] = "0"
        try:
            dot, orc = aligned(ho.analyze, dots, trace_path, strong_ldst=policy)
        finally:
            os.environ.pop("YOSEMITE_HB_STRICT", None)
    if orc is None:
        return None, None
    vc = copy.deepcopy(t)
    if "hb_races" in vc or "hb_races_sync_only" in vc:
        vc["hb_races"] = orc["races"]
        vc["hb_races_sync_only"] = orc["races_sync_only"]
    vp = Path(tmp) / f"vc_{policy}_{Path(trace_path).name}"
    vp.write_text(json.dumps(vc))
    sc = copy.deepcopy(t)
    for k in ("hb_races", "hb_races_sync_only", "coherence_profile"):
        sc.pop(k, None)
    sp = Path(tmp) / f"sc_{policy}_{Path(trace_path).name}"
    sp.write_text(json.dumps(sc))
    return (sd.analyze(dot, vp, strong_ldst=policy),
            sd.analyze(dot, sp, strong_ldst=policy))


def summarize(rep):
    out = {}
    for v in rep["verdicts"]:
        k = (min(v["current_pc"], v["ancient_pc"]), max(v["current_pc"], v["ancient_pc"]))
        out[k] = (v["verdict"], v["matrix_class"], v["conflict_class"], v["opcodes"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--policies", default="generic,token")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    pols = a.policies.split(",")
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for d in a.dirs:
            dots, traces = artifacts(d)
            name = Path(d).name
            if not dots or not traces:
                print(f"{name}: no artifacts")
                continue
            per = {p: {"vc": {}, "sc": {}} for p in pols}
            for tr in traces:
                for p in pols:
                    vr, sr = views(dots, tr, p, tmp)
                    if vr is None:
                        continue
                    per[p]["vc"].update({(tr.name,) + k: v for k, v in summarize(vr).items()})
                    per[p]["sc"].update({(tr.name,) + k: v for k, v in summarize(sr).items()})
            row = {"program": name}
            for p in pols:
                for m in ("vc", "sc"):
                    vs = [v[0] for v in per[p][m].values()]
                    row[f"{p}.{m}"] = {x: vs.count(x) for x in ("RACE", "SC", "ORDERED")}
            moved = []
            for m in ("vc", "sc"):
                a0, a1 = per[pols[0]][m], per[pols[-1]][m]
                for k in sorted(set(a0) | set(a1), key=str):
                    if a0.get(k, ("-",))[:3] != a1.get(k, ("-",))[:3]:
                        moved.append((m, k[0], hex(k[1]), hex(k[2]), a0.get(k, ("-",) * 4)[:3],
                                       a1.get(k, ("-",) * 4)[:3], a1.get(k, a0.get(k))[3]))
            row["moved"] = moved
            rows.append(row)
            cells = "  ".join(f"{p}.{m}=R{row[f'{p}.{m}']['RACE']}/S{row[f'{p}.{m}']['SC']}"
                              f"/O{row[f'{p}.{m}']['ORDERED']}" for p in pols for m in ("vc", "sc"))
            print(f"{name:52s} {cells}")
            for mv in moved:
                print(f"    {mv[0]} {mv[1]} {mv[2]}/{mv[3]}: {mv[4]} -> {mv[5]}  {mv[6]}")
            tv = sorted({v for k, v in TV_SEEN.items() if Path(k).parent.parent == Path(d)
                         or Path(d) in Path(k).parents})
            row["tv"] = tv
            for m in tv:
                print(f"    trace validity (oracle re-run with YOSEMITE_HB_STRICT=0): {m}")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1, default=list))
    return 0


if __name__ == "__main__":
    sys.exit(main())
