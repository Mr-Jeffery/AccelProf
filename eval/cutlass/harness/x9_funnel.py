#!/usr/bin/env python3
"""X9 report §2 funnel from the roll-up (summary.json of x9_summarize.py) and the triage rules of
eval/cutlass/triage/{splitk,streamk,new_groups}.md, applied per deduped group by its two innermost CUTLASS frames:
  S2  barrier.h flag pairs (SC)                       -> not (a)  [morally strong; streamk.md S2]
  K1  semaphore.h pairs (SC)                           -> not (a)  [splitk.md K1]
  S1b one side a finisher/reduction read of the stream-K workspace (functional.h:134/177/202, complex.h:202,
      block_striped.h:165)                             -> (a) DR   [streamk.md S1b: GenericBarrier::wait_eq_reset]
  S1a block_striped.h:194 store x peer atomic reduce (functional.h:943/963/992) -> (b)
  K   split-K serial epilogue accesses (arch/memory.h, predicated_tile_iterator.h, epilogue_direct_store.h) -> (b)
Anything else -> UNCLASSIFIED (printed; must be 0).
usage: x9_funnel.py <summary.json> [<groups out tsv>]"""
import json, sys, collections
S = json.load(open(sys.argv[1]))
READ = {"include/cutlass/functional.h:134", "include/cutlass/functional.h:177", "include/cutlass/functional.h:202",
        "include/cutlass/complex.h:202", "include/cutlass/block_striped.h:165"}
RED = {"include/cutlass/functional.h:943", "include/cutlass/functional.h:963", "include/cutlass/functional.h:992"}
def klass(a, b):
    f = {a, b}
    if any("barrier.h" in x for x in f): return "S2", "not (a)"
    if any("semaphore.h" in x for x in f): return "K1", "not (a)"
    if f & READ: return "S1b", "(a)"
    if "include/cutlass/block_striped.h:194" in f and f & RED: return "S1a", "(b)"
    if all(("arch/memory.h" in x or "predicated_tile_iterator.h" in x or "epilogue_direct_store.h" in x) for x in f):
        return "K", "(b)"
    return "?", "UNCLASSIFIED"
fam = collections.defaultdict(lambda: collections.Counter())
rows = []
for g in S["groups"]:
    c, k = klass(g["a"], g["b"])
    fam[g["family"]]["groups"] += 1
    fam[g["family"]][k] += 1
    fam[g["family"]]["pairs_" + k] += int(g["pairs"])
    rows.append((g["family"], g["a"], g["b"], g["pairs"], g["kernels"], c, k))
print("family\tfiles\tpairs\tCONFIRMED\tBARRIER-ORDERED\tRECLASSIFIED\tON-ONLY\tgroups\t(a)\t(b)\tnot(a)\tUNCLASSIFIED\tpairs(a)")
for f, s in sorted(S["families"].items()):
    st = s.get("status", s)
    tot = sum(int(st.get(x, 0)) for x in ("CONFIRMED", "BARRIER-ORDERED", "RECLASSIFIED"))
    t = fam[f]
    print(f"{f}\t{s.get('files','')}\t{tot}\t{st.get('CONFIRMED',0)}\t{st.get('BARRIER-ORDERED',0)}\t{st.get('RECLASSIFIED',0)}\t"
          f"{st.get('ON-ONLY',0)}\t{t['groups']}\t{t['(a)']}\t{t['(b)']}\t{t['not (a)']}\t{t['UNCLASSIFIED']}\t{t['pairs_(a)']}")
for r in rows:
    if r[-1] == "UNCLASSIFIED": print("UNCLASSIFIED", *r)
if len(sys.argv) > 2:
    with open(sys.argv[2], "w") as o:
        o.write("family\tframe_a\tframe_b\tpairs\tkernels\tcluster\tclass\n")
        for r in rows: o.write("\t".join(map(str, r)) + "\n")
