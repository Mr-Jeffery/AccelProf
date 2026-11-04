#!/usr/bin/env python3
"""C6b step 3: assert_no_hb.txt. (1) the dynamic result of the guarded loader over the three runs (probes/*.jsonl of every run),
(2) the strip report, (3) a static grep of `hb_` literals in the modules the collector-only path imports."""
import collections
import glob
import json
import os
import re

W = "/home/fzheng4/wt-c6b"
O = f"{W}/eval/results/co-chain-b/step3"
STORE = "/mnt/beegfs/fzheng4/c6b-step3/store"
L = []
P = L.append

P("# assert_no_hb: no hb_* key reaches the collector-only verdict layer (step 3)\n")
# ---- (1) strip report
sr = json.load(open(f"{STORE}/strip_report.json"))
tot = collections.Counter()
for r in sr:
    tot.update(r["removed"])
P("## 1. Stripped copy (c6b_s3_strip.py)")
P(f"ids {len(sr)}, kernel JSONs {sum(r['kernels'] for r in sr)}, bytes in {sum(r['bytes_in'] for r in sr)}, bytes out {sum(r['bytes_out'] for r in sr)}, "
  f"errors {sum(1 for r in sr if r['err'])}, ids without a scalar-clock directory {sum(1 for r in sr if r['no_sc_dir'])}.")
P("hb_* keys deleted (dicts at any depth; each file is re-walked after deletion and asserted to hold none):")
for k, v in sorted(tot.items()):
    P(f"  {k}: {v}")
nested = {k: v for k, v in tot.items() if k.startswith("nested:")}
P(f"nested hb_* keys (below the top level) deleted outside the removed top-level subtrees: {sum(nested.values())}\n")

# ---- (2) dynamic
P("## 2. Guarded loader, dynamic result over the three runs")
P("Every kernel JSON is parsed with an object_hook that raises HbGuardError on a dict holding an hb_* key, and into a dict subclass whose")
P("__getitem__/get/__contains__/pop/setdefault raise on an hb_* key that is PRESENT. A probe of an ABSENT hb_* key is counted per call site (the")
P("unmodified verdict layer probes such keys on every dump, collector-only recordings included; the answer is the key-absent default).\n")
allsite = collections.Counter()
for st in ("s1", "s2", "cfg"):
    calls = reads = 0
    probes = collections.Counter()
    for fn in glob.glob(f"{O}/run-{st}/**/probes-*.jsonl", recursive=True):
        for ln in open(fn):
            j = json.loads(ln)
            calls += 1
            reads += j["reads"]
            for k, n in j["probes"].items():
                probes[k] += n
    allsite.update(probes)
    P(f"run {st}: sd.analyze calls {calls}; value reads / hb keys present in memory (assert == 0): {reads}; probes of absent hb_* keys: {sum(probes.values())}")
    for k, n in sorted(probes.items()):
        P(f"    {k}: {n}")
P("")
P("Strict demonstration (S3_STRICT=1, P5-canary, one worker): the unmodified analysis raises at its first probe of an absent key -> "
  "strict mode cannot be run through to a verdict without changing sync_dominance.py:")
try:
    for ln in open(f"{O}/strict-demo/baselines-cuvein-shardstrictall.csv").read().splitlines()[1:]:
        P("    " + ln.split(",")[-1])
except OSError as e:
    P(f"    (strict demo file missing: {e})")
P("")

# ---- (3) static
P("## 3. Static grep: hb_ literals in the modules the collector-only path imports")
local = {}
for d in (f"{W}/python", f"{W}/eval/baselines", f"{W}/eval"):
    for p in glob.glob(f"{d}/*.py"):
        local.setdefault(os.path.basename(p)[:-3], p)
queue, seen = ["parallel", "run_cuvein", "blib", "sync_dominance"], []
while queue:
    m = queue.pop(0)
    if m in seen or m not in local:
        continue
    seen.append(m)
    for ln in open(local[m], errors="replace"):
        mm = re.match(r"\s*(?:from|import)\s+([A-Za-z_]\w*)", ln)
        if mm and mm.group(1) in local:
            queue.append(mm.group(1))
P("modules (transitive local imports from parallel.py / run_cuvein.py / blib.py / sync_dominance.py): " + ", ".join(f"{m}.py" for m in seen))
KEY = re.compile(r"""(\.get\(\s*["']hb_\w*|\[\s*["']hb_\w*["']\s*\]|["']hb_\w*["']\s+(?:not\s+)?in\s)""")
PFX = re.compile(r"""startswith\(\s*["']hb_""")
rows = collections.defaultdict(list)
text_lines = collections.Counter()
for m in seen:
    for n, ln in enumerate(open(local[m], errors="replace"), 1):
        if "hb_" not in ln:
            continue
        rel = os.path.relpath(local[m], W)
        s = ln.strip()
        if s.startswith("#"):
            text_lines[rel] += 1
        elif KEY.search(ln):
            rows["key read / probe"].append((rel, n, s))
        elif PFX.search(ln):
            rows["prefix test (dump detection)"].append((rel, n, s))
        else:
            text_lines[rel] += 1      # docstring, comment tail, identifier containing hb_ (hb_modes ...), string
for cat in ("prefix test (dump detection)", "key read / probe"):
    P(f"\n### {cat}: {len(rows[cat])} lines")
    for rel, n, s in rows[cat]:
        P(f"  {rel}:{n}: {s[:170]}")
P("\nother lines mentioning hb_ (comments, docstrings, identifiers such as hb_modes / hb_class / hb_chain): " +
  ", ".join(f"{k} {v}" for k, v in sorted(text_lines.items())))
static_sites = {(rel.split("/")[-1], n) for rel, n, _ in rows["key read / probe"] + rows["prefix test (dump detection)"]}
dyn_sites = {tuple(k.split("|")[0].rsplit(":", 1)) for k in allsite}
dyn_sites = {(a, int(b)) for a, b in dyn_sites}
P(f"\nCross-check: dynamic probe sites {len(dyn_sites)}; of them in the static key-read/prefix list: {len(dyn_sites & static_sites)}; "
  f"not in it: {sorted(dyn_sites - static_sites)}")
P(f"Static key-read lines never probed in the three runs: {sorted(static_sites - dyn_sites)}")
open(f"{O}/assert_no_hb.txt", "w").write("\n".join(L) + "\n")
print("\n".join(L[:60]))
