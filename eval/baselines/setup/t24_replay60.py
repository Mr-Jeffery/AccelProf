#!/usr/bin/env python3
"""T24 step 4: replay the 60 (program, mode) recordings of X5b section 4 (eval/X5_BYTE_PAIRS.md,
eval/results/x5b/partial.jsonl on branch eval/x5-byte-pairs) as recorded, with this tree's
hb_oracle (the warp-barrier assembly) and with 38af04e's (the per-record join), every launch.

  t24_replay60.py --groups <x5b partial.jsonl> --old-oracle <38af04e hb_oracle.py> --out <jsonl>
                  [--shard i/n]

Per launch: the race pc pairs (races: space:a-b:kind:class; sync_only: a-b) of
  old     38af04e's oracle on the records as recorded;
  new     this tree's oracle on the records as recorded (strict; a TV-... AlignmentError is recorded
          and the launch is replayed again with YOSEMITE_HB_STRICT=0);
  merged  38af04e's oracle on X5b's merged records (each completed partial instance one record at
          its completion, active mask = the union: x5b_partial.partial_instances, copied here).
Reported: pairs only in new / only in old (the change's effect), new != merged (the assembly against
X5b's construction), the partial-instance census, TV messages. As X5b: programs with 1296-node
inputs replay without their global records (memory). Read-only on the stores.
"""
import argparse
import collections
import contextlib
import glob
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT_TREE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT_TREE / "python"))
import sync_dominance as sd                  # noqa: E402
import hb_oracle as ho_new                   # noqa: E402

STORES = "/mnt/beegfs/fzheng4/cuvein_traces"
MEM = ("read", "write", "atomic")


def load_old(path):
    spec = importlib.util.spec_from_file_location("hb_oracle_38af04e", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def kernel_jsons(d):
    return sorted(glob.glob(os.path.join(d, "kernel_*.json")),
                  key=lambda p: int(p.rsplit("_", 1)[1].split(".")[0]))


def launches(d, kernels, mangled):
    for kj in kernel_jsons(d):
        t = json.loads(Path(kj).read_text())
        try:
            m = sd.select_kernel(kernels, t["kernel"]["kernel_name"])
        except sd.AlignmentError:
            continue
        if m == mangled:
            yield kj, t


def partial_instances(ev):
    """X5b's merge (x5b_partial.partial_instances): -> (census, merged events)."""
    c = collections.Counter()
    opened, drop, widen = {}, set(), {}
    for e in ev:
        if e.get("type") != "syncwarp":
            continue
        k = (e["block"], e["warp"], e["pc"])
        sm, am = e["sync_mask"], e["active_mask"]
        if k not in opened:
            if am & sm == sm:
                continue
            opened[k] = [am, [e["seq"]]]
            continue
        st = opened[k]
        st[0] |= am
        st[1].append(e["seq"])
        if st[0] & sm == sm:
            c[f"instances of {len(st[1])} records"] += 1
            drop.update(st[1][:-1])
            widen[st[1][-1]] = st[0]
            del opened[k]
    c["never completed"] += len(opened)
    merged = [dict(e, active_mask=widen[e["seq"]]) if e["seq"] in widen else e
              for e in ev if e["seq"] not in drop]
    return c, merged


@contextlib.contextmanager
def strict_off():
    old = os.environ.get("YOSEMITE_HB_STRICT")
    os.environ["YOSEMITE_HB_STRICT"] = "0"
    try:
        yield
    finally:
        if old is None:
            del os.environ["YOSEMITE_HB_STRICT"]
        else:
            os.environ["YOSEMITE_HB_STRICT"] = old


def race_sets(mod, dot, t, events, tmpdir):
    """-> (sets, tv message or None, error or None)"""
    t2 = dict(t, hb_events=events)
    fd, path = tempfile.mkstemp(suffix=".json", dir=tmpdir)
    tv = None
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(t2, f)
        try:
            rep = mod.analyze(dot, path)
        except sd.AlignmentError as e:
            if not str(e).startswith("TV-"):
                return None, None, str(e)[:200]
            tv = str(e)[:200]
            with strict_off():
                rep = mod.analyze(dot, path)
    finally:
        os.unlink(path)
    return ({"races": sorted({f"{r['space']}:{r['a_pc']:#x}-{r['b_pc']:#x}:{r['kind']}:{r['class']}"
                              for r in rep["races"] if r.get("a_pc") is not None}),
             "sync_only": sorted({f"{a:#x}-{b:#x}" for a, b, _ in rep["races_sync_only"]})},
            tv, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", required=True)
    ap.add_argument("--old-oracle", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args()
    ho_old = load_old(a.old_oracle)
    groups = [json.loads(ln) for ln in open(a.groups)]
    si, sn = map(int, a.shard.split("/"))
    tmpdir = os.environ.get("TMPDIR", "/tmp")
    with open(a.out, "w") as out:
        for g in groups[si::sn]:
            store, pid, mode, kernel = g["store"], g["id"], g["mode"], g["kernel"]
            dotbase, mangled = kernel.split("::", 1)
            dot = f"{STORES}/{store}/{pid}/dots/{dotbase}"
            kernels = sd.parse_dot(dot)
            shared_only = g["shared_only"]
            rec = {"store": store, "id": pid, "mode": mode, "kernel": kernel,
                   "shared_only": shared_only, "launches": 0, "census": collections.Counter(),
                   "only_new": collections.Counter(), "only_old": collections.Counter(),
                   "new_ne_merged": collections.Counter(), "tv_new": [], "tv_old": [],
                   "errors": []}
            for kj, t in launches(f"{STORES}/{store}/{pid}/{mode}", kernels, mangled):
                ev = sorted(t["hb_events"], key=lambda e: e["seq"])
                if shared_only:
                    ev = [e for e in ev if e.get("space") != "global"]
                rec["launches"] += 1
                cen, merged = partial_instances(ev)
                rec["census"].update(cen)
                old, tvo, err_o = race_sets(ho_old, dot, t, ev, tmpdir)
                new, tvn, err_n = race_sets(ho_new, dot, t, ev, tmpdir)
                mrg, _, err_m = race_sets(ho_old, dot, t, merged, tmpdir)
                name = os.path.basename(kj)
                if err_o or err_n or err_m:
                    rec["errors"].append([name, err_o, err_n, err_m])
                    continue
                if tvn:
                    rec["tv_new"].append([name, tvn])
                if tvo:
                    rec["tv_old"].append([name, tvo])
                for f in ("races", "sync_only"):
                    for p in set(new[f]) - set(old[f]):
                        rec["only_new"][f"{f} {p}"] += 1
                    for p in set(old[f]) - set(new[f]):
                        rec["only_old"][f"{f} {p}"] += 1
                    for p in set(new[f]) ^ set(mrg[f]):
                        rec["new_ne_merged"][f"{f} {p}"] += 1
            for k in ("census", "only_new", "only_old", "new_ne_merged"):
                rec[k] = dict(rec[k])
            out.write(json.dumps(rec) + "\n")
            out.flush()
            print(pid[:60], mode[:6], rec["launches"], rec["census"], "ONLY-NEW", rec["only_new"],
                  "ONLY-OLD", rec["only_old"], "NEW!=MERGED", rec["new_ne_merged"],
                  "TV", len(rec["tv_new"]), rec["tv_new"][:1], rec["errors"][:1], flush=True)


if __name__ == "__main__":
    main()
