#!/usr/bin/env python3
"""T8 step 4: are the regenerated reports and analysis CSVs identical up to the labels?

  python3 t8_compare_reports.py <before checkout> <after checkout>

Both checkouts ran the same p_final2 chain (setup/t8_chain_check.sh): BEFORE = pre-T8
code on pre-T8 data, AFTER = T8 code on migrated data. The AFTER files are mapped back
to the pre-T8 vocabulary (LABELS, most specific first) and compared with BEFORE, first
exactly, then as line multisets (classify_endpoints writes its rows in glob() order,
which differs between runs of the SAME code). Every line that still differs is printed:
those are the intended wording changes of make_tables.py, nothing else may remain.
"""
import collections
import sys

LABELS = [
    ("cuVein (vector-clock)", "cuVein (engine)"), ("cuVein (scalar-clock)", "cuVein (trace-only)"),
    ("cuVein-VC", "cuVein-eng"), ("cuVein-SC", "cuVein-tr"),
    ("**VC**", "**eng**"), ("**SC**", "**tr**"),
    ("cuvein/vector-clock", "cuvein/engine"), ("cuvein/scalar-clock", "cuvein/trace-only"),
    ("cuVein vector-clock=", "cuVein-engine="), ("cuVein scalar-clock=", "cuVein-trace-only="),
    ("cuVein vector-clock vs SuperCollider", "cuVein-engine vs SuperCollider"),
    ("cuVein vector-clock P", "cuVein-engine P"), ("cuVein vector-clock PI", "cuVein-engine PI"),
    ("cuVein vector-clock **", "cuVein-engine **"),
    ("vector-clock", "engine"), ("scalar-clock", "trace-only"),
]
FILES = ["eval/BASELINES.md", "eval/BASELINES_SUMMARY.md",
         "eval/results/baselines-diagnose.csv", "eval/results/baselines-disagreements.csv",
         "eval/results/baselines-fp-causes.csv",
         "eval/baselines/setup/t8_check/compare_fpfix.{}.txt"]


def back(line):
    for new, old in LABELS:
        line = line.replace(new, old)
    return squeeze(line)


def squeeze(line):
    """runs of blanks -> one: fixed-width columns widen with the longer labels"""
    return " ".join(line.split(" ")) if "  " not in line else __import__("re").sub(r" {2,}", " ", line)


def main():
    before, after = sys.argv[1], sys.argv[2]
    files = sys.argv[3].split(",") if len(sys.argv) > 3 else FILES
    bad = 0
    for f in files:
        if "{}" in f:
            fb, fa = f"{after}/{f.format('before')}", f"{after}/{f.format('after')}"
        else:
            fb, fa = f"{before}/{f}", f"{after}/{f}"
        b = [squeeze(l) for l in open(fb).read().splitlines()]
        a = [back(l) for l in open(fa).read().splitlines()]
        if a == b:
            print(f"IDENTICAL up to labels            {f} ({len(b)} lines)")
            continue
        cb, ca = collections.Counter(b), collections.Counter(a)
        if cb == ca:
            print(f"IDENTICAL up to labels + row order {f} ({len(b)} lines)")
            continue
        only_b, only_a = sorted((cb - ca).elements()), sorted((ca - cb).elements())
        print(f"DIFFERS                            {f}: {len(only_b)} line(s) only before, {len(only_a)} only after")
        for l in only_b[:12]:
            print(f"   - {l[:230]}")
        for l in only_a[:12]:
            print(f"   + {l[:230]}")
        bad += 1
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
