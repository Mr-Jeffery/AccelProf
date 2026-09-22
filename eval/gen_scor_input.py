#!/usr/bin/env python3
"""Generate deterministic stdin inputs for the ScoR benchmark apps (E0).

Each app reads its whole input from stdin (cin/scanf). Two sizes per app:
'small' (fits the exact hb_oracle) and 'large' (engine-only). Writes files to
the given out dir as <app>.<size>.in.

    python eval/gen_scor_input.py --out /abs/inputs
"""
import argparse
import os
import random

random.seed(1234)


def rints(n, lo=0, hi=100):
    return " ".join(str(random.randint(lo, hi)) for _ in range(n))


def rfloats(n):
    return " ".join(f"{random.random():.3f}" for _ in range(n))


def edges(V, E):
    # simple undirected graph, lowest-index vertex first (u<v), no dups/self-loops
    # (the ScoR graph codes require "lowest index vertex first"). Seed a path so the
    # graph is connected, then add random extra edges up to E.
    seen = set()
    out = []
    for i in range(min(E, V - 1)):          # connecting path 0-1-2-...
        seen.add((i, i + 1)); out.append(f"{i} {i+1}")
    while len(out) < E:
        u = random.randint(0, V - 2)
        v = random.randint(u + 1, V - 1)
        if (u, v) not in seen:
            seen.add((u, v)); out.append(f"{u} {v}")
    return "\n".join(out)


def gen(app, size):
    small = size == "small"
    if app == "reduction":                      # size \n <size ints>
        n = 4096 if small else 1 << 20
        return f"{n}\n{rints(n, 0, 9)}\n"
    if app == "1dconv":                          # filterSize arraySize \n filt \n arr
        fs, asz = 5, (1024 if small else 1 << 20)
        return f"{fs} {asz}\n{rfloats(fs)}\n{rfloats(asz)}\n"
    if app in ("graph-coloring", "graph-connectivity"):   # V E \n E*(u v)
        # small kept tiny: these codes are iterative (many kernel launches), so the
        # traced event stream balloons with graph size; a small graph converges fast.
        V, E = (64, 96) if small else (2048, 12000)
        return f"{V} {E}\n{edges(V, E)}\n"
    if app == "matrix-multiplication":           # rA cA cB \n A \n B
        r = c = k = 32 if small else 256
        return f"{r} {c} {k}\n{rints(r*c, 0, 9)}\n{rints(c*k, 0, 9)}\n"
    if app == "rule-110":                        # size steps \n <size 0/1>
        n, steps = (1024, 16) if small else (1 << 16, 64)
        return f"{n} {steps}\n" + " ".join(random.choice("01") for _ in range(n)) + "\n"
    if app == "uts":                             # maxHeight avgChildren \n seed
        h, ch = (4, 4) if small else (6, 6)
        return f"{h} {ch}\n42\n"
    raise SystemExit(f"unknown app {app}")


APPS = ["reduction", "1dconv", "graph-coloring", "graph-connectivity",
        "matrix-multiplication", "rule-110", "uts"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    for app in APPS:
        for size in ("small", "large"):
            path = os.path.join(args.out, f"{app}.{size}.in")
            with open(path, "w") as f:
                f.write(gen(app, size))
            print(f"wrote {path} ({os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    main()
