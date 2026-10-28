#!/usr/bin/env python3
"""Driver input preparation for hecbench-dxtc2-1 (not kernel code): crop the repo's lena_std.ppm (P6, 512x512) and the matching
DXT1 reference lena_ref.dds to the top-left CROP x CROP pixels (multiple of 4).  DXT1 blocks are independent 4x4 tiles stored
row-major, so the cropped reference is exactly the corresponding blocks of the full reference.
usage: crop.py <lena_std.ppm> <lena_ref.dds> <out.ppm> <out_ref.dds> [CROP=32]"""
import sys

ppm, dds, out_ppm, out_dds = sys.argv[1:5]
crop = int(sys.argv[5]) if len(sys.argv) > 5 else 32
assert crop % 4 == 0

d = open(ppm, "rb").read()
# header: "P6\n<w> <h>\n255\n"
parts, pos = [], 0
while len(parts) < 4:
    while d[pos:pos + 1].isspace():
        pos += 1
    st = pos
    while not d[pos:pos + 1].isspace():
        pos += 1
    parts.append(d[st:pos])
pos += 1                                   # exactly one whitespace byte after maxval
assert parts[0] == b"P6" and parts[3] == b"255", parts
w, h = int(parts[1]), int(parts[2])
pix = d[pos:]
assert len(pix) == w * h * 3, (len(pix), w, h)
rows = [pix[(y * w) * 3:(y * w + crop) * 3] for y in range(crop)]
open(out_ppm, "wb").write(b"P6\n%d %d\n255\n" % (crop, crop) + b"".join(rows))

r = open(dds, "rb").read()
HDR = 128
assert len(r) == HDR + (w // 4) * (h // 4) * 8, len(r)
bw = w // 4
blocks = []
for by in range(crop // 4):
    for bx in range(crop // 4):
        o = HDR + (by * bw + bx) * 8
        blocks.append(r[o:o + 8])
open(out_dds, "wb").write(r[:HDR] + b"".join(blocks))
print("crop.py: %dx%d -> %dx%d, %d DXT1 blocks" % (w, h, crop, crop, len(blocks)))
