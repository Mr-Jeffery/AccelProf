#!/usr/bin/env python3
"""TOOLS_ON_STREAMK attribution: every report of every tool on the four reproducer variants, mapped to source.
Line info: runs/<exe>.lineinfo.txt (nvdisasm -c --print-line-info-inline of the cubins cuobjdump -xelf extracts from the
executable; one kernel function). An offset maps to the frames of the //## File block that precedes its instruction
(one frame per line, innermost first).
  racecheck : `RACECHECK SUMMARY` of runs/racecheck-<id>.txt (hazard lines listed if any)
  iGUARD    : `Race: <kind>` + the next location line (`... Sass offset N - (TID t, addr)`) of runs/iguard-<id>-iguard_rep1.txt;
              reps 2 and 3 compared on the set of (kind, offset)
  cuRace    : raw (+ raw_sc) records of confirm/<s2|scalar-clock>/<id>__cuvein__<mode>.json, a_pc / b_pc mapped
Site of one access: PAIR-STORE (producer's partial store/reduce: block_striped.h:194, functional.h:943/963/992),
PAIR-LOAD (consumer's partial load: functional.h:134/177/202, block_striped.h:165), FLAG (any barrier.h frame),
else OTHER. A cuRace report (a pair) is `pair` when one end is PAIR-STORE and the other PAIR-LOAD, `flag` when an end
is FLAG; an iGUARD report (one access) is `pair` when it is PAIR-STORE or PAIR-LOAD.
usage: x9_tools_attr.py <tools_streamk dir>  -> <dir>/attribution.tsv, summary on stdout"""
import collections, glob, json, os, re, sys
D = sys.argv[1]; R = f"{D}/runs"
STORE = {"block_striped.h:194", "functional.h:943", "functional.h:963", "functional.h:992"}
LOAD = {"functional.h:134", "functional.h:177", "functional.h:202", "block_striped.h:165"}
FILE_RE = re.compile(r'File "([^"]+)", line (\d+)')
OFF_RE = re.compile(r"/\*([0-9a-f]{4,})\*/")
def lineinfo(exe):
    m, cur, pend = {}, [], False
    for ln in open(f"{R}/{exe}.lineinfo.txt", errors="replace"):
        if "//## File" in ln:
            if not pend: cur = []
            pend = True
            x = FILE_RE.findall(ln)                  # one frame per line, innermost first; `inlined at` = the next line
            if x: cur.append(f"{os.path.basename(x[0][0])}:{x[0][1]}")
            continue
        o = OFF_RE.search(ln)
        if o:
            pend = False
            m[int(o.group(1), 16)] = cur
    return m
LI = {e: lineinfo(e) for e in ("repro", "repro_fixed")}
def site(fr):
    if any(f.startswith("barrier.h:") for f in fr): return "FLAG"
    if fr and fr[0] in STORE: return "PAIR-STORE"
    if fr and fr[0] in LOAD: return "PAIR-LOAD"
    return "OTHER"
out = ["tool\tid\tkind\tinstr_or_space\ta_offset\ta_frames\ta_site\tb_offset\tb_frames\tb_site\tcount\tcategory"]
summ = collections.defaultdict(collections.Counter)
ids = [l.split(",")[0] for l in open(f"{D}/manifest.csv").read().split("\n")[1:] if l]
for i in ids:
    exe = "repro_fixed" if "fixed" in i else "repro"; li = LI[exe]
    rc = open(f"{R}/racecheck-{i}.txt", errors="replace").read()
    s = re.findall(r"RACECHECK SUMMARY: (\d+) hazards", rc)
    summ[("racecheck", i)][f"hazards={s[-1] if s else '?'}"] += 1
    txt = open(f"{R}/iguard-{i}-iguard_rep1.txt", errors="replace").read().split("\n")
    sets = []
    for rep in (1, 2, 3):
        t = open(f"{R}/iguard-{i}-iguard_rep{rep}.txt", errors="replace").read().split("\n")
        cur = set()
        for k, ln in enumerate(t):
            if ln.startswith("Race: ") and k + 1 < len(t):
                o = re.search(r"Sass offset (\d+)", t[k + 1]); cur.add((ln[6:].strip(), int(o.group(1)) if o else -1, t[k + 1].split(" ;")[0].strip()))
        sets.append(cur)
    agg = collections.Counter()
    for kind, off, ins in sets[0]:
        fr = li.get(off, ["?"]); st = site(fr)
        cat = {"PAIR-STORE": "pair", "PAIR-LOAD": "pair", "FLAG": "flag"}.get(st, "other")
        agg[(kind, ins.split()[0], off, ";".join(fr), st, cat)] += 1
        summ[("iGUARD", i)][cat] += 1
    for (kind, op, off, fr, st, cat), n in sorted(agg.items(), key=lambda x: x[0][2]):
        out.append(f"iGUARD\t{i}\t{kind}\t{op}\t{off}\t{fr}\t{st}\t\t\t\t{n}\t{cat}")
    summ[("iGUARD", i)]["reps_same_sites"] = int(sets[0] == sets[1] == sets[2])
    for mode, sub, suf in (("cuRace S2", "s2", "collector-only"), ("cuRace scalar-clock", "scalar-clock", "scalar-clock")):
        d = json.load(open(f"{D}/confirm/{sub}/{i}__cuvein__{suf}.json"))
        agg = collections.Counter()
        for r in d["raw"] + [dict(x, _sc=1) for x in d.get("raw_sc", [])]:
            fa, fb = li.get(r["a_pc"], ["?"]), li.get(r["b_pc"], ["?"]); sa, sb = site(fa), site(fb)
            cat = "pair" if {sa, sb} == {"PAIR-STORE", "PAIR-LOAD"} else "flag" if "FLAG" in (sa, sb) else "other"
            agg[(("SC " if r.get("_sc") else "") + f"{r.get('conflict_class')} {r.get('race_type')}", r.get("space"),
                 fa[0], ";".join(fa), sa, fb[0], ";".join(fb), sb, cat)] += 1
            summ[(mode, i)][cat] += 1
            if fa[0] != d.get("pc_lines", {}).get(str(r["a_pc"]), fa[0]) or fb[0] != d.get("pc_lines", {}).get(str(r["b_pc"]), fb[0]):
                summ[(mode, i)]["LINEINFO-MISMATCH"] += 1
        for (k, sp, a0, fa, sa, b0, fb, sb, cat), n in sorted(agg.items()):
            out.append(f"{mode}\t{i}\t{k}\t{sp}\t{a0}\t{fa}\t{sa}\t{b0}\t{fb}\t{sb}\t{n}\t{cat}")
open(f"{D}/attribution.tsv", "w").write("\n".join(out) + "\n")
for k in sorted(summ): print(k[0], k[1], dict(summ[k]))
