#!/usr/bin/env python3
"""C6b step 3: build the hb-stripped copy of the scalar-clock recordings of X1b's `final-2026-11-view`.
For every id: <OUT>/<id>/meta.json (modes = {"collector-only": the scalar-clock mode entry}), dots -> the original dots dir
(symlink), collector-only/kernel_*.json = the scalar-clock kernel JSON with EVERY top-level or nested key starting with
"hb_" deleted (recursively, in dicts at any depth). The original store is only read. 16 worker processes.
Writes <OUT>/strip_report.json (per id: kernels, bytes, removed-key counts) and prints totals."""
import collections
import copy
import json
import os
import sys
from multiprocessing import Pool

V = os.environ.get("S3_VIEW", "/mnt/beegfs/fzheng4/cuvein_traces/final-2026-11-view")
OUT = os.environ.get("S3_STORE", "/mnt/beegfs/fzheng4/c6b-step3/store")


def strip(o, removed, depth):
    if isinstance(o, dict):
        for k in [k for k in o if isinstance(k, str) and k.startswith("hb_")]:
            removed[("top:" if depth == 0 else "nested:") + k] += 1
            del o[k]
        for v in o.values():
            strip(v, removed, depth + 1)
    elif isinstance(o, list):
        for v in o:
            strip(v, removed, depth + 1)


def has_hb(o):
    if isinstance(o, dict):
        return any((isinstance(k, str) and k.startswith("hb_")) or has_hb(v) for k, v in o.items())
    if isinstance(o, list):
        return any(has_hb(v) for v in o)
    return False


def one(i):
    src = f"{V}/{i}"
    dst = f"{OUT}/{i}"
    rep = {"id": i, "kernels": 0, "bytes_in": 0, "bytes_out": 0, "removed": {}, "err": None, "no_sc_dir": False}
    removed = collections.Counter()
    try:
        # the meta of the store the scalar-clock directory really lives in (the view's meta.json links to the
        # first pass; an id whose scalar-clock rows come from a long / 24 h pass has the long pass's meta there)
        scr = os.path.realpath(f"{src}/scalar-clock")
        mp = os.path.join(os.path.dirname(scr), "meta.json")
        own = os.path.isdir(scr) and os.path.exists(mp) and \
            os.path.realpath(mp) != os.path.realpath(f"{src}/meta.json")
        rep["meta_from_other_store"] = bool(own)
        meta = json.load(open(mp if own else f"{src}/meta.json"))
        os.makedirs(dst, exist_ok=True)
        modes = meta.get("modes") or {}
        sc = modes.get("scalar-clock")
        meta["modes"] = {"collector-only": copy.deepcopy(sc)} if sc is not None else {}
        meta["c6b_step3_source"] = f"{V}/{i}/scalar-clock (hb_* keys deleted)"
        json.dump(meta, open(f"{dst}/meta.json", "w"))
        dots = os.path.realpath(f"{src}/dots")
        if os.path.lexists(f"{dst}/dots"):
            os.remove(f"{dst}/dots")
        os.symlink(dots, f"{dst}/dots")
        sd = f"{src}/scalar-clock"
        if not os.path.isdir(sd):
            rep["no_sc_dir"] = True
            return rep
        os.makedirs(f"{dst}/collector-only", exist_ok=True)
        for fn in sorted(os.listdir(sd)):
            if not (fn.startswith("kernel_") and fn.endswith(".json")):
                continue
            p = f"{sd}/{fn}"
            rep["bytes_in"] += os.path.getsize(p)
            j = json.load(open(p))
            strip(j, removed, 0)
            assert not has_hb(j), (i, fn)
            q = f"{dst}/collector-only/{fn}"
            with open(q, "w") as f:
                json.dump(j, f)
            rep["bytes_out"] += os.path.getsize(q)
            rep["kernels"] += 1
    except Exception as e:      # noqa: BLE001
        rep["err"] = f"{type(e).__name__}: {e}"
    rep["removed"] = dict(removed)
    return rep


if __name__ == "__main__":
    ids = sorted(os.listdir(V))
    os.makedirs(OUT, exist_ok=True)
    with Pool(16) as p:
        res = p.map(one, ids, chunksize=8)
    json.dump(res, open(f"{OUT}/strip_report.json", "w"))
    ov = [r["id"] for r in res if r.get("meta_from_other_store")]
    open(f"{OUT}/ov_ids.txt", "w").write("\n".join(ov) + "\n")
    print("ids whose meta comes from a long / 24 h store:", ov)
    tot = collections.Counter()
    for r in res:
        tot.update(r["removed"])
    print("ids", len(res), "kernels", sum(r["kernels"] for r in res), "bytes_in", sum(r["bytes_in"] for r in res),
          "bytes_out", sum(r["bytes_out"] for r in res), "errors", [(r["id"], r["err"]) for r in res if r["err"]][:20],
          "no_sc_dir", [r["id"] for r in res if r["no_sc_dir"]])
    print("removed keys (count of dicts):", dict(tot))
