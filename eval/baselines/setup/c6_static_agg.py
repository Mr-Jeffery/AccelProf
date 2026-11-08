import json, sys, collections
d = json.load(open(sys.argv[1]))
SZ = (1, 2, 4, 8, 16)
pcs = collections.defaultdict(lambda: collections.Counter())   # suite -> size -> (prog,kernel,pc) count
progs = collections.defaultdict(lambda: collections.Counter())  # suite -> size -> programs with such pc
nprog = collections.Counter()
other = collections.Counter()
deficit = collections.defaultdict(lambda: [0, 0, 0])  # suite -> [pcs with ndef>0, programs with any, total pcs]
local = collections.Counter()
seen = set()
for r in d["B"]:
    key = r["id"]
    if key in seen:      # same id in two stores: count once (first store)
        continue
    seen.add(key)
    s = r["suite"] if r["store"].startswith("final") else "RW"
    nprog[s] += 1
    have = set(); anydef = False
    for k, p in r["pcs"].items():
        if any("LOCAL" in f and "GLOBAL" not in f and "SHARED" not in f for f in p["flags"]):
            local[s] += 1
            continue
        for z in set(p["sizes"]):
            if z in SZ:
                pcs[s][z] += 1; have.add(z)
            else:
                other[(s, z)] += 1
        deficit[s][2] += 1
        if p.get("ndef", 0) > 0:
            deficit[s][0] += 1; anydef = True
    for z in have:
        progs[s][z] += 1
    if anydef:
        deficit[s][1] += 1
order = ["P1", "PI", "P3", "P4", "P5", "P6", "P7", "P9", "RW"]
print("| suite | programs | " + " | ".join(f"pcs {z} B (programs)" for z in SZ) + " | local-only pcs |")
print("|---|---|" + "---|" * len(SZ) + "---|")
tot = collections.Counter(); totp = collections.Counter()
for s in order:
    if s not in nprog: continue
    print(f"| {s} | {nprog[s]} | " + " | ".join(f"{pcs[s][z]:,} ({progs[s][z]:,})" for z in SZ) + f" | {local[s]:,} |")
    for z in SZ: tot[z] += pcs[s][z]; totp[z] += progs[s][z]
print(f"| all | {sum(nprog.values())} | " + " | ".join(f"{tot[z]:,} ({totp[z]:,})" for z in SZ) + f" | {sum(local.values()):,} |")
print("other sizes:", dict(other))
print("\ndeficit (expected words > observed edge words), non-local pcs: suite: pcs with deficit / pcs, programs with any")
for s in order:
    if s in deficit:
        a, b, c = deficit[s]
        print(f"{s}: {a:,} / {c:,} pcs, {b:,} programs")
