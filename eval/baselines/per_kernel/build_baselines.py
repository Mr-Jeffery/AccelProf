#!/usr/bin/env python3
"""X13 step 3: racecheck / iGUARD / HiRace / SuperCollider reports -> kernels, then the per-kernel verdict of each tool.
racecheck, SuperCollider: file:line -> kernel through nvdisasm --print-line-info of the binary the tool ran (lm/*.csv, linemap.py).
iGUARD: the kernel name it prints ("- Kernel <name>: Sass offset"). HiRace: single-kernel Indigo 1.3 codes (checked against the
cubin inventory). Outputs baselines.csv (one row per tool, run id, reported location, kernel) and kernel_verdicts_baselines.csv."""
import collections, csv, glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tinput, kfold
mt, runs, meta, man, p9 = tinput.load()
APH = tinput.APH
D = f"{APH}/eval/results/per-kernel"
nk = lambda s: s.replace(" ", "")
NAT = "/home/fzheng4/AccelProf/eval/baselines/setup/tools/supercollider/supercollider-artifacts/bin/hecbench/native"
# cubin kernels and line map
dem = {}                               # (exe, mangled) -> demangled nk
cub = collections.defaultdict(dict)    # exe -> {nk: display}
for r in csv.DictReader(open(f"{D}/cubin_kernels.csv")):
    if r["status"] == "ok" and r["is_entry"] == "1":
        dem[(r["exe"], r["mangled"])] = nk(r["demangled"])
        cub[r["exe"]][nk(r["demangled"])] = r["demangled"]
lmap = collections.defaultdict(set)    # (exe, file, line) -> {kernel nk}
lmap_fn = collections.defaultdict(set)
for f in glob.glob(f"{D}/lm/lm-*.csv"):
    for r in csv.DictReader(open(f)):
        if r["status"] == "ok" and (r["exe"], r["kernel"]) in dem:
            lmap[(r["exe"], r["file"], int(r["line"]))].add(dem[(r["exe"], r["kernel"])])
nat_exe = lambda prog: f"{NAT}/{prog}"
rows_out = []
status_c = collections.Counter()

def kernels_for_lines(exe, lines):
    """lines: 'file:line' tokens -> ({kernel}, [(token, status)])"""
    ks, st = set(), []
    for tok in lines:
        m = re.match(r"(.+):(\d+)$", tok)
        if not m:
            st.append((tok, "unparsed")); continue
        c = lmap.get((exe, os.path.basename(m.group(1)), int(m.group(2))), set())
        if not c:
            st.append((tok, "unmapped"))
        elif len(c) > 1:
            st.append((tok, "ambiguous:" + "|".join(sorted(c)))); ks |= c
        else:
            st.append((tok, "unique")); ks |= c
    return ks, st

def iguard_kernels(ids_text):
    return set(nk(x) for x in re.findall(r"-Kernel(.+?):(?:Sassoffset\d+|Line\d+)", ids_text.replace(" ", "")) ) | set(
        nk(x) for x in re.findall(r"- Kernel (.+?): Sass offset \d+", ids_text))

# X11 stage-B tool rows for P9 (new_verdict rows with 'new:' sources)
x11rows = collections.defaultdict(list)
for f in glob.glob(f"{APH}/eval/x_logs/x11/stageB/x11b-*/racecheck.csv") + glob.glob(f"{APH}/eval/x_logs/x11/stageB/x11b-*/iguard.csv"):
    tool = "racecheck" if f.endswith("racecheck.csv") else "iguard"
    prog = re.search(r"x11b-(?:racecheck|iguard)-([A-Za-z0-9]+)-r\d", f).group(1)
    for r in csv.DictReader(open(f)):
        x11rows[(prog, tool)].append(r)
# full iGUARD logs of X11 (cut at 2,000 characters in the CSV)
LOGS = {}
for p in ("atomicCAS", "mr", "knn", "dxtc2", "expdist", "tridiagonal"):
    for r in (1, 2, 3):
        for ff in glob.glob(f"/mnt/beegfs/fzheng4/x11_work/iguard_logs/x11b-iguard-{p}-r{r}/X11-{p}/iguard_rep*.txt"):
            LOGS.setdefault(p, []).append(ff)
SCL = {}
for r in csv.DictReader(open(f"{D}/sc_rerun_lines.csv")) if os.path.exists(f"{D}/sc_rerun_lines.csv") else []:
    SCL.setdefault(r["id"], []).append(r)

# binaries
bin_ids = collections.defaultdict(list)
for i, m in man.items():
    if m["pset"] in ("P1", "PI", "P4", "P6", "P9") and m.get("exe"):
        bin_ids[m["exe"]].append(i)
cur = collections.defaultdict(lambda: collections.defaultdict(set))   # binary -> mode -> kernels (universe)
for r in csv.DictReader(open(f"{D}/curace.csv")):
    cur[r["binary"]]["all"].add(nk(r["kernel"]))
SCP = {r["id"]: r for r in []}
kv_rows = []
notes = []
for exe, ids in sorted(bin_ids.items()):
    pset = man[ids[0]]["pset"]
    prog = man[ids[0]]["program"][:-5] if pset == "P9" else None
    key_b = f"hecbench:{prog}" if prog else exe
    label = man[ids[0]]["label"].upper()
    univ = cur[key_b]["all"] or set(cub.get(exe, {}))
    vws = [v for v in ("P1", "PI", "PI@sc7", "P4", "P6@in", "P9") if set(mt.binary_view_ids(meta, v)) & set(ids)]
    if pset == "P6":
        vws = vws + (["P6"] if "P6" not in vws else [])
    for tool in ("racecheck", "iguard", "hirace", "supercollider"):
        rl = []
        for i in ids:
            rv = runs.get((i, tool, ""))
            if not rv:
                continue
            V = rv["verdict"]
            rep_k, detail = set(), []
            lines = rv.get("report_lines", "").split() if rv.get("report_lines") else []
            if pset == "P9":
                s = p9[(prog, tool)]
                new = "new:" in s["source_files"]
                if tool in ("racecheck", "iguard") and new:
                    rr = x11rows[(prog, tool)]
                    lines = sorted({l for r in rr for l in r["report_lines"].split()})
                    ids_text = " ".join(r["report_ids"] for r in rr)
                    exe_used = nat_exe(prog + "")
                    if tool == "iguard" and LOGS.get(prog):
                        ids_text += " " + " ".join(open(ff, errors="replace").read() for ff in LOGS[prog])
                        detail.append("iguard-full-log")
                    elif tool == "iguard":
                        detail.append("iguard-csv-only")
                    V = {"TO": "TIMEOUT"}.get(s["new_verdict"], s["new_verdict"])
                else:
                    exe_used = exe
                    ids_text = rv.get("report_ids", "")
                if tool == "supercollider":
                    exe_used = nat_exe(prog)
                    sid = f"P9-{prog}-cuda"
                    if sid in SCL:
                        fns = {r["function"] for r in SCL[sid]}
                        sl = {(r["file"].split("/")[-1], r["line"]) for r in SCL[sid]}
                        lines = sorted(f"{a}:{b}" for a, b in sl)
                        # function-name resolution: atomic_{min,max,add}P<t><t> -> atomic{Min,Max,Add}Derived<type>; fill_shared_mem_tiled_1D<..,T> -> distance<T>
                        for fn in fns:
                            m1 = re.match(r"_Z10atomic_(min|max|add)P(y|x|d)\2$", fn)
                            m2 = re.match(r"_Z24fill_shared_mem_tiled_1DILi4ELi8E(d|f)", fn)
                            if m1:
                                op = {"min": "Min", "max": "Max", "add": "Add"}[m1.group(1)]
                                ty = {"y": "unsignedlonglong", "x": "longlong", "d": "double"}[m1.group(2)]
                                cand = [k for k in cub.get(exe_used, {}) if k.startswith(f"voidatomic{op}Derived<{ty}>")]
                                rep_k |= set(cand); detail.append(f"{fn}->{cand}")
                            if m2:
                                ty = {"d": "double", "f": "float"}[m2.group(1)]
                                cand = [k for k in cub.get(exe_used, {}) if k.startswith(f"voiddistance<{ty}>")]
                                rep_k |= set(cand); detail.append(f"{fn}->{cand}")
                        lines = []
                    elif V == "RACE" and not lines and prog == "dxtc2":
                        rep_k |= set(cub.get(exe_used, {}))          # single-kernel binary (compress): not from a log line
                        detail.append("single-kernel-binary(no-log-lines)")
            else:
                exe_used = exe
                ids_text = rv.get("report_ids", "")
                if tool == "supercollider" and pset == "PI":
                    pass
            if V == "RACE":
                if tool == "iguard":
                    names = iguard_kernels(ids_text)
                    for n_ in names:
                        # match by normalised name against the cubin list of the binary the tool ran
                        c = [k for k in cub.get(exe_used, {}) if k == n_ or k.replace("void", "", 1) == n_ or ("void" + n_) == k]
                        if c: rep_k |= set(c)
                        else: detail.append("iguard-name-unmatched:" + n_[:60])
                elif tool == "hirace":
                    ks = set(cub.get(exe, {}))
                    if len(ks) == 1: rep_k |= ks; detail.append("single-kernel-code")
                    else: detail.append(f"hirace-multi-kernel:{len(ks)}")
                elif tool in ("racecheck", "supercollider"):
                    if tool == "supercollider" and pset == "PI":
                        ks = set(cub.get(exe, {}))
                        if len(ks) == 1: rep_k |= ks; detail.append("single-kernel-code")
                    elif lines:
                        ks, st = kernels_for_lines(exe_used, lines)
                        rep_k |= ks
                        for t, s_ in st:
                            if s_ != "unique": detail.append(f"{t}:{s_}")
                    elif tool == "racecheck" and pset == "P9" and prog == "expdist" and not lines:
                        # X11 racecheck rows for expdist carry no file:line; the report text names the device function
                        # distance_tiled<T>, which only distance<T> calls (6a8c46c4 kernel.h:101-113)
                        txt = " ".join(r["notes"] for r in x11rows[(prog, tool)])
                        for ty in sorted(set(re.findall(r"distance_tiled<(double|float)", txt))):
                            cand = [k for k in cub.get(exe_used, {}) if k.startswith(f"voiddistance<{ty}>")]
                            rep_k |= set(cand); detail.append(f"distance_tiled<{ty}>->{cand}")
                    elif not rep_k and not any(d.startswith(("single", "fn", "distance_tiled")) for d in detail):
                        detail.append("race-without-lines")
            for k in sorted(rep_k):
                rows_out.append([tool, i if pset != "P9" else f"P9:{prog}", key_b, k, ";".join(sorted(lines))[:200], ";".join(detail)[:300]])
            if "ambiguous" in ";".join(detail) or "unmapped" in ";".join(detail) or "race-without-lines" in detail or "unmatched" in ";".join(detail):
                notes.append((tool, key_b, i, ";".join(detail)[:300]))
            launched = set(univ) if V in ("RACE", "CLEAN") else set()
            rl.append(dict(id=i, verdict=V, launched=launched, reporting=rep_k))
            if pset == "P9":
                break           # one folded entry per program (the CSV row of the program)
        if not rl:
            continue
        kvd = kfold.fold_kernels(rl, univ)
        for kn, v in kvd.items():
            kv_rows.append([key_b, ";".join(vws), label, cub.get(exe, {}).get(kn, kn), tool, "", v])
        # fold-back vs the binary verdict
        want = mt.fold_verdict([r["verdict"] for r in rl])
        if want != kfold.fold_back(kvd):
            notes.append((tool, key_b, "fold-back", f"binary={want} kernels={kfold.fold_back(kvd)}"))

def w(path, hdr, rows):
    with open(path, "w", newline="") as f:
        cw = csv.writer(f); cw.writerow(hdr); cw.writerows(rows)
w(f"{D}/baselines.csv", ["tool", "run", "binary", "kernel", "reported_locations", "method_detail"], rows_out)
w(f"{D}/kernel_verdicts_baselines.csv", ["binary", "views", "binary_label", "kernel", "tool", "mode", "verdict"], kv_rows)
w(f"{D}/baselines_notes.csv", ["tool", "binary", "run", "note"], notes)
c = collections.Counter(n[0] + ":" + ("fold-back" if n[2] == "fold-back" else n[3].split(":")[-1][:20]) for n in notes)
print(len(rows_out), "report rows;", len(notes), "notes", dict(c.most_common(12)))
