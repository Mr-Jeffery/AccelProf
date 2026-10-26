#!/usr/bin/env python3
"""Cell-by-cell comparison of two make_tables.py outputs (X1's committed eval/BASELINES*.md against
X1b's eval/results/final-b/tables/BASELINES*.md).

Every markdown table is matched by (section heading path, table number within the section, header).
A row is keyed by its first cell (a blank first cell inherits the one above, as the per-suite tables
leave it blank on the second mode's row), widened to the first two or three cells when that is not
unique; a table whose rows stay non-unique is compared as a multiset of rows. Text outside tables is
compared line by line per section. The listing "First 2000 of N disagreement rows" (BASELINES.md §3)
is skipped: which rows it shows follows the CSV's row order, which follows the directory order of
eval/results; the CSVs themselves are compared as multisets of rows (--csv).

  compare_tables.py <old.md> <new.md> [<old2.md> <new2.md> ...] \
      [--csv <old.csv> <new.csv> <group col,...> ...] > out.md
"""
import collections
import csv
import difflib
import sys


def split_row(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def parse(path):
    """-> (tables, prose): tables = [(section, k, header, rows)], prose = {section: [lines]}."""
    lines = open(path, encoding="utf-8").read().split("\n")
    heads, tables, prose = [], [], {}
    i, count = 0, {}
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("#"):
            lvl = len(ln) - len(ln.lstrip("#"))
            heads = [h for h in heads if h[0] < lvl] + [(lvl, ln.strip("# ").strip())]
            i += 1
            continue
        sec = " > ".join(h[1] for h in heads) or "(top)"
        if ln.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: ") \
                and lines[i + 1].startswith("|"):
            header = split_row(ln)
            j, rows = i + 2, []
            while j < len(lines) and lines[j].startswith("|"):
                rows.append(split_row(lines[j]))
                j += 1
            k = count.get(sec, 0)
            count[sec] = k + 1
            tables.append((sec, k, header, rows))
            i = j
            continue
        if ln.strip():
            prose.setdefault(sec, []).append(ln)
        i += 1
    return tables, prose


def keyed(rows):
    filled, last = [], ""
    for r in rows:
        r = list(r)
        if r and not r[0]:
            r[0] = last
        elif r:
            last = r[0]
        filled.append(r)
    for width in (1, 2, 3):
        keys = [tuple(r[:width]) for r in filled]
        if len(set(keys)) == len(keys):
            return dict(zip(keys, rows)), width
    return {(f"row {n + 1}",): r for n, r in enumerate(rows)}, 0


def cell_diff(a, b):
    """Short description of a changed cell; long cells (notes) by their changed fragments."""
    if len(a) <= 160 and len(b) <= 160:
        return f"`{a}` → `{b}`"
    ta = [x for x in a.replace("<br>", "; ").split("; ") if x]
    tb = [x for x in b.replace("<br>", "; ").split("; ") if x]
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=ta, b=tb, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        old = "; ".join(ta[i1:i2])
        new = "; ".join(tb[j1:j2])
        out.append(f"`{old or '—'}` → `{new or '—'}`")
    return "; ".join(out) if out else "(whitespace only)"


def compare(old, new, out):
    ot, op = parse(old)
    nt, np_ = parse(new)
    out.append(f"## `{new}` against `{old}`\n")
    om = {(s, k, tuple(h)): rows for s, k, h, rows in ot}
    nm = {(s, k, tuple(h)): rows for s, k, h, rows in nt}
    summary = []
    for key in [k for k in om if k in nm] + [k for k in nm if k not in om]:
        sec, k, header = key
        if key not in om:
            summary.append((sec, k, "only in the new file", 0, 0))
            out.append(f"### {sec} — table {k + 1}: only in the new file\n")
            continue
        if sec.endswith("3. Disagreements") and header[:2] == ("program", "tool_a"):
            summary.append((sec, k, "listing skipped (order-dependent; see the CSV comparison)", 0, 0))
            continue
        orows, rw = keyed(om[key])
        nrows, _ = keyed(nm[key])
        if rw == 0:
            co = collections.Counter(tuple(r) for r in om[key])
            cn = collections.Counter(tuple(r) for r in nm[key])
            gone, added = co - cn, cn - co
            summary.append((sec, k, f"{len(om[key])} rows (multiset)", 0, 0, sum(gone.values()), sum(added.values())))
            if gone or added:
                out.append(f"### {sec} — table {k + 1} ({len(om[key])} rows, compared as a multiset)\n")
                for r, n in gone.items():
                    out.append(f"- only in the old file ({n}×): `{' | '.join(r)[:400]}`")
                for r, n in added.items():
                    out.append(f"- only in the new file ({n}×): `{' | '.join(r)[:400]}`")
                out.append("")
            continue
        changes = []
        for rk in [x for x in orows if x in nrows]:
            a, b = orows[rk], nrows[rk]
            for c in range(max(len(a), len(b))):
                ca = a[c] if c < len(a) else ""
                cb = b[c] if c < len(b) else ""
                if ca != cb:
                    col = header[c] if c < len(header) else f"col {c + 1}"
                    changes.append((rk, col, cell_diff(ca, cb)))
        gone = [x for x in orows if x not in nrows]
        added = [x for x in nrows if x not in orows]
        nrow = len({c[0] for c in changes})
        summary.append((sec, k, f"{len(orows)} rows", nrow, len(changes), len(gone), len(added)))
        if changes or gone or added:
            out.append(f"### {sec} — table {k + 1} ({len(orows)} rows; {nrow} changed, {len(changes)} cells"
                       + (f"; {len(gone)} rows only in the old file" if gone else "")
                       + (f"; {len(added)} rows only in the new file" if added else "") + ")\n")
            for rk, col, d in changes:
                out.append(f"- **{' / '.join(rk)}**, column *{col}*: {d}")
            for rk in gone:
                out.append(f"- row only in the old file: **{' / '.join(rk)}**")
            for rk in added:
                out.append(f"- row only in the new file: **{' / '.join(rk)}**")
            out.append("")
    for key in om:
        if key not in nm:
            out.append(f"### {key[0]} — table {key[1] + 1}: only in the old file\n")
    out.append("### Text outside tables\n")
    nprose = 0
    for sec in list(op) + [s for s in np_ if s not in op]:
        a, b = op.get(sec, []), np_.get(sec, [])
        if a == b:
            continue
        d = [l for l in difflib.unified_diff(a, b, lineterm="", n=0) if not l.startswith(("---", "+++", "@@"))]
        if d:
            nprose += 1
            out.append(f"- **{sec}**:")
            for l in d:
                out.append(f"  - {'old' if l[0] == '-' else 'new'}: {l[1:][:600]}")
    if not nprose:
        out.append("(no change)")
    out.append("")
    return summary


def compare_csv(old, new, group, out):
    """Multiset comparison of two CSVs: counts per group, then every row only on one side, by first column."""
    ro = list(csv.DictReader(open(old, newline="", encoding="utf-8")))
    rn = list(csv.DictReader(open(new, newline="", encoding="utf-8")))
    fields = list((ro or rn)[0].keys())
    co = collections.Counter(tuple(r.get(f, "") for f in fields) for r in ro)
    cn = collections.Counter(tuple(r.get(f, "") for f in fields) for r in rn)
    gone, added = co - cn, cn - co
    out.append(f"## `{new}` against `{old}` (rows as a multiset)\n")
    out.append(f"Rows: {len(ro)} → {len(rn)}; only in the old file {sum(gone.values())}, only in the new file "
               f"{sum(added.values())}, in both {sum((co & cn).values())}.\n")
    gi = [fields.index(c) for c in group]
    go = collections.Counter(tuple(t[i] for i in gi) for t in co.elements())
    gn = collections.Counter(tuple(t[i] for i in gi) for t in cn.elements())
    out.append(f"Rows per ({', '.join(group)}), groups whose count changed:\n")
    out.append("| " + " | ".join(group) + " | old | new | change |")
    out.append("|" + "---|" * (len(group) + 3))
    nch = 0
    for g in sorted(set(go) | set(gn)):
        if go[g] != gn[g]:
            nch += 1
            out.append("| " + " | ".join(g) + f" | {go[g]} | {gn[g]} | {gn[g] - go[g]:+d} |")
    if not nch:
        out.append("| (none) |" + " |" * (len(group) + 2))
    out.append("")
    byp = collections.defaultdict(lambda: [[], []])
    for t, n in gone.items():
        byp[t[0]][0].extend([t] * n)
    for t, n in added.items():
        byp[t[0]][1].extend([t] * n)
    out.append(f"Rows only on one side, by `{fields[0]}` ({len(byp)} values):\n")
    for p in sorted(byp):
        g_, a_ = byp[p]
        out.append(f"- **{p}**: {len(g_)} only old, {len(a_)} only new")
        for t in g_:
            out.append(f"  - old: `{','.join(t[1:])[:300]}`")
        for t in a_:
            out.append(f"  - new: `{','.join(t[1:])[:300]}`")
    out.append("")


def main():
    a = sys.argv[1:]
    csvs = []
    while "--csv" in a:
        k = a.index("--csv")
        csvs.append((a[k + 1], a[k + 2], a[k + 3].split(",")))
        a = a[:k] + a[k + 4:]
    out, summ = [], []
    for old, new in zip(a[0::2], a[1::2]):
        summ.append((new, compare(old, new, out)))
    for old, new, group in csvs:
        compare_csv(old, new, group, out)
    head = ["# X1 against X1b: make_tables.py outputs, cell by cell\n",
            "Generated by `compare_tables.py`. Per table: rows compared, rows with a changed cell, changed cells.\n"]
    for new, s in summ:
        head.append(f"**{new}**\n")
        head.append("| section | table | rows | rows changed | cells changed | rows only old / new |")
        head.append("|---|---|---|---|---|---|")
        for x in s:
            if len(x) == 5:
                head.append(f"| {x[0]} | {x[1] + 1} | {x[2]} | — | — | — |")
            else:
                head.append(f"| {x[0]} | {x[1] + 1} | {x[2]} | {x[3]} | {x[4]} | {x[5]} / {x[6]} |")
        head.append("")
    print("\n".join(head + out))


if __name__ == "__main__":
    main()
