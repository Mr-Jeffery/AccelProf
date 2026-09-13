#!/usr/bin/env python3
"""Aggregate one program-input run into a single eval CSV row.

Pairs every kernel_N.json in a dependency dir with its aligning CFG .dot
(sync_dominance aborts on the wrong one), collects verdicts, dedups the RACE
set on (unordered pc pair, memory-space class), optionally cross-checks the C++
HB engine against the exact hb_oracle, and prints/append-writes the schema row.

Runs under the project env (needs networkx + pydot). Import path is the running
tree's python/ dir (sync_dominance, hb_oracle).
"""
import argparse
import csv
import glob
import io
import json
import os
import re
import sys
from pathlib import Path

# Column schema — every suite, every row (task spec).
COLUMNS = ["suite", "program", "variant", "bug_label", "input", "grid", "block",
           "events", "t_native", "t_trace", "t_engine", "peak_mem_mb",
           "reports_raw", "reports_dedup", "TP", "FN", "FP", "TN",
           "racecheck_verdict", "oracle_verified", "tv_violations",
           "structural", "latent", "unknown_sync", "notes"]

_LAUNCH = re.compile(r"Launching kernel .*?<<<\((\d+), (\d+), (\d+)\), "
                     r"\((\d+), (\d+), (\d+)\)>>>")


def parse_grid_block(logpath):
    """-> (grid_str, block_str) most-common launch geometry, or ('','')."""
    if not logpath or not os.path.exists(logpath):
        return "", ""
    grids, blocks = {}, {}
    for ln in Path(logpath).read_text(errors="replace").splitlines():
        m = _LAUNCH.search(ln)
        if m:
            g = "x".join(m.group(1, 2, 3))
            b = "x".join(m.group(4, 5, 6))
            grids[g] = grids.get(g, 0) + 1
            blocks[b] = blocks.get(b, 0) + 1
    top = lambda d: max(d, key=d.get) if d else ""
    gs, bs = top(grids), top(blocks)
    if len(grids) > 1:
        gs += f"(+{len(grids)-1})"
    if len(blocks) > 1:
        bs += f"(+{len(blocks)-1})"
    return gs, bs


def _dedup_key(v):
    """Dedup on (unordered pc pair, memory-space class) — never hides a distinct race."""
    a, b = sorted((v["ancient_pc"], v["current_pc"]))
    space = v["space"].split("/")[0]  # location class
    return (a, b, space)


def _race_sig(races):
    """Comparable signature of an hb race set (engine vs oracle)."""
    out = []
    for r in races or []:
        pcs = tuple(sorted(p for p in (r.get("a_pc"), r.get("b_pc")) if p is not None))
        out.append((r.get("addr"), pcs, r.get("kind")))
    return sorted(out)


def emit_row(args):
    """args: namespace/obj with the CLI fields below. Builds one row, prints a
    summary line, and (if args.csv) appends it. Usable from driver.py too."""
    g = lambda k, d="": getattr(args, k, d)
    args.oracle = bool(g("oracle", False))
    args.oracle_max_events = g("oracle_max_events", 300000)
    args.expect_pcs = g("expect_pcs", "")
    args.racecheck = g("racecheck", "")
    args.detail = g("detail", "")
    args.csv = g("csv", "")
    args.log = g("log", "")
    for k in ("variant", "label", "input", "t_native", "t_trace", "t_engine", "peak_kb"):
        setattr(args, k, g(k, ""))
    sys.path.insert(0, args.python_dir)
    import functools
    import sync_dominance as sd
    # Many-kernel apps pair each kernel JSON against every CFG dot; pydot parsing
    # dominates. parse_dot is read-only wrt callers, so memoize it (parse each dot
    # once per process instead of once per kernel).
    if not getattr(sd.parse_dot, "__wrapped__", None):
        sd.parse_dot = functools.lru_cache(maxsize=None)(sd.parse_dot)
    try:
        import hb_oracle
    except Exception:
        hb_oracle = None

    dots = sorted(glob.glob(os.path.join(args.cubindir, "*.dot")))
    kjsons = sorted(glob.glob(os.path.join(args.depdir, "kernel_*.json")),
                    key=lambda p: int(re.search(r"kernel_(\d+)", p).group(1)))

    events = 0
    verdicts = []
    unknown_sync = 0
    kernels_paired = 0
    kernels_unpaired = 0
    oracle_states = []   # per-kernel: "yes" | "engine-only" | "mismatch" | "no-hb"
    notes = []

    for kj in kjsons:
        d = json.loads(Path(kj).read_text())
        n_ev = len(d.get("hb_events", []))
        events += n_ev
        hb_races = d.get("hb_races")

        rep, used_dot = None, None
        for dot in dots:
            try:
                rep = sd.analyze(dot, kj,
                                 assume_warp_lockstep=bool(g("assume_warp_lockstep", False)))
                used_dot = dot
                break
            except sd.AlignmentError:
                continue
            except Exception as e:            # malformed dot stub etc.
                continue
        if rep is None:
            kernels_unpaired += 1
            continue
        kernels_paired += 1
        unknown_sync += rep["diagnostics"]["unknown_sync_count"]
        verdicts.extend(rep["verdicts"])

        # oracle cross-check (engine hb_races vs exact VC oracle over the same dump)
        if g("no_engine", False):
            # trace-only mode: the dump carries an empty hb_races (engine skipped);
            # verdicts are the static leg's, there is nothing to cross-check.
            oracle_states.append("no-engine")
        elif hb_races is None:
            oracle_states.append("no-hb")
        elif not args.oracle or hb_oracle is None:
            oracle_states.append("engine-only")
        elif n_ev > args.oracle_max_events:
            oracle_states.append("engine-only")
        else:
            try:
                orc = hb_oracle.analyze(used_dot, kj)
                oracle_states.append("yes" if _race_sig(orc["races"]) ==
                                     _race_sig(hb_races) else "mismatch")
            except Exception as e:
                oracle_states.append("engine-only")
                notes.append(f"oracle-err:{type(e).__name__}")

    races = [v for v in verdicts if v["verdict"] == "RACE"]
    reports_raw = len(races)
    dedup = {}
    for v in races:
        dedup.setdefault(_dedup_key(v), v)
    reports_dedup = len(dedup)
    structural = sum(v.get("hb_class") == "structural" for v in verdicts)
    latent = sum(v.get("hb_class") == "latent" for v in verdicts)
    tv_violations = sum(v.get("hb_class") == "model_bug" for v in verdicts)
    benign = sum(v.get("hb_class") == "benign" for v in verdicts)
    warp_po = sum(v.get("hb_class") == "warp-po-ordered" for v in verdicts)
    if benign:
        notes.append(f"benign={benign}")
    if warp_po:
        notes.append(f"warp-po-ordered={warp_po}(assumes-lockstep)")

    # oracle_verified summary across kernels
    if oracle_states and all(s == "no-engine" for s in oracle_states):
        oracle_verified = "no-engine"
    elif all(s in ("yes", "no-hb") for s in oracle_states) and "yes" in oracle_states:
        oracle_verified = "yes"
    elif "mismatch" in oracle_states:
        oracle_verified = "MISMATCH"
    elif oracle_states and all(s == "no-hb" for s in oracle_states):
        oracle_verified = "no-hb"
    else:
        oracle_verified = "engine-only"

    # provisional confusion cell from the label (triage refines).
    # A racy program is caught by ANY RACE verdict (structural OR latent) matching
    # the planted PCs — this is the tool's own detection criterion (the CI asserts
    # verdict==RACE >= 1). structural vs latent is the classification refinement,
    # kept as its own columns; fence-omission races surface as latent because the
    # dynamic engine has no MEMBAR patch point (a documented tool boundary).
    expect = {int(x, 16) for x in args.expect_pcs.split(",") if x.strip()}

    def matches_expect(v):
        if not expect:
            return True
        return v["ancient_pc"] in expect or v["current_pc"] in expect

    race_hits = [v for v in races if matches_expect(v)]
    TP = FN = FP = TN = ""
    if args.label == "racy":
        TP, FN = (1, 0) if race_hits else (0, 1)
        if race_hits and structural == 0:
            notes.append("caught-latent-only")
    elif args.label in ("race-free", "racefree"):
        FP, TN = (1, 0) if reports_raw > 0 else (0, 1)

    if kernels_unpaired:
        notes.append(f"{kernels_unpaired}-kernel(s)-unpaired-to-CFG")
    if unknown_sync:
        notes.append(f"unknown_sync={unknown_sync}")
    if g("notes_extra", ""):
        notes.append(args.notes_extra)

    grid, block = parse_grid_block(args.log)
    peak_mb = ""
    if args.peak_kb:
        try:
            peak_mb = round(int(args.peak_kb) / 1024.0, 1)
        except ValueError:
            peak_mb = args.peak_kb

    row = {
        "suite": args.suite, "program": args.program, "variant": args.variant,
        "bug_label": args.label, "input": args.input, "grid": grid, "block": block,
        "events": events, "t_native": args.t_native, "t_trace": args.t_trace,
        "t_engine": args.t_engine, "peak_mem_mb": peak_mb,
        "reports_raw": reports_raw, "reports_dedup": reports_dedup,
        "TP": TP, "FN": FN, "FP": FP, "TN": TN,
        "racecheck_verdict": args.racecheck, "oracle_verified": oracle_verified,
        "tv_violations": tv_violations, "structural": structural, "latent": latent,
        "unknown_sync": unknown_sync, "notes": ";".join(notes),
    }

    # stdout: the row as key=val (human), plus append CSV if requested
    print(" | ".join(f"{k}={row[k]}" for k in
                      ("program", "variant", "bug_label", "events", "reports_raw",
                       "reports_dedup", "structural", "latent", "tv_violations",
                       "oracle_verified", "TP", "FN", "FP", "TN")))

    if args.csv:
        newfile = not os.path.exists(args.csv) or os.path.getsize(args.csv) == 0
        with open(args.csv, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            if newfile:
                w.writeheader()
            w.writerow(row)

    if args.detail:
        Path(args.detail).write_text(json.dumps({
            "row": row, "dedup_reports": [dedup[k] for k in dedup],
            "all_races": races, "oracle_states": oracle_states,
        }, indent=2) + "\n")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--python-dir", required=True)
    ap.add_argument("--depdir", required=True)
    ap.add_argument("--cubindir", required=True)
    ap.add_argument("--log", default="")
    ap.add_argument("--suite", required=True)
    ap.add_argument("--program", required=True)
    ap.add_argument("--variant", default="")
    ap.add_argument("--label", default="")
    ap.add_argument("--input", default="")
    ap.add_argument("--t-native", dest="t_native", default="")
    ap.add_argument("--t-trace", dest="t_trace", default="")
    ap.add_argument("--t-engine", dest="t_engine", default="")
    ap.add_argument("--peak-kb", dest="peak_kb", default="")
    ap.add_argument("--racecheck", default="")
    ap.add_argument("--oracle", action="store_true")
    ap.add_argument("--oracle-max-events", dest="oracle_max_events", type=int, default=300000)
    ap.add_argument("--expect-pcs", dest="expect_pcs", default="")
    ap.add_argument("--csv", default="")
    ap.add_argument("--detail", default="")
    emit_row(ap.parse_args())


if __name__ == "__main__":
    main()
