#!/usr/bin/env python3
"""T22 replay: synthetic traces for what the recorded corpus rarely exercises -- trace-validity
violations (the sharded pass monitors a block's records in one shard and must keep the serial
pass's first violation), R3's trace points around atomics (kept per warp chunk in one shard), and
random barrier / syncwarp / exit interleavings with non-coalesced lanes over global and shared
locations (sync pairs whose conflicts spread over shards). Output: pack.py's record format, one
file per case, and the sidecar (rmw pcs) for kernel `synth`; the reference is the serial pass on
the same file (YOSEMITE_HB_SHARDS=1), compared with cmp.py.

  synth.py <out dir> [--seeds N]
"""
import os
import random
import struct
import sys

NAME = "synth"
HDR = struct.Struct("<BxxxIQIIII")
GLOBAL, SHARED, EXIT, BARRIER, SYNCWARP = 0, 1, 3, 4, 5
WRITE, ATOMIC = 0x2, 0x4
RMW_PCS = (0x900, 0x910)


class Trace:
    def __init__(self, blocks, bthreads):
        self.grid, self.bt, self.recs = blocks, bthreads, []

    def mem(self, block, warp, pc, mask, addrs, space=GLOBAL, kind="read", size=4):
        flags = WRITE if kind == "write" else ATOMIC if kind == "atomic" else 0
        self.recs.append((space, warp, block, pc, mask, size, flags, addrs))

    def sync(self, typ, block, warp, pc, mask, size=0, flags=0):
        self.recs.append((typ, warp, block, pc, mask, size, flags, ()))

    def write(self, path):
        name = NAME.encode()
        with open(path, "wb") as f:
            f.write(b"T22R" + struct.pack("<II", 1, len(name)) + name)
            f.write(struct.pack("<6I", self.grid, 1, 1, self.bt, 1, 1))
            f.write(struct.pack("<Q", len(self.recs)))
            for typ, warp, block, pc, mask, size, flags, addrs in self.recs:
                f.write(HDR.pack(typ, warp, block, pc, mask, size, flags))
                if addrs:
                    assert len(addrs) == bin(mask).count("1")
                    f.write(struct.pack(f"<{len(addrs)}Q", *addrs))


FULL = 0xFFFFFFFF


def lanes(mask, base, stride=4):
    return [base + stride * i for i in range(32) if mask >> i & 1]


def tv_cases(out):
    # two violations in two blocks: block 3 exits twice (position 4), block 1 issues a read after
    # its exit (position 7); the serial pass keeps block 3's
    t = Trace(4, 64)
    for b in range(4):
        t.mem(b, 0, 0x100, FULL, lanes(FULL, 0x10000 + 0x100 * b))
    t.sync(EXIT, 3, 1, 0x200, FULL)
    t.sync(EXIT, 3, 1, 0x200, FULL)
    t.sync(EXIT, 1, 1, 0x200, FULL)
    t.mem(1, 1, 0x110, FULL, lanes(FULL, 0x20000))
    for b in (0, 2):
        t.mem(b, 1, 0x120, FULL, lanes(FULL, 0x10000))
    t.write(f"{out}/tv_two_blocks.bin")
    # the same violations in the other position order: block 1's first
    t = Trace(4, 64)
    t.sync(EXIT, 1, 1, 0x200, FULL)
    t.mem(1, 1, 0x110, FULL, lanes(FULL, 0x20000))
    t.sync(EXIT, 3, 1, 0x200, FULL)
    t.sync(EXIT, 3, 1, 0x200, FULL)
    t.write(f"{out}/tv_two_blocks_rev.bin")
    # pending at the end in two blocks (whole-block barriers half arrived), plus a completion-order
    # violation: block 2 warp 0 waits at barrier 0 and issues a write
    t = Trace(4, 64)
    t.sync(BARRIER, 0, 0, 0x300, FULL, 0, 0)
    t.sync(BARRIER, 3, 1, 0x300, FULL, 0, 0)
    t.sync(BARRIER, 2, 0, 0x300, FULL, 0, 0)
    t.mem(2, 0, 0x130, FULL, lanes(FULL, 0x30000), kind="write")
    t.write(f"{out}/tv_pending.bin")
    # pending at the end only (no record-time violation)
    t = Trace(5, 64)
    for b in (4, 1):
        t.sync(BARRIER, b, 0, 0x300, FULL, 0, 0)
    t.write(f"{out}/tv_pending_only.bin")
    # overfill: a counted barrier of 48 threads reached by two full warps (64 > 48)
    t = Trace(2, 64)
    t.sync(BARRIER, 1, 0, 0x310, FULL, 48, 1)
    t.sync(BARRIER, 1, 1, 0x310, FULL, 48, 1)
    t.write(f"{out}/tv_overfill.bin")


def random_case(out, seed, blocks=7, warps=4, phases=5):
    r = random.Random(seed)
    t = Trace(blocks, warps * 32)
    gpool = [0x40000 + 4 * i for i in range(48)] + [0x50000 + 128 * i for i in range(16)]
    # per warp: a list of ops per phase; then a barrier (the last phase: some warps exit first)
    prog = {}
    for b in range(blocks):
        for w in range(warps):
            ops = []
            for ph in range(phases):
                for j in range(r.randint(0, 4)):
                    ops.append(("mem", ph, j))
                if r.random() < 0.2:
                    ops.append(("syncwarp", ph))
                ops.append(("bar", ph))
            if r.random() < 0.3:          # an early exit before the last barrier
                ops = ops[:-1]
            ops.append(("exit",))
            prog[(b, w)] = ops
    pos = {k: 0 for k in prog}
    waiting = {}                          # (b, w) -> barrier phase
    exited = set()
    arrived = {}                          # (b, ph) -> set of warps
    live = [k for k in prog]
    while live:
        k = r.choice(live)
        b, w = k
        if k in waiting:
            live.remove(k)
            continue
        op = prog[k][pos[k]]
        pos[k] += 1
        if op[0] == "mem":
            ph, j = op[1], op[2]
            pc = 0x1000 + 0x40 * ph + 0x10 * j
            mask = FULL if r.random() < 0.7 else r.getrandbits(32) | 1
            n = bin(mask).count("1")
            atom = r.random() < 0.1
            if atom:
                pc = RMW_PCS[ph % 2]
                kind, space = "atomic", GLOBAL
                addrs = [gpool[r.randrange(4)]] * n
            else:
                kind = "write" if r.random() < 0.4 else "read"
                space = SHARED if r.random() < 0.4 else GLOBAL
                if space == SHARED:
                    base = 0x100 * r.randrange(4)
                    addrs = ([base + 4 * i for i in range(n)] if r.random() < 0.5
                             else [4 * r.randrange(96) for _ in range(n)])
                else:
                    addrs = ([gpool[(r.randrange(48) + i) % 48] for i in range(n)] if r.random() < 0.5
                             else [r.choice(gpool) for _ in range(n)])
            t.mem(b, w, pc, mask, addrs, space=space, kind=kind)
        elif op[0] == "syncwarp":
            t.sync(SYNCWARP, b, w, 0x2000 + op[1], FULL, FULL)
        elif op[0] == "bar":
            ph = op[1]
            t.sync(BARRIER, b, w, 0x3000 + 0x10 * ph, FULL, 0, 0)
            arrived.setdefault((b, ph), set()).add(w)
            waiting[k] = ph
            alive = {x for x in range(warps) if (b, x) not in exited}
            if arrived[(b, ph)] >= alive:
                for x in arrived[(b, ph)]:
                    waiting.pop((b, x), None)
                    if (b, x) not in exited and pos[(b, x)] < len(prog[(b, x)]) and (b, x) not in live:
                        live.append((b, x))
        else:
            t.sync(EXIT, b, w, 0x4000, FULL)
            exited.add(k)
            # an exit can complete the block's open barrier (exit-aware assembly)
            for (bb, ph), ws in arrived.items():
                if bb != b:
                    continue
                alive = {x for x in range(warps) if (b, x) not in exited}
                if ws and alive and ws >= alive:
                    for x in ws:
                        if waiting.get((b, x)) == ph:
                            waiting.pop((b, x))
                            if pos[(b, x)] < len(prog[(b, x)]) and (b, x) not in live:
                                live.append((b, x))
        if pos[k] >= len(prog[k]) and k in live:
            live.remove(k)
    t.write(f"{out}/random_{seed}.bin")


def main(out, seeds=20):
    os.makedirs(out, exist_ok=True)
    with open(f"{out}/atomic_scope.txt", "w") as f:
        f.write(f"# kernel {NAME}\n")
        for pc in RMW_PCS:
            f.write(f"{pc} 3 rmw {NAME}\n")
    tv_cases(out)
    for s in range(seeds):
        random_case(out, s)
    print(f"{out}: tv cases + {seeds} random traces")


if __name__ == "__main__":
    args = sys.argv[1:]
    seeds = int(args[args.index("--seeds") + 1]) if "--seeds" in args else 20
    main(args[0], seeds)
