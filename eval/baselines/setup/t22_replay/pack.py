#!/usr/bin/env python3
"""T22 replay, step 1: a kernel_N.json with hb_events -> a binary record file that replay.cpp feeds
through libsanalyzer (yosemite_kernel_start / gpu_data_analysis / kernel_end) exactly as the
collector's drains would, so one recorded trace runs through HbClock at any YOSEMITE_HB_SHARDS.

Each event becomes the MemoryAccess fields HbClock reads: type, block (ctaId), warp, pc,
active_mask, accessSize (barrier thread_count, syncwarp sync_mask, pipeline_wait groups, memory
size), flags (barrier bar_index; memory WRITE for "write", ATOMIC alone for "atomic" -- the
offline pass reads an atomic whose pc the sidecar does not list as a read, so no WRITE bit),
the active lanes' addresses in lane order. Events are written in dump order (= HbClock's order).

  pack.py <kernel_N.json> <out.bin>
Format (little-endian): b"T22R", u32 1, u32 len, name, u32 grid[3], u32 block[3], u64 nrec;
per record: u8 type, 3 pad, u32 warp, u64 block, u32 pc, u32 mask, u32 size, u32 flags, then
popcount(mask) u64 addresses for a memory record.
"""
import json
import struct
import sys

TYPE = {"read": None, "write": None, "atomic": None,   # memory: 0 global / 1 shared
        "exit": 3, "barrier": 4, "syncwarp": 5, "pipeline_commit": 6, "pipeline_wait": 7}
WRITE, ATOMIC = 0x2, 0x4


def main(src, dst):
    t = json.load(open(src))
    k = t["kernel"]
    ev = t.get("hb_events")
    if not ev:
        sys.exit(f"{src}: no hb_events")
    name = k["kernel_name"].encode()
    with open(dst, "wb") as f:
        f.write(b"T22R" + struct.pack("<II", 1, len(name)) + name)
        f.write(struct.pack("<6I", *k["grid_dim"], *k["block_dim"]))
        f.write(struct.pack("<Q", len(ev)))
        hdr = struct.Struct("<BxxxIQIIII")
        for e in ev:
            typ = e["type"]
            mask = e.get("active_mask", 0)
            size = flags = 0
            addrs = ()
            if typ in ("read", "write", "atomic"):
                code = 1 if e["space"] == "shared" else 0
                size = e["size"]
                flags = WRITE if typ == "write" else ATOMIC if typ == "atomic" else 0
                addrs = [l["addr"] for l in e["lanes"]]
                lanes = [l["lane"] for l in e["lanes"]]
                if lanes != [i for i in range(32) if mask >> i & 1]:
                    sys.exit(f"{src}: seq {e['seq']}: lanes do not match the active mask")
            else:
                code = TYPE[typ]
                if typ == "barrier":
                    size, flags = e["thread_count"], e["bar_index"]
                elif typ == "syncwarp":
                    size = e["sync_mask"]
                elif typ == "pipeline_wait":
                    size = e["groups"]
            f.write(hdr.pack(code, e["warp"], e["block"], e["pc"], mask, size, flags))
            if addrs:
                f.write(struct.pack(f"<{len(addrs)}Q", *addrs))
    print(f"{src} -> {dst}: {len(ev)} records")


if __name__ == "__main__":
    main(*sys.argv[1:3])
