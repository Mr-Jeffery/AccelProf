#!/usr/bin/env python3
"""TOOLS_ON_STREAMK, vector clock: the reports of confirm/vector-clock/<id>__cuvein__vector-clock.json mapped to source with
the same line info and site rules as x9_tools_attr.py (runs/<exe>.lineinfo.txt; PAIR-STORE / PAIR-LOAD / FLAG / OTHER).
The dossier's pair: store block_striped.h:194 with SK:772 (split 2) or SK:989 (split 3) among its frames, load
functional.h:134 (split 2) or block_striped.h:165 (split 3) as the innermost frame.
usage: x9_tools_vc_attr.py <tools_streamk dir> -> <dir>/attribution_vc.tsv, summary on stdout"""
import collections, csv, glob, json, os, re, sys
D = sys.argv[1]; R = f"{D}/runs"
STORE = {"block_striped.h:194", "functional.h:943", "functional.h:963", "functional.h:992"}
LOAD = {"functional.h:134", "functional.h:177", "functional.h:202", "block_striped.h:165"}
FILE_RE = re.compile(r'File "([^"]+)", line (\d+)'); OFF_RE = re.compile(r"/\*([0-9a-f]{4,})\*/")
def lineinfo(exe):
    m, cur, pend = {}, [], False
    for ln in open(f"{R}/{exe}.lineinfo.txt", errors="replace"):
        if "//## File" in ln:
            if not pend: cur = []
            pend = True
            x = FILE_RE.findall(ln)
            if x: cur.append(f"{os.path.basename(x[0][0])}:{x[0][1]}")
            continue
        o = OFF_RE.search(ln)
        if o: pend = False; m[int(o.group(1), 16)] = cur
    return m
LI = {e: lineinfo(e) for e in ("repro", "repro_fixed")}
def site(fr):
    if any(f.startswith("barrier.h:") for f in fr): return "FLAG"
    if fr and fr[0] in STORE: return "PAIR-STORE"
    if fr and fr[0] in LOAD: return "PAIR-LOAD"
    return "OTHER"
DOSSIER = {"s2": ("gemm_universal_streamk.h:772", "functional.h:134"), "s3": ("gemm_universal_streamk.h:989", "block_striped.h:165")}
out = ["id\tkind\tspace\ta_pc\ta_frames\ta_site\tb_pc\tb_frames\tb_site\tcount\tcategory\tdossier_pair"]
ids = [l.split(",")[0] for l in open(f"{D}/manifest.csv").read().split("\n")[1:] if l]
for i in ids:
    exe = "repro_fixed" if "fixed" in i else "repro"; li = LI[exe]; sk, ld = DOSSIER[i[-2:]]
    d = json.load(open(f"{D}/confirm/vector-clock/{i}__cuvein__vector-clock.json"))
    c = collections.Counter(); dp = set(); mism = 0
    for r in d["raw"] + [dict(x, _sc=1) for x in d.get("raw_sc", [])]:
        fa, fb = li.get(r["a_pc"], ["?"]), li.get(r["b_pc"], ["?"]); sa, sb = site(fa), site(fb)
        cat = "pair" if {sa, sb} == {"PAIR-STORE", "PAIR-LOAD"} else "flag" if "FLAG" in (sa, sb) else "other"
        st, lo = (fa, fb) if sa == "PAIR-STORE" else (fb, fa)
        dos = cat == "pair" and st[0] == "block_striped.h:194" and sk in st and lo[0] == ld
        if dos: dp.add((r["a_pc"], r["b_pc"]))
        c[cat] += 1; c["dossier"] += dos
        if fa[0] != d.get("pc_lines", {}).get(str(r["a_pc"]), fa[0]) or fb[0] != d.get("pc_lines", {}).get(str(r["b_pc"]), fb[0]): mism += 1
        out.append(f"{i}\t{('SC ' if r.get('_sc') else '')}{r.get('conflict_class')} {r.get('race_type')}\t{r.get('space')}\t{r['a_pc']}\t"
                   f"{';'.join(fa)}\t{sa}\t{r['b_pc']}\t{';'.join(fb)}\t{sb}\t{r.get('count', '')}\t{cat}\t{int(dos)}")
    keys = [k for k in d if k not in ("raw", "raw_sc", "pc_lines")]
    print(i, dict(c), "dossier_pc_pairs", len(dp), "lineinfo_mismatch", mism, "| verdict", d.get("verdict"), d.get("status"), "| keys", keys[:20])
open(f"{D}/attribution_vc.tsv", "w").write("\n".join(out) + "\n")
for f in sorted(glob.glob(f"{D}/../../results/cutlass/tools_streamk/vector-clock/*.csv")):
    for row in csv.DictReader(open(f)):
        print(os.path.basename(f), {k: row[k] for k in list(row)[:14]})
