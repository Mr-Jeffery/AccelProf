#!/usr/bin/env python3
"""WARPSYNC join gap, phase 1: byte scan of every kernel JSON in the kept stores (read only).

  wjg_scan.py list --out <files.jsonl>                     enumerate the stores' kernel JSONs
  wjg_scan.py scan --files <files.jsonl> --out <jsonl> [--shard i/n] [--procs k]

Stores (CLAUDE.md A2 "Kept traces for offline re-analysis"): every directory under
/mnt/beegfs/fzheng4/cuvein_traces, and the home copies eval/baselines/traces_keep* (since T-H
behind symlinks in /mnt/beegfs/fzheng4/home_archive/eval_baselines). Layout
<store>/<id>/<mode>/kernel_N.json; anything else is listed with its relative path.

Per kernel JSON (each real file read once; symlinked duplicates point at the same real path):
  recs        occurrences of the record prefix `{"seq": ` (the dump's hb_events objects)
  hb_events   whether the key `"hb_events": [` is present, and whether the array is empty
  sw_full     syncwarp records whose active_mask covers sync_mask
  sw_partial  syncwarp records whose active_mask does not (a diverged warp's group), by pc
  sw_odd      occurrences of "syncwarp" that are not a parseable syncwarp record
The file is read in chunks cut at record starts, so no record is split. Nothing is written
to the stores. A file with sw_partial == 0 has no diverged syncwarp instance: the merge of
phase 2 leaves its records unchanged. Phase 2 (wjg_census.py) re-reads every file with
sw_partial > 0 in full and checks these counts against the parsed hb_events.
"""
import argparse
import collections
import fnmatch
import functools
import glob
import hashlib
import json
import multiprocessing as mp
import os
import re
import socket
import sys
import time

import orjson

BEEGFS = "/mnt/beegfs/fzheng4"
TRACE_ROOT = f"{BEEGFS}/cuvein_traces"
HOME_KEEP = f"{BEEGFS}/home_archive/eval_baselines"
CHUNK = 256 << 20
REC = b'{"seq":'                 # both serializations: '{"seq": 1' (collector, json.dump) and '{"seq":1' (compact)
KEY_RE = re.compile(rb'"hb_events":\s*\[')
KN_RE = re.compile(rb'"kernel_name":\s*"((?:[^"\\]|\\.)*)"')


MODES = ("vector-clock", "scalar-clock", "engine", "trace-only")


def stores():
    """(tag, root): the trace stores, then the other BeeGFS directories that hold kernel JSONs
    (task working directories, not stores under CLAUDE.md A2; tagged `other:`)."""
    out = [(os.path.basename(p), p) for p in sorted(glob.glob(f"{TRACE_ROOT}/*")) if os.path.isdir(p)]
    out += [("home:" + os.path.basename(p), p)
            for p in sorted(glob.glob(f"{HOME_KEEP}/traces_keep*")) if os.path.isdir(p)]
    out += [("other:" + os.path.basename(p), p) for p in sorted(glob.glob(f"{BEEGFS}/*"))
            if os.path.isdir(p) and p not in (TRACE_ROOT, f"{BEEGFS}/home_archive")]
    return out


def id_mode(rel):
    """<...>/<id>/<mode>/kernel_N.json -> (id, mode, prefix); mode = the last path component
    that names a mode."""
    for i in range(len(rel) - 2, -1, -1):
        if rel[i] in MODES:
            return (rel[i - 1] if i else None), rel[i], "/".join(rel[:max(i - 1, 0)])
    return None, None, "/".join(rel[:-1])


def cmd_list(a):
    n = 0
    with open(a.out, "w") as out:
        for tag, root in stores():
            if a.only and tag not in a.only.split(","):
                continue
            for dp, dns, fns in os.walk(root, followlinks=True):
                if a.id_glob and dp != root and \
                        not fnmatch.fnmatch(os.path.relpath(dp, root).split(os.sep)[0], a.id_glob):
                    dns[:] = []
                    continue
                dns.sort()
                for fn in sorted(fns):
                    if not (fn.startswith("kernel_") and fn.endswith(".json")):
                        continue
                    p = os.path.join(dp, fn)
                    rel = os.path.relpath(p, root).split(os.sep)
                    try:
                        st = os.stat(p)
                        real = os.path.realpath(p)
                    except OSError as e:
                        out.write(json.dumps({"store": tag, "rel": "/".join(rel), "err": str(e)}) + "\n")
                        continue
                    pid, mode, prefix = id_mode(rel)
                    rec = {"store": tag, "rel": "/".join(rel), "real": real, "size": st.st_size,
                           "id": pid, "mode": mode, "prefix": prefix}
                    out.write(json.dumps(rec) + "\n")
                    n += 1
    print(f"{n} kernel JSONs", flush=True)


def scan_piece(piece, st):
    st["recs"] += piece.count(REC)
    i = piece.find(b'"syncwarp"')
    while i != -1:
        s = piece.rfind(b"{", 0, i)
        e = piece.find(b"}", i)
        obj = None
        if s != -1 and e != -1:
            try:
                obj = orjson.loads(piece[s:e + 1])
            except orjson.JSONDecodeError:
                obj = None
        if isinstance(obj, dict) and obj.get("type") == "syncwarp" and "seq" in obj:
            sm, am = obj["sync_mask"], obj["active_mask"]
            if am & sm == sm:
                st["sw_full"] += 1
            else:
                st["sw_partial"] += 1
                st["partial_pcs"][hex(obj["pc"])] += 1
            i = piece.find(b'"syncwarp"', e + 1)
        else:
            st["sw_odd"] += 1
            i = piece.find(b'"syncwarp"', i + 10)


def scan_file(real):
    t0 = time.time()
    st = {"real": real, "recs": 0, "sw_full": 0, "sw_partial": 0, "sw_odd": 0,
          "partial_pcs": collections.Counter(), "hb_events_key": False, "hb_events_empty": None,
          "kname": None, "bytes": 0}
    try:
        with open(real, "rb") as f:
            carry = b""
            first = True
            while True:
                chunk = f.read(CHUNK)
                if first:
                    m = KN_RE.search(chunk[:1 << 20])
                    if m:
                        st["kname"] = orjson.loads(b'"' + m.group(1) + b'"')
                    first = False
                st["bytes"] += len(chunk)
                buf = carry + chunk
                if not st["hb_events_key"]:
                    m = KEY_RE.search(buf)
                    if m and m.end() < len(buf):
                        st["hb_events_key"] = True
                        st["hb_events_empty"] = buf[m.end():m.end() + 50].lstrip()[:1] == b"]"
                if not chunk:
                    scan_piece(buf, st)
                    break
                cut = buf.rfind(REC)
                if cut <= 0:
                    keep = min(len(buf), 64)
                    scan_piece(buf[:len(buf) - keep], st)
                    carry = buf[len(buf) - keep:]
                else:
                    scan_piece(buf[:cut], st)
                    carry = buf[cut:]
    except OSError as e:
        st["err"] = str(e)
    st["partial_pcs"] = dict(st["partial_pcs"])
    st["secs"] = round(time.time() - t0, 2)
    return st


def claimed_scan(real, claims):
    """Scan `real` unless another worker (any job sharing `claims`) took it: the claim is an
    O_EXCL create of claims/<sha1(real)>, so jobs started at different times share one queue."""
    try:
        fd = os.open(os.path.join(claims, hashlib.sha1(real.encode()).hexdigest()),
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return None
    os.write(fd, f"{socket.gethostname()} {os.getpid()} {real}\n".encode())
    os.close(fd)
    return scan_file(real)


def cmd_scan(a):
    seen, todo = set(), []
    for ln in open(a.files):
        r = json.loads(ln)
        if "real" in r and r["real"] not in seen:
            seen.add(r["real"])
            todo.append((r["size"], r["real"]))
    if a.only_nokey:
        # rescan the files an earlier scan saw without the spaced `"hb_events": [` key: compact dumps
        # (`"hb_events":[{"seq":1`) were counted as record-free by the first scan's patterns
        nokey = set()
        for p in sorted(glob.glob(a.only_nokey)):
            for ln in open(p):
                d = json.loads(ln)
                if not d.get("err") and not d["hb_events_key"]:
                    nokey.add(d["real"])
        todo = [t for t in todo if t[1] in nokey]
    todo.sort(reverse=True)
    si, sn = map(int, a.shard.split("/"))
    todo = [p for _, p in todo[si::sn]]
    done = set()
    for p in glob.glob(a.done_glob) if a.done_glob else [a.out]:
        if not os.path.exists(p):
            continue
        for ln in open(p):                         # resume: skip files already scanned
            try:
                done.add(json.loads(ln)["real"])
            except (ValueError, KeyError):
                pass
    todo = [p for p in todo if p not in done]
    print(f"shard {si}/{sn}: {len(todo)} files to scan ({len(done)} done)", flush=True)
    t0 = time.time()
    if a.claims:
        os.makedirs(a.claims, exist_ok=True)
        work = functools.partial(claimed_scan, claims=a.claims)
    else:
        work = scan_file
    with open(a.out, "a") as out, mp.Pool(a.procs) as pool:
        for k, st in enumerate(pool.imap_unordered(work, todo, chunksize=1), 1):
            if st is None:
                continue
            out.write(json.dumps(st) + "\n")
            out.flush()
            if k % 500 == 0 or st["sw_partial"]:
                print(f"{k}/{len(todo)} {time.time() - t0:.0f}s {st['bytes'] >> 20}MB "
                      f"sw {st['sw_full']}/{st['sw_partial']} {st['real'][-90:]}", flush=True)
    print(f"done {time.time() - t0:.0f}s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list")
    p.add_argument("--out", required=True)
    p.add_argument("--only", default="", help="comma-separated store tags (default: all)")
    p.add_argument("--id-glob", default="", help="program ids to keep (smoke tests)")
    p = sub.add_parser("scan")
    p.add_argument("--files", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--shard", default="0/1")
    p.add_argument("--procs", type=int, default=16)
    p.add_argument("--claims", default="", help="claims directory shared by concurrent jobs")
    p.add_argument("--done-glob", default="", help="scan outputs whose files count as done")
    p.add_argument("--only-nokey", default="", help="glob of earlier scan outputs: rescan their key-less files")
    a = ap.parse_args()
    {"list": cmd_list, "scan": cmd_scan}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
