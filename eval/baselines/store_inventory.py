#!/usr/bin/env python3
"""T0: inventory every cuVein trace store and mirror its index into home.

A trace store is a directory of `<id>/{meta.json,dots/,logs/,<mode>/kernel_*.json}`
written by `parallel.py` (BeeGFS: /mnt/beegfs/$USER/cuvein_traces/<tag>; home:
eval/baselines/traces_keep*/ -- the size-capped FP/FN/ERROR/TIMEOUT copies).
For every program this reports what the store actually holds and why a trace is
missing -- the answer to "what did the earlier keep-all run drop":

  trace_dropped        --keep-all-cap-gb: `_cap_kept` deleted the kernel JSONs
  trace-too-large      --keep-cap-mb: `_keep_trace` copied meta/dots/logs only
  <mode>:unsaved:...   no rep of that mode produced a saveable dump
                       (all-reps-timed-out / no-kernel-json / not-saved) and no
                       <mode>-partial-rep<k>/ prefix dump is there either (a kept
                       prefix dump is listed under kept_partial, not lost)
  <mode>:missing       the mode never ran (shard killed before it started)
  <mode>:missing-on-disk  meta says saved but no kernel_*.json is there
  error:<msg>          collect_one failed before the runs (missing-exe, ...)
  collecting           meta written at start of collection, never finalized

BeeGFS is not backed up, so STORE_INFO.json and every meta.json of each BeeGFS
store are mirrored to --index-dir/<tag>/ (home, small) together with INDEX.json
(this scan). Run on a node where BeeGFS is mounted (compute nodes only):

  srun -p normal -N1 -n1 -t 00:30:00 .env/bin/python eval/baselines/store_inventory.py \
      --md eval/baselines/store_index/inventory.md
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
USER = os.environ.get("USER", "nobody")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "python"))
import hb_modes  # noqa: E402  (vector-clock / scalar-clock; pre-T8 stores accepted with a warning)


def _du_bytes(path):
    try:
        out = subprocess.run(["du", "-sb", path], capture_output=True, text=True,
                             timeout=3600).stdout
        return int(out.split()[0])
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return -1


def _json_sizes(pattern):
    files = glob.glob(pattern)
    total = 0
    for f in files:
        try:
            total += os.path.getsize(f)
        except OSError:
            pass
    return len(files), total


def scan_program(idir, store_modes):
    _id = os.path.basename(idir)
    rec = dict(id=_id, modes={}, lost=[])
    try:
        meta = hb_modes.canon_meta(json.loads(open(f"{idir}/meta.json").read()),
                                   f"{idir}/meta.json")
    except (OSError, ValueError) as e:
        rec["lost"].append(f"unreadable-meta:{type(e).__name__}")
        return rec
    for k in ("pset", "error", "status", "trace_dropped", "keep_reason", "trace_bytes",
              "node", "arch", "native_rc", "tool_timeout"):
        if k in meta:
            rec[k] = meta[k]
    if meta.get("error"):
        rec["lost"].append(f"error:{meta['error']}")
    if meta.get("status") == "collecting":
        rec["lost"].append("collecting")
    if meta.get("trace_dropped"):
        rec["lost"].append(f"trace_dropped:{meta['trace_dropped']}")
    if "trace-too-large" in (meta.get("keep_reason") or ""):
        rec["lost"].append("trace-too-large")
    modes_meta = meta.get("modes", {}) or {}
    rank = lambda m: hb_modes.MODES.index(m) if m in hb_modes.MODES else len(hb_modes.MODES)
    for mode in sorted(set(store_modes) | set(modes_meta), key=lambda m: (rank(m), m)):
        mm = modes_meta.get(mode)
        n_json, b_json = _json_sizes(f"{hb_modes.resolve_dir(idir, mode)}/kernel_*.json")
        partials = sorted(glob.glob(f"{idir}/{mode}-partial-rep*")
                          + glob.glob(f"{idir}/{hb_modes.LEGACY_OF.get(mode, mode)}-partial-rep*"))
        p_json = sum(_json_sizes(f"{p}/kernel_*.json")[1] for p in partials)
        m = dict(on_disk_json=n_json, on_disk_bytes=b_json,
                 partial_dirs=[os.path.basename(p) for p in partials],
                 partial_bytes=p_json)
        if mm is None:
            m["saved"] = None
            rec["lost"].append(f"{mode}:missing")
        else:
            reps = mm.get("reps", []) or []
            m.update(saved=mm.get("saved"), partial=mm.get("partial"),
                     events=mm.get("events"), n_reps=len(reps),
                     timed_out=sum(1 for r in reps if r.get("timed_out")),
                     complete=sum(1 for r in reps if r.get("complete")),
                     max_dump_mb=max([r.get("dump_mb") or 0 for r in reps] or [0]),
                     max_nkernels=max([r.get("nkernels") or 0 for r in reps] or [0]),
                     max_peak_mb=max([r.get("peak_mb") or 0 for r in reps
                                      if isinstance(r.get("peak_mb"), (int, float))] or [0]))
            if not mm.get("saved"):
                if reps and m["timed_out"] == len(reps):
                    why = "all-reps-timed-out"
                elif m["max_nkernels"] == 0:
                    why = "no-kernel-json"
                else:
                    why = "not-saved"
                if mm.get("partial_dump") and p_json:
                    # T0: the timed-out rep's prefix dump IS in the store -- evidence
                    # kept, not a loss (it is still not a verdict)
                    rec.setdefault("kept_partial", []).append(f"{mode}:{mm['partial_dump']}")
                else:
                    rec["lost"].append(f"{mode}:unsaved:{why}")
            elif n_json == 0 and not meta.get("trace_dropped") \
                    and "trace-too-large" not in (meta.get("keep_reason") or ""):
                rec["lost"].append(f"{mode}:missing-on-disk")
        rec["modes"][mode] = m
    return rec


def scan_store(store, kind, modes_default=hb_modes.MODES, du=True):
    info = {}
    try:
        info = json.loads(open(f"{store}/STORE_INFO.json").read())
    except (OSError, ValueError):
        pass
    modes = tuple(hb_modes.canon(m, f"{store}/STORE_INFO.json") for m in (info.get("modes") or modes_default))
    programs = [scan_program(os.path.dirname(md), modes)
                for md in sorted(glob.glob(f"{store}/*/meta.json"))]
    errors = {}
    for ef in sorted(glob.glob(f"{store}/*.error")):
        try:
            errors[os.path.basename(ef)[:-6]] = open(ef).read().strip()[:200]
        except OSError:
            pass
    rec = dict(store=store, kind=kind, tag=os.path.basename(store.rstrip("/")),
               info=info, modes=list(modes), n_programs=len(programs),
               n_lost=sum(1 for p in programs if p["lost"]),
               error_files=errors, programs=programs,
               bytes=_du_bytes(store) if du else -1, scanned=time.strftime("%Y-%m-%d %H:%M:%S"),
               scanned_on=os.uname().nodename)
    return rec


def mirror(rec, index_dir):
    """Copy STORE_INFO.json + every meta.json of a BeeGFS store into home."""
    dst = f"{index_dir}/{rec['tag']}"
    os.makedirs(dst, exist_ok=True)
    n = 0
    if os.path.exists(f"{rec['store']}/STORE_INFO.json"):
        shutil.copy2(f"{rec['store']}/STORE_INFO.json", f"{dst}/STORE_INFO.json")
    for p in rec["programs"]:
        src = f"{rec['store']}/{p['id']}/meta.json"
        if os.path.exists(src):
            os.makedirs(f"{dst}/{p['id']}", exist_ok=True)
            shutil.copy2(src, f"{dst}/{p['id']}/meta.json")
            n += 1
    slim = dict(rec, programs=rec["programs"])
    open(f"{dst}/INDEX.json", "w").write(json.dumps(slim, indent=1))
    return n


def _gb(b):
    return f"{b / 1e9:.1f} GB" if isinstance(b, (int, float)) and b >= 0 else "?"


def markdown(recs):
    out = ["| store | kind | created | git head | modes | programs | with a loss | on disk | scanned on |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in recs:
        i = r["info"]
        out.append(f"| `{r['store']}` | {r['kind']} | {i.get('created', '—')} | "
                   f"`{(i.get('git_head') or '—')[:8]}` | {','.join(r['modes'])} | "
                   f"{r['n_programs']} | {r['n_lost']} | {_gb(r['bytes'])} | {r['scanned_on']} |")
    out.append("")
    out.append("Per-store loss breakdown (count of programs per reason; a program can carry several):")
    out.append("")
    out.append("| store | reason | programs |")
    out.append("|---|---|---|")
    for r in recs:
        cnt = {}
        for p in r["programs"]:
            for l in p["lost"]:
                key = l.split(":")[0] if l.startswith(("error", "trace_dropped")) else ":".join(l.split(":")[:3])
                cnt[key] = cnt.get(key, 0) + 1
        for k, v in sorted(cnt.items()):
            out.append(f"| {r['tag']} | `{k}` | {v} |")
        if r["error_files"]:
            out.append(f"| {r['tag']} | `.error files` | {len(r['error_files'])} |")
    out.append("")
    out.append("Every program with a lost or partial trace:")
    out.append("")
    out.append("| store | id | reasons | mode dumps on disk | largest raw dump seen (MB) | peak RSS (MB) |")
    out.append("|---|---|---|---|---|---|")
    for r in recs:
        for p in r["programs"]:
            if not p["lost"]:
                continue
            disk = "; ".join(f"{m}:{v['on_disk_json']}j/{_gb(v['on_disk_bytes'])}"
                             + (f"+{len(v['partial_dirs'])}partial" if v["partial_dirs"] else "")
                             for m, v in p["modes"].items())
            dump = max([v.get("max_dump_mb") or 0 for v in p["modes"].values()] or [0])
            peak = max([v.get("max_peak_mb") or 0 for v in p["modes"].values()] or [0])
            out.append(f"| {r['tag']} | `{p['id']}` | {', '.join(p['lost'])} | {disk} | {dump:.0f} | {peak:.0f} |")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--beegfs-root", default=f"/mnt/beegfs/{USER}/cuvein_traces")
    ap.add_argument("--home-stores", default=f"{HERE}/traces_keep*")
    ap.add_argument("--store", action="append", default=[],
                    help="extra store dir(s) to scan (kind=extra)")
    ap.add_argument("--index-dir", default=f"{HERE}/store_index")
    ap.add_argument("--out", default="", help="inventory JSON (default <index-dir>/inventory.json)")
    ap.add_argument("--md", default="", help="markdown summary (default <index-dir>/inventory.md)")
    ap.add_argument("--no-mirror", action="store_true")
    ap.add_argument("--no-du", action="store_true", help="skip du (slow on big stores)")
    a = ap.parse_args()
    os.makedirs(a.index_dir, exist_ok=True)
    recs = []
    if os.path.isdir(a.beegfs_root):
        for s in sorted(glob.glob(f"{a.beegfs_root}/*/")):
            print(f"[scan beegfs] {s}", flush=True)
            r = scan_store(s.rstrip("/"), "beegfs", du=not a.no_du)
            if not a.no_mirror:
                r["mirrored_metas"] = mirror(r, a.index_dir)
            recs.append(r)
    else:
        print(f"NOTE: {a.beegfs_root} is not present on {os.uname().nodename} "
              f"(BeeGFS is mounted on compute nodes only)", file=sys.stderr)
    for s in sorted(glob.glob(a.home_stores)):
        if os.path.isdir(s):
            print(f"[scan home] {s}", flush=True)
            recs.append(scan_store(s.rstrip("/"), "home", du=not a.no_du))
    for s in a.store:
        print(f"[scan extra] {s}", flush=True)
        recs.append(scan_store(s.rstrip("/"), "extra", du=not a.no_du))
    out = a.out or f"{a.index_dir}/inventory.json"
    md = a.md or f"{a.index_dir}/inventory.md"
    open(out, "w").write(json.dumps(recs, indent=1))
    open(md, "w").write(markdown(recs))
    for r in recs:
        print(f"{r['tag']:>24} {r['kind']:6} programs={r['n_programs']:4} lost={r['n_lost']:4} "
              f"bytes={_gb(r['bytes'])} mirrored={r.get('mirrored_metas', '-')}")
    print(f"-> {out}\n-> {md}")


if __name__ == "__main__":
    main()
