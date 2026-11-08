| program | records | verdict N=16 / C1 | N=16: wall s | native s | slowdown | µs/rec | peak MB | C1 `-n 1`: wall s | native s | slowdown | µs/rec | peak MB | wall speed-up |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| stencil1d | 85,983,231,000 | CLEAN / CLEAN | 9,079.5 | 4.722 | 1,922.8 | 0.106 | 4,169 | 36,373.3 | 4.774 | 7,619.1 | 0.423 | 4,240 | 4.0x |
| particlefilter | 22,515,702,514 | RACE / RACE | 1,488.3 | 1.269 | 1,172.8 | 0.066 | 2,053 | 3,200.2 | 1.171 | 2,732.9 | 0.142 | 1,152 | 2.2x |
| heartwall | 8,071,484,636 | RACE / RACE | 1,106.5 | 0.769 | 1,438.8 | 0.137 | 1,259 | 2,347.6 | 0.769 | 3,052.7 | 0.291 | 988 | 2.1x |
| pathfinder | 7,058,581,010 | RACE / RACE | 623.3 | 1.470 | 424.0 | 0.088 | 2,018 | 702.4 | 1.470 | 477.9 | 0.100 | 2,023 | 1.1x |
| bitonic-sort | 1,226,469,735 | CLEAN / CLEAN | 649.3 | 37.036 | 17.5 | 0.529 | 1,433 | 635.3 | 31.940 | 19.9 | 0.518 | 1,379 | 1.0x |
| haversine | 629,145,600 | CLEAN / CLEAN | 113.4 | 3.123 | 36.3 | 0.180 | 2,465 | 227.4 | 3.123 | 72.8 | 0.361 | 2,307 | 2.0x |
| srad | 589,889,126 | RACE / RACE | 146.3 | 0.317 | 461.5 | 0.248 | 889 | 401.3 | 0.371 | 1,081.7 | 0.680 | 890 | 2.7x |
| lavaMD | 398,843,648 | CLEAN / CLEAN | 27.3 | 0.418 | 65.2 | 0.068 | 1,305 | 83.4 | 0.383 | 217.7 | 0.209 | 1,219 | 3.1x |
| mandelbrot | 327,687,360 | CLEAN / CLEAN | 101.7 | 2.272 | 44.7 | 0.310 | 915 | 162.4 | 3.825 | 42.5 | 0.496 | 876 | 1.6x |
| nbody | 320,355,120 | CLEAN / CLEAN | 33.7 | 12.142 | 2.8 | 0.105 | 969 | 59.9 | 14.570 | 4.1 | 0.187 | 867 | 1.8x |
| bezier-surface | 106,955,008 | CLEAN / CLEAN | 30.3 | 19.858 | 1.5 | 0.283 | 4,048 | 45.4 | 24.463 | 1.9 | 0.424 | 3,936 | 1.5x |
| hotspot | 37,410,000 | CLEAN / CLEAN | 10.8 | 0.669 | 16.2 | 0.290 | 890 | 21.5 | 0.518 | 41.5 | 0.575 | 875 | 2.0x |
| bfs | 7,436,165 | RACE / RACE | 4.5 | 1.420 | 3.2 | 0.609 | 1,180 | 4.8 | 1.069 | 4.5 | 0.649 | 1,004 | 1.1x |
| backprop | 1,232,901 | CLEAN / CLEAN | 1.0 | 0.268 | 3.6 | 0.786 | 922 | 1.7 | 0.268 | 6.2 | 1.355 | 902 | 1.7x |

- N=16: geomean slowdown 51.5 (n=14); median µs/record 0.214; peak RSS median 1,282 MB, max 4,169 MB; median serial floor 0.156 µs
- C1 `-n 1`: geomean slowdown 93.5 (n=14); median µs/record 0.424; peak RSS median 1,078 MB, max 4,240 MB; median serial floor 0.390 µs
- fit wall = a + b x records (N=16, n=14): a = 22.0 s, b = 0.1030 µs/record
- fit wall = a + b x records (C1 -n 1, n=14): a = -577.9 s, b = 0.4114 µs/record
- wall speed-up C1/N=16: geomean 1.84x, min 0.98x (bitonic-sort), max 4.01x (stencil1d)
- workers notes: ['16']; reps per program N=16: [3]; C1: [1, 3]
- records equal to C1: True; verdict equal to C1: True
- >=1e9 records (stencil1d, particlefilter, heartwall, pathfinder, bitonic-sort): N=16 geomean slowdown 474.8 vs C1 904.1; median µs/rec 0.106 vs 0.291
