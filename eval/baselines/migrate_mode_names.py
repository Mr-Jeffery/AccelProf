#!/usr/bin/env python3
"""T8 converter: rewrite every persisted cuVein mode name to the T8 vocabulary.

    engine      -> vector-clock
    trace-only  -> scalar-clock   (and the no-engine spellings)

Dry-run by default (prints what it would do); --apply executes. Idempotent: running
it again finds nothing to do. One log line per change, a summary at the end, and the
whole log written to --log. What it touches:

  CSVs under --results (default eval/results, recursive):
    mode              engine / trace-only                 -> vector-clock / scalar-clock
    oracle_verified   no-engine                           -> scalar-clock
    notes             mode=trace-only(no-engine)          -> mode=scalar-clock
                      no-engine-output(rc=N)              -> no-kernel-json(rc=N)
                        (it meant "the analyzed run wrote no kernel JSON", in either
                        mode -- the name parallel.py already uses)
                      keep_reason tokens engine:X / trace-only:X
    tool_a, tool_b, ptx_871_match, suite_label_match      cuvein/engine, cuvein/trace-only
    file names        E*-noengine.csv                     -> E*-scalar-clock.csv
  Other occurrences (quoted OS error text with a path such as
  '.../P7-nbody-cuda/trace-only/kernel_18.json') are historical messages about
  directories that no longer exist; they are left as they are and counted.

  Kept-trace stores (--store, repeatable; a store = directory of <id>/meta.json):
    <id>/engine/ <id>/trace-only/                         -> vector-clock/ scalar-clock/
    <id>/engine-partial-rep<k>/ ...                       -> vector-clock-partial-rep<k>/ ...
    <id>/logs/engine_rep<k>.txt ...                       -> logs/vector-clock_rep<k>.txt ...
    <id>/meta.json   modes keys, modes.*.partial_dump, keep_reason tokens
    <id>/<mode>-partial-rep<k>/PARTIAL  "mode" field
    STORE_INFO.json  modes list

  Confirm directories (--confirm, repeatable):
    <id>__cuvein__engine.json                             -> <id>__cuvein__vector-clock.json
    the "mode" field inside

A target that already exists is never overwritten: the pair is logged as CONFLICT and
left for a human. BeeGFS stores exist only on compute nodes -- run there (srun/sbatch).

--reverse undoes the store and confirm-directory part (directory, log and confirm file
names, meta.json / PARTIAL / STORE_INFO.json / confirm "mode" fields) for a rollback;
it refuses to touch CSVs, which are git-tracked (roll those back with git).

  .env/bin/python eval/baselines/migrate_mode_names.py \
      --store 'eval/baselines/traces_keep*' --confirm 'eval/baselines/confirm*' \
      --log eval/baselines/setup/migrate_mode_names.home.log            # dry run
  ... --apply
"""
import argparse
import csv
import glob
import json
import os
import re
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(HERE))

MODE_MAP = {"engine": "vector-clock", "trace-only": "scalar-clock"}
OV_MAP = {"no-engine": "scalar-clock"}
TOOL_COLS = ("tool_a", "tool_b", "ptx_871_match", "suite_label_match")
NOTE_SUBS = [
    (re.compile(r"mode=trace-only\(no-engine\)"), "mode=scalar-clock"),
    # driver.py wrote "no-engine-output(rc=N)" when the ANALYZED run (either mode) left
    # no kernel JSON -- 16 of its 24 rows are in vector-clock files, so the T8 brief's
    # "scalar-clock-output" would mislabel them; parallel.py calls the same condition
    # "no-kernel-json(rc=N)".
    (re.compile(r"\bno-engine-output\("), "no-kernel-json("),
    (re.compile(r"(?<![\w/-])engine:(?=(FP|FN|ERROR|TIMEOUT)\b)"), "vector-clock:"),
    (re.compile(r"(?<![\w/-])trace-only:(?=(FP|FN|ERROR|TIMEOUT)\b)"), "scalar-clock:"),
]
TOOL_SUBS = [(re.compile(r"\bcuvein/engine\b"), "cuvein/vector-clock"),
             (re.compile(r"\bcuvein/trace-only\b"), "cuvein/scalar-clock")]
LEFT_RE = re.compile(r"trace-only|no-engine|noengine")
KEEP_SUBS = NOTE_SUBS[2:]


class Log:
    def __init__(self, apply):
        self.apply = apply
        self.lines = []
        self.count = Counter()

    def __call__(self, kind, msg):
        self.count[kind] += 1
        line = f"{'APPLY' if self.apply else 'DRY'} {kind}: {msg}"
        self.lines.append(line)
        print(line, flush=True)


def _sub_all(subs, s):
    for rx, rep in subs:
        s = rx.sub(rep, s)
    return s


# ---------------------------------------------------------------- CSVs
def migrate_csv(path, log):
    with open(path, newline="") as fh:
        rd = csv.reader(fh)
        try:
            header = next(rd)
        except StopIteration:
            return
        rows = list(rd)
    idx = {c: i for i, c in enumerate(header)}
    changed = Counter()
    left = 0
    for row in rows:
        for c, i in idx.items():
            if i >= len(row):
                continue
            v = row[i]
            nv = v
            if c == "mode":
                nv = MODE_MAP.get(v, v)
            elif c == "oracle_verified":
                nv = OV_MAP.get(v, v)
            elif c == "notes" or c == "evidence" or c == "keep_reason":
                nv = _sub_all(NOTE_SUBS, v)
            elif c in TOOL_COLS:
                nv = _sub_all(TOOL_SUBS, v)
            if nv != v:
                row[i] = nv
                changed[c] += 1
            if LEFT_RE.search(row[i]):
                left += 1
    if changed:
        log("csv", f"{path}: " + ", ".join(f"{c}={n}" for c, n in sorted(changed.items()))
            + (f" (left {left} free-text occurrence(s) in quoted error messages)" if left else ""))
        if log.apply:
            tmp = path + ".t8tmp"
            with open(tmp, "w", newline="") as fh:
                w = csv.writer(fh, lineterminator=_line_end(path))
                w.writerow(header)
                w.writerows(rows)
            os.replace(tmp, path)
    elif left:
        log("csv-left", f"{path}: {left} free-text occurrence(s) left (quoted error messages)")


def _line_end(path):
    with open(path, "rb") as fh:
        head = fh.read(65536)
    return "\r\n" if b"\r\n" in head else "\n"


def rename_csv_files(root, log):
    for path in sorted(glob.glob(f"{root}/**/*noengine*.csv", recursive=True)):
        new = path.replace("-noengine", "-scalar-clock").replace("_noengine", "_scalar-clock")
        _rename(path, new, log, "rename-file")


# ---------------------------------------------------------------- stores
def _rename(src, dst, log, kind):
    if not os.path.lexists(src) or src == dst:
        return False
    if os.path.lexists(dst):
        log("CONFLICT", f"{src} -> {dst}: target exists, left as is")
        return False
    log(kind, f"{src} -> {dst}")
    if log.apply:
        os.rename(src, dst)
    return True


def _rewrite_json(path, fn, log, kind):
    try:
        with open(path) as fh:
            txt = fh.read()
        d = json.loads(txt)
    except (OSError, ValueError) as e:
        log("SKIP", f"{path}: unreadable ({type(e).__name__})")
        return
    what = fn(d)
    if what:
        log(kind, f"{path}: {what}")
        if log.apply:
            tmp = path + ".t8tmp"
            with open(tmp, "w") as fh:
                fh.write(json.dumps(d, indent=2 if txt.lstrip().startswith("{\n") else None)
                         + ("\n" if txt.endswith("\n") else ""))
            os.replace(tmp, path)


def set_reverse():
    """--reverse: map the T8 names back (stores and confirm dirs only)."""
    global MODE_MAP, KEEP_SUBS
    MODE_MAP = {v: k for k, v in MODE_MAP.items()}            # T8 name -> legacy name
    KEEP_SUBS = [(re.compile(rf"(?<![\w/-]){re.escape(t8)}:(?=(FP|FN|ERROR|TIMEOUT)\b)"), f"{legacy}:")
                 for t8, legacy in MODE_MAP.items()]


def _fix_meta(d):
    what = []
    modes = d.get("modes")
    if isinstance(modes, dict) and any(k in MODE_MAP for k in modes):
        d["modes"] = {MODE_MAP.get(k, k): v for k, v in modes.items()}
        what.append("modes keys")
    for v in (d.get("modes") or {}).values():
        pd = v.get("partial_dump") if isinstance(v, dict) else None
        if pd:
            for old, new in MODE_MAP.items():
                if pd.startswith(old + "-partial-rep"):
                    v["partial_dump"] = new + pd[len(old):]
                    what.append("partial_dump")
    kr = d.get("keep_reason")
    if isinstance(kr, str):
        nkr = _sub_all(KEEP_SUBS, kr)
        if nkr != kr:
            d["keep_reason"] = nkr
            what.append("keep_reason")
    return ", ".join(what)


def _fix_partial(d):
    if d.get("mode") in MODE_MAP:
        d["mode"] = MODE_MAP[d["mode"]]
        return "mode"
    return ""


def _fix_store_info(d):
    m = d.get("modes")
    if isinstance(m, list) and any(x in MODE_MAP for x in m):
        d["modes"] = [MODE_MAP.get(x, x) for x in m]
        return "modes list"
    return ""


def migrate_store(store, log):
    if os.path.exists(f"{store}/STORE_INFO.json"):
        _rewrite_json(f"{store}/STORE_INFO.json", _fix_store_info, log, "store-info")
    n = 0
    for meta in sorted(glob.glob(f"{store}/*/meta.json")):
        idir = os.path.dirname(meta)
        n += 1
        for old, new in MODE_MAP.items():
            _rename(f"{idir}/{old}", f"{idir}/{new}", log, "rename-dir")
            for pd in sorted(glob.glob(f"{idir}/{old}-partial-rep*")):
                _rename(pd, f"{idir}/{new}{os.path.basename(pd)[len(old):]}", log, "rename-dir")
            for lg in sorted(glob.glob(f"{idir}/logs/{old}_rep*.txt")):
                _rename(lg, f"{idir}/logs/{new}{os.path.basename(lg)[len(old):]}", log, "rename-log")
        # PARTIAL markers (after the renames when applying; before, in a dry run)
        for new in MODE_MAP.values():
            for pm in glob.glob(f"{idir}/{new}-partial-rep*/PARTIAL"):
                _rewrite_json(pm, _fix_partial, log, "partial-marker")
        if not log.apply:
            for old in MODE_MAP:
                for pm in glob.glob(f"{idir}/{old}-partial-rep*/PARTIAL"):
                    _rewrite_json(pm, _fix_partial, log, "partial-marker")
        _rewrite_json(meta, _fix_meta, log, "meta")
    return n


def migrate_confirm(cdir, log):
    for f in sorted(glob.glob(f"{cdir}/*__cuvein__*.json")):
        base = os.path.basename(f)
        path = f
        for old, nm in MODE_MAP.items():
            suffix = f"__cuvein__{old}.json"
            if base.endswith(suffix):
                new = f"{cdir}/{base[:-len(suffix)]}__cuvein__{nm}.json"
                if not _rename(f, new, log, "rename-confirm"):
                    path = None           # conflict: logged, left for a human
                elif log.apply:
                    path = new
        if path:
            _rewrite_json(path, _fix_partial, log, "confirm-mode")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--results", action="append", default=[],
                    help="CSV root(s) (default eval/results); '' to skip")
    ap.add_argument("--store", action="append", default=[], help="kept-trace store glob(s)")
    ap.add_argument("--confirm", action="append", default=[], help="confirm dir glob(s)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--reverse", action="store_true",
                    help="roll back stores/confirm dirs to the pre-T8 names (needs --results '')")
    ap.add_argument("--log", default="")
    a = ap.parse_args()
    if a.reverse:
        if a.results != [""]:
            ap.error("--reverse only rolls back stores and confirm dirs: pass --results '' "
                     "(CSVs are git-tracked; roll them back with git)")
        set_reverse()
    log = Log(a.apply)
    t0 = time.time()
    roots = [r for r in (a.results or [f"{APH}/eval/results"]) if r]
    for root in roots:
        for path in sorted(glob.glob(f"{root}/**/*.csv", recursive=True)):
            migrate_csv(path, log)
        rename_csv_files(root, log)
    nstores = nprog = 0
    for pat in a.store:
        for s in sorted(glob.glob(pat)):
            if os.path.isdir(s):
                nstores += 1
                nprog += migrate_store(s.rstrip("/"), log)
    for pat in a.confirm:
        for c in sorted(glob.glob(pat)):
            if os.path.isdir(c):
                migrate_confirm(c.rstrip("/"), log)
    summary = (f"{'APPLIED' if a.apply else 'DRY RUN'}{' REVERSE' if a.reverse else ''} {time.strftime('%Y-%m-%d %H:%M:%S')} on "
               f"{os.uname().nodename} in {time.time() - t0:.0f}s: results roots {roots}, "
               f"{nstores} store(s) / {nprog} program dir(s), confirm dirs {a.confirm}; "
               + ", ".join(f"{k}={v}" for k, v in sorted(log.count.items())))
    print(summary)
    if a.log:
        with open(a.log, "a") as fh:
            fh.write("\n".join(log.lines + [summary]) + "\n")
    sys.exit(1 if log.count.get("CONFLICT") else 0)


if __name__ == "__main__":
    main()
