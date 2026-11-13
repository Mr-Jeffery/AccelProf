| program | size | mode | N | wall (s, counter on) | native (s) | peak RSS (MB) | rc | timed out | job |
|---|---|---|---|---|---|---|---|---|---|
| atomicCAS | r100 | collector-only | 16 | 33.454 | 3.643 | 1067.8 | 0 | False | 340799 |
| atomicCAS | r200 | collector-only | 16 | 44.165 | 3.67 | 1138.1 | 0 | False | 340799 |
| bfs | 1M | collector-only | 16 | 3.469 | 0.715 | 1277.4 | 0 | False | 340799 |
| bfs | 1M | scalar-clock | 16 | 5.424 | 0.716 | 2756.6 | 0 | False | 340799 |
| bfs | 500K | collector-only | 16 | 2.168 | 0.466 | 1100.2 | 0 | False | 340799 |
| bfs | 500K | scalar-clock | 16 | 3.924 | 0.616 | 1779.0 | 0 | False | 340799 |
| pathfinder | R1000 | collector-only | 16 | 647.121 | 1.166 | 2098.4 | 0 | False | 340799 |
| pathfinder | R100 | collector-only | 16 | 7.824 | 0.266 | 1064.5 | 0 | False | 340799 |
| pathfinder | R10 | collector-only | 16 | 0.866 | 0.223 | 962.5 | 0 | False | 340799 |
| pathfinder | R200 | collector-only | 16 | 27.846 | 0.365 | 1180.6 | 0 | False | 340799 |
| pathfinder | R20 | collector-only | 16 | 1.067 | 0.215 | 972.6 | 0 | False | 340799 |
| stencil1d | L10 | collector-only | 16 | 309.52 | 0.516 | 4612.9 | 0 | False | 340799 |
| stencil1d | L10 | scalar-clock | 16 | 90.793 | 0.466 | 122562.4 | 1 | False | 340799 |
| stencil1d | L20 | collector-only | 16 | 608.514 | 0.516 | 4623.4 | 0 | False | 340799 |
| stencil1d | L20 | scalar-clock | 16 | 104.559 | 0.666 | 122607.7 | 1 | False | 340799 |
