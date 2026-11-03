#!/usr/bin/env python3
"""X8: time / peak RSS / fiber count of one oracle run (one schedule seed) at the manifest row's launch.
  measure_row.py <manifest id> [seed]   (builds the oracle binary like oracle_pi.build if absent)"""
import csv, os, re, resource, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oracle_pi
mid = sys.argv[1]; seed = sys.argv[2] if len(sys.argv) > 2 else "0"
m = next(r for r in csv.DictReader(open(f"{oracle_pi.HERE}/../manifest.csv")) if r["id"] == mid)
os.makedirs(oracle_pi.BIN, exist_ok=True)
err = oracle_pi.build(m["monitored_kernels"], m["program"])
print("build:", err or "ok", flush=True)
g, tpb, nb = m["args"].split()
n, e = [int.from_bytes(open(g, "rb").read(8)[i:i + 4], "little") for i in (0, 4)]
eb = min(int(nb), max(n, e)); fibers = eb * int(tpb)
t0 = time.time()
p = subprocess.run([f"{oracle_pi.BIN}/{m['program']}", g, tpb, nb, seed], capture_output=True, text=True, timeout=14400)
wall = time.time() - t0
ru = resource.getrusage(resource.RUSAGE_CHILDREN)
line = next((l for l in p.stdout.splitlines() if l.startswith("ORACLE")), p.stdout[-200:])
print(f"{mid} nodes={n} edges={e} launch={tpb}x{nb} fibers={fibers} wall_s={wall:.1f} peak_rss_gb={ru.ru_maxrss / 1048576:.2f} rc={p.returncode} :: {line[:160]}")
