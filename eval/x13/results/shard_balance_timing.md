| program | size | mode | native (s) | N=1 wall (s) | N=16 wall (s), counter off | speed-up N=1 / N=16 | N=16 wall (s), counter on | counter-on / counter-off | N=16 peak RSS (MB, off) | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| atomicCAS | r100 | collector-only | 3.7 | 33.1 | 32.8 | 1.01x | 33.5 | 1.02x | 1,134.0 |  |
| atomicCAS | r200 | collector-only | 3.7 | 44.0 | 44.0 | 1.00x | 44.2 | 1.00x | 1,134.5 |  |
| bfs | 1M | collector-only | 0.7 | 3.3 | 2.8 | 1.20x | 3.5 | 1.25x | 1,265.2 |  |
| bfs | 1M | scalar-clock | 0.7 | 17.1 | 4.6 | 3.73x | 5.4 | 1.18x | 2,721.2 |  |
| bfs | 500K | collector-only | 0.5 | 2.0 | 1.9 | 1.08x | 2.2 | 1.16x | 1,097.2 |  |
| bfs | 500K | scalar-clock | 0.6 | 7.5 | 3.5 | 2.12x | 3.9 | 1.11x | 1,779.2 |  |
| pathfinder | R1000 | collector-only | 1.2 | missing | missing | missing | 647.1 | missing | missing |  |
| pathfinder | R100 | collector-only | 0.3 | missing | missing | missing | 7.8 | missing | missing |  |
| pathfinder | R10 | collector-only | 0.2 | 0.8 | 0.8 | 1.00x | 0.9 | 1.06x | 961.7 |  |
| pathfinder | R200 | collector-only | 0.4 | missing | missing | missing | 27.8 | missing | missing |  |
| pathfinder | R20 | collector-only | 0.2 | 1.0 | 1.0 | 1.05x | 1.1 | 1.10x | 967.5 |  |
| stencil1d | L10 | collector-only | 0.5 | 180.0 | 100.0 | 1.80x | 309.5 | 3.10x | 4,138.3 |  |
| stencil1d | L10 | scalar-clock | 0.5 | missing | missing | missing | missing | missing | 122,422.8 | N=16: rc=1 timed_out=False (peak 122422.8 MB); counter on: rc=1 timed_out=False (peak 122562.4 MB) |
| stencil1d | L20 | collector-only | 0.5 | 354.0 | 198.4 | 1.78x | 608.5 | 3.07x | 4,095.7 |  |
| stencil1d | L20 | scalar-clock | 0.7 | missing | missing | missing | missing | missing | missing | counter on: rc=1 timed_out=False (peak 122607.7 MB) |
