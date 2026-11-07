#!/usr/bin/env python3
"""T26 parity: synthetic capture streams (capture_shim.cpp's T26C format) for the paths a recorded
program rarely takes, replayed through the installed library and the new one (synth.sh).

    synth.py OUT.bin --seed S [--kernels K] [--records R]

Each stream holds tracked regions (one at a 4-byte but not 128-byte aligned start, one of odd size),
a region freed before a kernel touches it again (its addresses become untracked), untracked addresses,
and per kernel a mix of: global records with coalesced, strided, misaligned and segment-crossing lanes,
access sizes 0/1/2/4/8/12/16/32, repeat lanes (unique mask a proper subset of the active one), a first
active lane inside a region with other lanes outside it (the shadow's break), shared records with low
offsets, offsets past the per-object size and offsets that wrap 2^32, enough live blocks to exhaust a
32-object pool (run with YOSEMITE_GPU_SM_COUNT=1 YOSEMITE_GPU_MAX_ACTIVE_BLOCKS_PER_SM=1), block exits
that free objects for reuse, local records, barrier/syncwarp records, an unknown record type, block ids
above 2^22 (the flat thread id's truncation), and drains of varied sizes (below the inline threshold,
one chunk, several 32,768-record chunks).
"""
import argparse
import random
import struct

GLOBAL, SHARED, LOCAL, EXIT, BARRIER, SYNCWARP = 0, 1, 2, 3, 4, 5
FLAG_READ, FLAG_WRITE, FLAG_ATOMIC = 0x1, 0x2, 0x4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--kernels", type=int, default=4)
    ap.add_argument("--records", type=int, default=120000, help="records per kernel (about)")
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    f = open(a.out, "wb")
    f.write(b"T26C" + struct.pack("<I", 1))

    def tag(c):
        f.write(c.encode())

    regions = [(0x7F0000000000, 1 << 20), (0x7F0000200004, 777), (0x7F0000300000, 4096 + 3),
               (0x7F0000400000, 65536)]
    for p, s in regions:
        tag("A"); f.write(struct.pack("<QQii", p, s, 0, 0))
    freed = regions[3]
    unknown_base = 0x500000000000
    pcs = [0x10 * i for i in range(1, 40)]

    def rec(t, size, flags, warp, dsc, active, unique, cta, pc, addrs):
        out = struct.pack("<BIIIIIIQQ", t, size, flags, warp, dsc, active, unique, cta, pc)
        lanes = active | unique
        for l in range(32):
            if lanes >> l & 1:
                out += struct.pack("<Q", addrs.get(l, 0) & 0xFFFFFFFFFFFFFFFF)
        return out

    def unique_of(active, addrs):
        seen, u = set(), 0
        for l in range(32):
            if active >> l & 1 and addrs[l] not in seen:
                seen.add(addrs[l]); u |= 1 << l
        return u

    for k in range(a.kernels):
        if k == 2:   # free a region: later kernels' accesses to it are untracked
            tag("F"); f.write(struct.pack("<QQii", freed[0], freed[1], 0, 0))
        grid, bdim = rnd.choice([(48, 128), (100, 64), (7, 256)])
        warps = bdim // 32
        name = f"synth_kernel_{k}".encode()
        tag("K"); f.write(struct.pack("<I", len(name)) + name + struct.pack("<i", 0)
                          + struct.pack("<6I", grid, 1, 1, bdim, 1, 1))
        big = rnd.random() < 0.5
        cta_ids = list(range(grid)) if not big else [(1 << 22) + 5 * i for i in range(grid)]
        recs = []
        live = {}
        for i in range(a.records):
            cta = rnd.choice(cta_ids)
            warp = rnd.randrange(warps)
            pc = rnd.choice(pcs)
            r = rnd.random()
            if r < 0.55:     # global
                size = rnd.choice([4, 4, 4, 8, 16, 0, 1, 2, 12, 32])
                where = rnd.random()
                if where < 0.55:
                    base, rs = regions[0]
                    start = base + rnd.randrange(0, rs - 4096) // 4 * 4
                elif where < 0.65:
                    base, rs = regions[1]
                    start = base + rnd.randrange(0, rs)
                elif where < 0.75:
                    base, rs = regions[2]
                    start = base + rnd.randrange(0, rs)
                elif where < 0.85:
                    base, rs = freed
                    start = base + rnd.randrange(0, rs - 4096)
                else:
                    start = unknown_base + rnd.randrange(0, 1 << 16)
                pat = rnd.random()
                stride = max(size, 1)
                addrs = {}
                for l in range(32):
                    if pat < 0.5:
                        addrs[l] = start + l * stride                    # coalesced
                    elif pat < 0.65:
                        addrs[l] = start + 2 + l * stride                # misaligned
                    elif pat < 0.8:
                        addrs[l] = start + (l % 4) * stride              # repeats
                    elif pat < 0.9:
                        addrs[l] = start + l * 128 + 120                 # crosses segments
                    else:
                        addrs[l] = start + rnd.randrange(-256, 8192)     # scattered, some out of region
                active = rnd.choice([0xFFFFFFFF, 0xFFFFFFFF, 0x0000FFFF, 0x80000001,
                                     rnd.getrandbits(32), 0])
                unique = unique_of(active, addrs)
                if rnd.random() < 0.02:
                    unique = rnd.getrandbits(32) & active
                flags = rnd.choice([FLAG_READ, FLAG_WRITE, FLAG_ATOMIC | FLAG_WRITE | FLAG_READ])
                dsc = rnd.randrange(0, 34)
                recs.append(rec(GLOBAL, size, flags, warp, dsc, active, unique, cta, pc, addrs))
            elif r < 0.82:   # shared
                size = rnd.choice([4, 4, 8, 16, 0, 2])
                pat = rnd.random()
                if pat < 0.7:
                    start = rnd.randrange(0, 3000) // 4 * 4
                elif pat < 0.85:
                    start = 4096 - 64 + rnd.randrange(0, 128)            # past the 4096-byte object
                else:
                    start = 0xFFFFFFF0 - rnd.randrange(0, 64)            # wraps 2^32
                addrs = {l: (0x7E0000000000 | ((start + l * max(size, 1)) & 0xFFFFFFFF)) for l in range(32)}
                if rnd.random() < 0.3:
                    addrs = {l: addrs[l % 8] for l in range(32)}
                active = rnd.choice([0xFFFFFFFF, 0x0000FFFF, rnd.getrandbits(32), 0])
                unique = unique_of(active, addrs)
                flags = rnd.choice([FLAG_READ, FLAG_WRITE])
                recs.append(rec(SHARED, size, flags, warp, rnd.randrange(0, 34), active, unique, cta, pc, addrs))
                live[cta] = True
            elif r < 0.86:
                recs.append(rec(LOCAL, 4, FLAG_WRITE, warp, 1, 0xFFFFFFFF, 0xFFFFFFFF, cta, pc,
                                {l: 0xFFFC00 + 4 * l for l in range(32)}))
            elif r < 0.9:
                recs.append(rec(rnd.choice([BARRIER, SYNCWARP]), 0, 0, warp, 0, 0xFFFFFFFF, 0, cta, pc, {}))
            elif r < 0.9005:
                recs.append(rec(9, 4, FLAG_READ, warp, 1, 0x1, 0x1, cta, pc, {0: unknown_base}))
            else:            # a warp exits (a block's object is freed when all its threads exited)
                mask = rnd.choice([0xFFFFFFFF, 0x0000FFFF])
                recs.append(rec(EXIT, 0, 0, warp, 0, mask, 0, cta, 0, {}))
        # drains of varied sizes
        i = 0
        while i < len(recs):
            n = rnd.choice([1, 100, 3000, 4095, 4096, 32768, 40000, 70000, 100000])
            chunk = recs[i:i + n]
            tag("D"); f.write(struct.pack("<Q", len(chunk)))
            f.write(b"".join(chunk))
            i += n
        tag("E"); f.write(struct.pack("<I", len(name)) + name + struct.pack("<i", 0))
    tag("X")
    f.close()


if __name__ == "__main__":
    main()
