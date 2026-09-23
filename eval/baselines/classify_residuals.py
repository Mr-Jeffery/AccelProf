#!/usr/bin/env python3
"""Root-cause the residual cuVein ERROR/TIMEOUT programs -> baselines-diagnose.csv.

Input: the diagnostic re-run rows (parallel.py run --tag resid, 20-minute floor,
native rc/stderr + accelprof stderr + dump size captured in `notes`) merged into
eval/results/baselines-cuvein.csv, plus the manifest. For every id in
setup/residual_ids.txt and every mode, the best row of the *diagnostic* shard
(baselines-cuvein-shardresid*.csv) is classified:

  resolved          the re-run produced a verdict (RACE/CLEAN) -> not a defect
  app-native-fail   the program exits non-zero WITHOUT accelprof (native_rc!=0):
                    the app/corpus/args are at fault, not the collector
  trace-volume      TIMEOUT while the raw dump kept growing (dump_mb > 0): the
                    collector was still writing trace; the program's access count
                    exceeds what fits in the 20-min budget (inherent to tracing)
  collector-hang    TIMEOUT with an (almost) empty dump and modest RSS: stalled
  collector-memory  TIMEOUT with an empty dump but >=32 GB RSS: the collector
                    holds the whole trace in memory (nothing written before the
                    end) and cannot finish in 20 min: attributable to cuVein
  collector-oom     native rc==0 but the accelprof child was SIGKILLed (bash
                    "Killed", rc 137) -- the collector's memory grows with the
                    trace and is killed by the node: attributable to cuVein
  engine-hang       vector-clock-mode TIMEOUT with an empty dump while scalar-clock of
                    the SAME program resolved -- attributable to the cuVein
                    engine (not the tracer)
  collector-fail    native rc==0 but accelprof exits non-zero / no kernel JSON:
                    attributable to the cuVein collector
  trace-disk-full   the raw dependency_* dump filled the node-local scratch disk
                    ("No space left on device"): attributable to cuVein (dump
                    size is unbounded)
  analysis-timeout  trace collected but the offline sync_dominance analysis exceeded
                    the --analysis-timeout cap (notes carry dump_mb/nkernels)
  analysis-oom      the diagnostic shard log shows the *Python* runner itself
                    was Killed (no row written): the collector finished but the
                    sync_dominance analysis of the trace exhausted memory --
                    attributable to cuVein's scalar-clock analysis path
  no-diag-run       the diagnostic shard has no row for it (still running)

Writes eval/results/baselines-diagnose.csv (id, pset, program, mode, verdict,
cause, native_rc, timeout_s, dump_mb, evidence). make_tables.py renders it as
BASELINES.md section 1b. No GPU needed.
"""
import csv
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(HERE))
RES = f"{APH}/eval/results"

import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "python"))
import hb_modes  # noqa: E402  (vector-clock / scalar-clock; legacy names accepted with a warning)
VC, SC = hb_modes.VECTOR_CLOCK, hb_modes.SCALAR_CLOCK
OTHER = {VC: SC, SC: VC}
PRI = {"RACE": 3, "CLEAN": 2, "TIMEOUT": 1, "ERROR": 0}
_KV = re.compile(r"(native_rc|dump_mb|timeout|events)=([\d.]+)")


def _kv(notes):
    return {k: v for k, v in _KV.findall(notes or "")}


def _field(notes, key):
    m = re.search(rf"{key}=(.*?)(?:;(?:native_rc|native_err|err|dump_mb|timeout|events)=|$)", notes or "")
    return m.group(1).strip() if m else ""


def classify(r, manifest_label, other_mode_row=None):
    kv = _kv(r["notes"])
    v = r["verdict"]
    nrc = int(kv["native_rc"]) if "native_rc" in kv else 0
    dump = float(kv.get("dump_mb", 0) or 0)
    if v in ("RACE", "CLEAN"):
        return "resolved"
    if nrc != 0:
        # a native exec failure while the SAME program's tool run in the other
        # mode reached a verdict is a launch artefact of that node, not the app
        if other_mode_row and other_mode_row["verdict"] in ("RACE", "CLEAN"):
            pass
        else:
            return "app-native-fail"
    if "analysis-timeout=" in (r["notes"] or ""):
        return "analysis-timeout"   # trace collected; offline analysis exceeded its cap
    if "No space left on device" in (r["notes"] or ""):
        return "trace-disk-full"
    if "JSONDecodeError" in (r["notes"] or ""):
        return "trace-volume"      # dump truncated by the timeout kill, then parsed
    if "Killed" in (r["notes"] or "") or r.get("rc") in ("137", "-9"):
        return "collector-oom"
    try:
        _peak_gb = float(r.get("peak_mb") or 0) / 1024.0
    except ValueError:
        _peak_gb = 0.0
    if v == "ERROR" and _peak_gb >= 32:
        return "collector-oom"      # accelprof child died after growing to >=32 GB
    try:
        peak_gb = float(r.get("peak_mb") or 0) / 1024.0
    except ValueError:
        peak_gb = 0.0
    if v == "TIMEOUT":
        if dump > 1.0:
            return "trace-volume"
        if peak_gb >= 32:
            return "collector-memory"
        if (r["mode"] == VC and other_mode_row
                and other_mode_row["verdict"] in ("RACE", "CLEAN")):
            return "engine-hang"
        return "collector-hang"
    return "collector-fail"


def main():
    man = {r["id"]: r for r in csv.DictReader(open(f"{HERE}/manifest.csv", newline=""))}
    ids = [l.strip() for l in open(f"{HERE}/setup/residual_ids.txt") if l.strip()]
    best = {}
    # the P9 sweep rows (tag p9) were produced under the same 20-min-floor protocol
    # as the diagnostic shards, so they count as diagnostic input for P9 ids
    for path in sorted(glob.glob(f"{RES}/baselines-cuvein-shardresid*.csv")
                       + glob.glob(f"{RES}/baselines-cuvein-shardp9*.csv")):
        for r in csv.DictReader(open(path, newline="")):
            r["mode"] = hb_modes.canon(r["mode"], path)
            # a runner-level exception row carries no mode: it applies to both
            for mode in ((r["mode"],) if r["mode"] else hb_modes.MODES):
                k = (r["id"], mode)
                rr = dict(r, mode=mode)
                # ties go to the LATER shard file (a re-run supersedes an older attempt)
                if k not in best or PRI[r["verdict"]] >= PRI[best[k]["verdict"]]:
                    best[k] = rr
    # diagnostic shard logs: an id whose runner process was itself Killed leaves
    # no row -> analysis-oom (the collector finished; the Python analysis died)
    killed = {}
    for lg in glob.glob(f"{HERE}/setup/build_logs/diag-*.log") + glob.glob(f"{HERE}/setup/build_logs/p7fix*.log"):
        txt = open(lg, errors="replace").read()
        mm = re.search(r"\[run \d+/\d+\] (\S+)", txt)
        if mm and "Killed" in txt and "run: " not in txt:
            killed[mm.group(1)] = re.search(r"(Killed[^\n]{0,80})", txt).group(1)
    # last-resort input: the main sweep's own rows (baselines-cuvein.csv, 120 s floor).
    # Used only for a residual id the diagnostic pass never produced a row for (its
    # shard was cancelled/hung). The stable, floor-independent causes are honoured
    # (a hang that also hung for ~50 min by hand, an OOM, a growing dump, a native
    # fail, or an actual verdict); the evidence field flags the weaker provenance.
    base = {}
    bpath = f"{RES}/baselines-cuvein.csv"
    if os.path.exists(bpath):
        for r in csv.DictReader(open(bpath, newline="")):
            r["mode"] = hb_modes.canon(r["mode"], bpath)
            k = (r["id"], r["mode"])
            if r["mode"] and (k not in base or PRI[r["verdict"]] >= PRI[base[k]["verdict"]]):
                base[k] = r
    rows = []
    for i in ids:
        m = man.get(i, {})
        for mode in hb_modes.MODES:
            r = best.get((i, mode))
            if not r:
                if i in killed:
                    rows.append(dict(id=i, pset=m.get("pset", ""), program=m.get("program", i),
                                     mode=mode, verdict="", cause="analysis-oom", native_rc="",
                                     timeout_s="", dump_mb="", peak_mb="", wall_s="", native_wall_s="",
                                     evidence=killed.get(i, "")[:120]))
                    continue
                br = base.get((i, mode))
                if br:
                    kv = _kv(br["notes"])
                    cause = classify(br, m.get("label", ""), base.get((i, OTHER[mode])))
                    rows.append(dict(id=i, pset=br["pset"], program=br["program"], mode=mode,
                                     verdict=br["verdict"], cause=cause,
                                     native_rc=kv.get("native_rc", "0"), timeout_s=kv.get("timeout", ""),
                                     dump_mb=kv.get("dump_mb", ""), peak_mb=br.get("peak_mb", ""),
                                     wall_s=br["wall_s"], native_wall_s=br["native_wall_s"],
                                     evidence="from the 120 s main sweep (diagnostic shard produced no row); "
                                              + (br["notes"] or "")[:120]))
                    continue
                rows.append(dict(id=i, pset=m.get("pset", ""), program=m.get("program", i),
                                 mode=mode, verdict="", cause="no-diag-run", native_rc="",
                                 timeout_s="", dump_mb="", peak_mb="", wall_s="", native_wall_s="",
                                 evidence=""))
                continue
            kv = _kv(r["notes"])
            other = best.get((i, OTHER[mode]))
            cause = classify(r, m.get("label", ""), other)
            if i in killed and cause in ("app-native-fail", "collector-fail"):
                # the later re-run (inputs fixed) got past the app and the runner
                # was then Killed in analysis: that supersedes the older row
                cause = "analysis-oom"
            ev = _field(r["notes"], "native_err") if cause == "app-native-fail" else _field(r["notes"], "err")
            if cause == "trace-disk-full":
                ev = r["notes"][:200]
            if "JSONDecodeError" in (r["notes"] or ""):
                ev = "timed out; dump truncated by the kill (JSONDecodeError on the partial kernel JSON)"
            if cause == "analysis-oom":
                ev = killed.get(i, "")[:120]
            if cause == "resolved":
                ev = f"events={kv.get('events', '')}"
            rows.append(dict(id=i, pset=r["pset"], program=r["program"], mode=mode,
                             verdict=r["verdict"], cause=cause,
                             native_rc=kv.get("native_rc", "0"),
                             timeout_s=kv.get("timeout", ""), dump_mb=kv.get("dump_mb", ""),
                             peak_mb=r.get("peak_mb", ""),
                             wall_s=r["wall_s"], native_wall_s=r["native_wall_s"],
                             evidence=ev[-220:]))
    out = f"{RES}/baselines-diagnose.csv"
    fields = ["id", "pset", "program", "mode", "verdict", "cause", "native_rc",
              "timeout_s", "dump_mb", "peak_mb", "wall_s", "native_wall_s", "evidence"]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    c = Counter((r["mode"], r["cause"]) for r in rows)
    print(f"{len(rows)} rows -> {out}")
    for k in sorted(c):
        print(f"  {k[0]:11s} {k[1]:17s} {c[k]}")


if __name__ == "__main__":
    main()
