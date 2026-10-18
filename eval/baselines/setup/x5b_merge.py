#!/usr/bin/env python3
"""X5 byte pairs: merge x5b_byte_pairs.py outputs (read only on the inputs).

  x5b_merge.py --full 'glob' --shared 'glob' --out merged.jsonl --check check.md

The --shared-only run covers every row and carries the instance check; it is the merged record.
Where a full replay exists (the rows whose full replay fit in node memory), its `events` block is
attached as `events_full`, and --check compares the two: the barrier-only clock's answers (the
pair in races_sync_only as recorded and per removal variant) and the trace facts must be equal --
dropping the global records cannot change them; any difference is listed. The vector clock's
answers are compared too; they may differ only where the kernel's atomic joins matter.
"""
import argparse
import glob
import json


def key(r):
    return (r["id"], r["mode"], r["u"], r["v"])


def load(pattern):
    out = {}
    for f in sorted(glob.glob(pattern)):
        for ln in open(f):
            r = json.loads(ln)
            out[key(r)] = r
    return out


def sync_view(e):
    c = e.get("counts", {})
    return {"launches": c.get("launches"),
            "recorded_sync_only_true": c.get("oracle_sync_only:True", 0),
            "removed_sync_only_true": {v: d.get("sync_only:True", 0)
                                       for v, d in e.get("oracle_with_sync_records_removed", {}).items()},
            "sync_records": e.get("sync_records_at_cut_pcs"),
            "same_byte": c.get("same_byte_launches"),
            "other_bytes": c.get("words_shared_only_by_different_bytes")}


def race_view(e):
    c = e.get("counts", {})
    return {"recorded_races_true": c.get("oracle_races:True", 0),
            "removed_races_true": {v: d.get("races:True", 0)
                                   for v, d in e.get("oracle_with_sync_records_removed", {}).items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", required=True)
    ap.add_argument("--shared", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", required=True)
    a = ap.parse_args()
    full, shared = load(a.full), load(a.shared)
    both = sorted(k for k in set(full) & set(shared) if full[k].get("events") and shared[k].get("events"))
    for k in both:
        shared[k]["events_full"] = full[k]["events"]
    with open(a.out, "w") as f:
        for k in sorted(shared):
            f.write(json.dumps(shared[k]) + "\n")
    sync_diff = [k for k in both if sync_view(full[k]["events"]) != sync_view(shared[k]["events"])]
    race_diff = [k for k in both if race_view(full[k]["events"]) != race_view(shared[k]["events"])]
    with open(a.check, "w") as f:
        f.write(f"shared-only records {len(shared)} (the merged set); full-replay records "
                f"{len(full)}; rows with both {len(both)}; rows without a full replay "
                f"{len(set(shared) - set(full))}; full-replay rows missing from the shared-only "
                f"set {len(set(full) - set(shared))}\n\n")
        f.write(f"rows with both: barrier-only clock answers and trace facts differ in "
                f"{len(sync_diff)}; vector-clock answers differ in {len(race_diff)}\n\n")
        for k in sync_diff:
            f.write(f"- SYNC DIFF {k}: full {sync_view(full[k]['events'])} / "
                    f"shared-only {sync_view(shared[k]['events'])}\n")
        for k in race_diff:
            f.write(f"- races differ {k}: full {race_view(full[k]['events'])} / "
                    f"shared-only {race_view(shared[k]['events'])}\n")
        f.write("\nrows without a full replay:\n\n")
        for k in sorted(set(shared) - set(full)):
            f.write(f"- {k}\n")
    print(open(a.check).read())


if __name__ == "__main__":
    main()
