#!/usr/bin/env python3
"""X12 parity criterion (Jeffery 2026-11-07): the analysed report set -- the reported (pc,pc) pairs with their class, i.e. the
`report_ids` tokens (<space>:<pc>-<pc>:<RAW|WAR|WAW|...>) plus `report_lines` and the `classes=` note -- of a recording equals the baseline's.
  x12_pairs.py --a LABEL CSV [CSV ...] --b LABEL CSV [CSV ...] [--map-b 'sub:repl'] [--ids-file F] [--out FILE]
Rows are read per id; all reps of an id must agree with each other (else the id is reported as 'reps disagree'); for A or B with several
files (e.g. X11 r1/r2/r3) use --b once per baseline with --b-name. Prints a summary and every differing id with the pairs only in A / only in B."""
import argparse, csv, re, sys
csv.field_size_limit(1 << 30)

def load(files, ren=None):
    d = {}
    for f in files:
        for r in csv.DictReader(open(f, newline="")):
            if r.get("mode", "collector-only") not in ("collector-only", "collector-only-chain"):
                continue
            i = r["id"]
            if ren:
                i = re.sub(*ren, i)
            m = re.search(r"(?:^|;)classes=([^;]*)", r["notes"])
            d.setdefault(i, []).append(dict(verdict=r["verdict"], pairs=frozenset(r["report_ids"].split()),
                                              lines=frozenset(x for x in r["report_lines"].split(";") if x), classes=m.group(1) if m else "",
                                              n=r["reports_dedup"], note=r["notes"]))
    return d

def key(x): return (x["verdict"], x["pairs"], x["lines"], x["classes"])

def one(rows):
    ks = {key(x) for x in rows if x["verdict"] not in ("TIMEOUT", "ERROR")}
    return (rows[0], len(ks) <= 1) if rows else (None, True)

def compare(A, B, label_a, label_b, out):
    ids = sorted(set(A) & set(B)); diff = []; dis = []
    for i in ids:
        a, oka = one(A[i]); b, okb = one(B[i])
        if not oka or not okb: dis.append((i, "reps disagree in " + ("A" if not oka else "B"))); continue
        if a["verdict"] in ("TIMEOUT", "ERROR") or b["verdict"] in ("TIMEOUT", "ERROR"):
            dis.append((i, f"no verdict: {label_a}={a['verdict']} {label_b}={b['verdict']}")); continue
        if key(a) != key(b): diff.append((i, a, b))
    print(f"{label_a} vs {label_b}: ids compared {len(ids)} (only in A {len(set(A)-set(B))}, only in B {len(set(B)-set(A))}); pair set EQUAL {len(ids)-len(diff)-len(dis)}, DIFFER {len(diff)}, not comparable {len(dis)}", file=out)
    for i, a, b in diff:
        strip = lambda ps: {p.rsplit(':', 1)[0] for p in ps}
        kind = "same pc pairs, class differs (RAW/WAR/WAW direction)" if strip(a['pairs']) == strip(b['pairs']) else "pc-pair set differs"
        print(f"  DIFFER[{kind}] {i}: verdict {a['verdict']} vs {b['verdict']}; classes {a['classes']} vs {b['classes']}; |pairs| {len(a['pairs'])} vs {len(b['pairs'])}", file=out)
        print(f"    only in {label_a}: {sorted(a['pairs']-b['pairs'])[:12]}", file=out)
        print(f"    only in {label_b}: {sorted(b['pairs']-a['pairs'])[:12]}", file=out)
        if a['lines'] != b['lines']: print(f"    lines only A {sorted(a['lines']-b['lines'])[:6]} only B {sorted(b['lines']-a['lines'])[:6]}", file=out)
    for i, why in dis: print(f"  NOT-COMPARABLE {i}: {why}", file=out)
    return len(diff)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", nargs="+", required=True); ap.add_argument("--b", nargs="+", required=True)
    ap.add_argument("--map-a"); ap.add_argument("--map-b"); ap.add_argument("--ids-file")
    a = ap.parse_args()
    la, fa = a.a[0], a.a[1:]; lb, fb = a.b[0], a.b[1:]
    ra = tuple(a.map_a.split(":", 1)) if a.map_a else None; rb = tuple(a.map_b.split(":", 1)) if a.map_b else None
    A, B = load(fa, ra), load(fb, rb)
    if a.ids_file:
        keep = {l.strip() for l in open(a.ids_file)}; A = {k: v for k, v in A.items() if k in keep}; B = {k: v for k, v in B.items() if k in keep}
    sys.exit(1 if compare(A, B, la, lb, sys.stdout) else 0)
