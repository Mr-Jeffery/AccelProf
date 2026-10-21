#!/usr/bin/env python3
"""T24: before/after on the same records for the programs of a kept store whose dumps carry a
diverged WARPSYNC or a sync_mask naming exited/absent lanes (t24_census.py's list): every kernel JSON
of those (program, mode) dirs replayed with 38af04e's oracle and barrier_only_pairs and with this
tree's, on the records as recorded.

  t24_replay_store.py --store <dir> --census <census jsonl> --old-oracle <py> --old-sd <py> --out <jsonl>
                      [--shard i/n]

Per (program, mode): race pc pairs (oracle races and races_sync_only; barrier_only_pairs pairs) only
after / only before T24, TV messages under strict (a TV-... AlignmentError is recorded and the replay
repeated with YOSEMITE_HB_STRICT=0). Read-only on the store.
"""
import argparse
import collections
import glob
import importlib.util
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t24_replay60 as r60                   # noqa: E402  (puts this tree's python/ on sys.path)
from t24_replay60 import sd, ho_new          # noqa: E402


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def offline(mod, eng, t):
    rmw = {pc: s for pc, op in eng.pc_opcode.items() if (s := sd.atomic_scope(op)) is not None}
    coh = {pc: s for pc, op in eng.pc_opcode.items()
           if (s := sd.coherent_scope(op, sd.strong_ldst_policy())) is not None}
    plain = {k: v for k, v in t.items() if k not in ("hb_sync_pass", "hb_rmw_points")}
    tv = []
    pairs = mod.barrier_only_pairs(plain, rmw, coh, None, None, None, sd.dump_async_pcs(eng, t), tv_out=tv)
    return {f"{a:#x}-{b:#x}" for a, b in (pairs or {})}, tv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True)
    ap.add_argument("--census", required=True)
    ap.add_argument("--old-oracle", required=True)
    ap.add_argument("--old-sd", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--skip-done", help="a previous output: its dirs are not replayed again")
    a = ap.parse_args()
    done = {json.loads(ln)["dir"] for ln in open(a.skip_done)} if a.skip_done else set()
    ho_old = r60.load_old(a.old_oracle)
    sd_old = load("sync_dominance_38af04e", a.old_sd)
    dirs = collections.OrderedDict()
    for ln in open(a.census):
        r = json.loads(ln)
        d = "/".join(r["file"].split("/")[:2])
        if (r.get("partial records") or r.get("records naming exited or absent lanes")) and d not in done:
            dirs[d] = 1
    si, sn = map(int, a.shard.split("/"))
    tmpdir = os.environ.get("TMPDIR", "/tmp")
    with open(a.out, "w") as out:
        for d in list(dirs)[si::sn]:
            pid = d.split("/")[0]
            parsed = {}
            for dot in sorted(glob.glob(f"{a.store}/{pid}/dots/*.dot")):
                try:
                    parsed[dot] = sd.parse_dot(dot)
                except sd.AlignmentError:       # a dot without kernel clusters (host-side cubin)
                    continue
            rec = {"dir": d, "kernels": 0, "only_new": collections.Counter(),
                   "only_old": collections.Counter(), "tv_new": [], "tv_old": [], "errors": []}
            for kj in r60.kernel_jsons(f"{a.store}/{d}"):
                t = json.loads(Path(kj).read_text())
                if not t.get("hb_events"):
                    continue
                name = os.path.basename(kj)
                for dot, kernels in parsed.items():
                    try:
                        m = sd.select_kernel(kernels, t["kernel"]["kernel_name"])
                        eng = sd.HBGraph(*kernels[m])
                        break
                    except sd.AlignmentError:
                        continue
                else:
                    rec["errors"].append([name, "no CFG"])
                    continue
                ev = sorted(t["hb_events"], key=lambda e: e["seq"])
                old, tvo, err_o = r60.race_sets(ho_old, dot, t, ev, tmpdir)
                new, tvn, err_n = r60.race_sets(ho_new, dot, t, ev, tmpdir)
                if err_o or err_n:
                    rec["errors"].append([name, err_o, err_n])
                    continue
                rec["kernels"] += 1
                if tvn:
                    rec["tv_new"].append([name, tvn])
                if tvo:
                    rec["tv_old"].append([name, tvo])
                bo_old, tv_bo = offline(sd_old, eng, t)
                bo_new, tv_bn = offline(sd, eng, t)
                old["offline"], new["offline"] = sorted(bo_old), sorted(bo_new)
                if tv_bn:
                    rec["tv_new"].append([name, "offline: " + tv_bn[0][:160]])
                for f in ("races", "sync_only", "offline"):
                    for p in set(new[f]) - set(old[f]):
                        rec["only_new"][f"{f} {p}"] += 1
                    for p in set(old[f]) - set(new[f]):
                        rec["only_old"][f"{f} {p}"] += 1
            rec["only_new"], rec["only_old"] = dict(rec["only_new"]), dict(rec["only_old"])
            out.write(json.dumps(rec) + "\n")
            out.flush()
            print(d[:80], rec["kernels"], "ONLY-NEW", rec["only_new"], "ONLY-OLD", rec["only_old"],
                  "TV new", rec["tv_new"][:2], "TV old", rec["tv_old"][:2], rec["errors"][:2], flush=True)


if __name__ == "__main__":
    main()
