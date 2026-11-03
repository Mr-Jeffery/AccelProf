#!/usr/bin/env python
"""C6b step 0: why C6 (collector-only + chain closure) judged the P5-race_interblock_none-lock_rtraw pair
ORDERED while scalar-clock reported it.  Read-only: wraps sync_dominance's HBGraph methods with loggers."""
import glob, json, os, sys
B = "/mnt/beegfs/fzheng4/cuvein_traces"
PROG = "P5-race_interblock_none-lock_rtraw"
W = os.environ.get("RTRAW_PYHOME", os.environ["CUVEIN_HOME"])
sys.path.insert(0, W + "/python")
import sync_dominance as sd
print("sync_dominance from", sd.__file__)

for store in ("final-2026-11-co", "final-2026-11"):
    d = f"{B}/{store}/{PROG}"
    print("== ls", d)
    for root, ds, fs in os.walk(d):
        for f in sorted(fs):
            p = os.path.join(root, f)
            print("  ", p[len(d):], os.path.getsize(p))

def find(store, mode, pat):
    r = sorted(glob.glob(f"{B}/{store}/{PROG}/**/{pat}", recursive=True))
    return [p for p in r if mode in p or p.endswith(".dot")]

LOG = []
def wrap(cls, name, fmt):
    orig = getattr(cls, name)
    def w(self, *a, **k):
        r = orig(self, *a, **k)
        LOG.append((name, fmt(self, a, r)))
        return r
    setattr(cls, name, w)
H = lambda x: hex(x) if isinstance(x, int) else x
def hl(l): return None if l is None else [H(x) for x in l]
wrap(sd.HBGraph, "_past_release", lambda s, a, r: f"_past_release(acq={H(a[0])}, cur={H(a[1])}) -> {r}"
     + (f"  [acq opcode {s.pc_opcode.get(a[0])}, cur opcode {s.pc_opcode.get(a[1])}]" if a[0] is not None else ""))
wrap(sd.HBGraph, "_before_acquire", lambda s, a, r: f"_before_acquire(u={H(a[0])}, rel={H(a[1])}) -> {r}")
wrap(sd.HBGraph, "chain", lambda s, a, r: f"chain(anc={H(a[0])}, cur={H(a[1])}) -> {hl(r)}; release_points={ {H(k):hl(sorted(v)) for k,v in (s.release_points or {}).items()} if s.release_points is not None else None}; acquire_points={ {H(k):hl(sorted(v)) for k,v in (s.acquire_points or {}).items()} if s.acquire_points is not None else None}")
wrap(sd.HBGraph, "ordered", lambda s, a, r: f"ordered(cur={H(a[0])}, anc={H(a[1])}, d={a[2]}) -> strength={r['strength']} syncs={r['syncs']} coh={r['coherence']} chain={hl(r['chain'])}")

def run(label, store, mode):
    kj = find(store, mode, "kernel_*.json")
    dot = find(store, mode, "*.dot")
    print(f"\n######## {label}: store={store} mode={mode}\n kernel jsons: {kj}\n dots: {dot}")
    if not kj or not dot:
        print(" (missing)"); return
    for k in kj:
        trace = json.load(open(k))
        print(" keys:", list(trace.keys()), "kernel:", trace.get("kernel"))
        print(" nodes:")
        for n in trace.get("nodes", []): print("   ", n)
        print(" edges:")
        for e in trace.get("edges", []): print("   ", e)
        ev = trace.get("hb_events")
        print(" hb_events:", None if ev is None else (len(ev) if hasattr(ev, "__len__") else type(ev)))
        LOG.clear()
        rep = sd.analyze(dot[0], k, chain_closure=(mode == "collector-only"))
        print(" diagnostics:", json.dumps(rep["diagnostics"])[:1500])
        print(" verdicts:")
        for v in rep.get("verdicts", []):
            print("   ", json.dumps(v))
        print(" skipped:", rep.get("skipped"))
        print(" analysis log (chain / _past_release / _before_acquire / ordered):")
        for n, m in LOG: print("   ", m)
    return dot[0]

d_co = run("C6 collector-only (+closure)", "final-2026-11-co", "collector-only")
for mode in ("scalar-clock",):
    run("scalar-clock", "final-2026-11", mode)
# the CFG: instructions (pc: opcode) of the kernel, and the dot text
if d_co:
    print("\n######## DOT", d_co)
    print(open(d_co).read())
    mangled, eng = sd.kernel_graph(d_co, json.load(open(find("final-2026-11-co","collector-only","kernel_*.json")[0]))["kernel"]["kernel_name"])
    print("pc_opcode:")
    for pc in sorted(eng.pc_opcode): print(f"   {pc:#x} {eng.pc_opcode[pc]}")

# ---- P6-memcpy-shared_readwrite_race-racy (F4): the collector-only recording's pc 0x70 / 0x90 / 0xa0
P6 = "P6-memcpy-shared_readwrite_race-racy"
print("\n######## P6", P6)
for store, mode in (("final-2026-11-co", "collector-only"), ("final-2026-11", "scalar-clock")):
    kjs = sorted(glob.glob(f"{B}/{store}/{P6}/**/kernel_*.json", recursive=True))
    dots = sorted(glob.glob(f"{B}/{store}/{P6}/**/*.dot", recursive=True))
    print(f"-- {store} {mode}: {kjs} {dots}")
    for k in kjs:
        t = json.load(open(k))
        print(" kernel:", t.get("kernel", {}).get("kernel_name"), "keys:", list(t.keys()))
        for n in t.get("nodes", []): print("   node", n)
        for e in t.get("edges", []): print("   edge", e)
        ev = t.get("hb_events")
        print(" hb_events:", None if ev is None else len(ev))
        if ev:
            for e in list(ev)[:12]: print("   ev", e)
            kinds = {}
            for e in ev:
                kk = e.get("kind") or e.get("type") or e.get("op") if isinstance(e, dict) else str(e)[:20]
                kinds[kk] = kinds.get(kk, 0) + 1
            print("   event kinds:", kinds)
    if dots:
        mg, eg = sd.kernel_graph(dots[0], json.load(open(kjs[0]))["kernel"]["kernel_name"])
        for pc in (0x70, 0x90, 0xa0):
            print(f"   pc {pc:#x}: {eg.pc_opcode.get(pc)}")
