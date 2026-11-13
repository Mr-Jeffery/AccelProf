| program | size | pass | drained records | global | shared | local | barrier | block_exit | syncwarp | pipeline | sync-event fraction (barrier+exit+syncwarp+pipeline) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| atomicCAS | r100 | pcdep (collector-only) | 343,733,070 | 338,031,093 | 0 | 0 | 0 | 5,701,977 | 0 | 0 | 1.66 % |
| atomicCAS | r200 | pcdep (collector-only) | 352,750,137 | 342,132,968 | 0 | 0 | 0 | 10,617,169 | 0 | 0 | 3.01 % |
| bfs | 1M | pcdep (collector-only) | 7,436,165 | 6,301,003 | 0 | 0 | 0 | 1,135,162 | 0 | 0 | 15.27 % |
| bfs | 1M | pcdep (scalar-clock) | 7,436,165 | 6,301,003 | 0 | 0 | 0 | 1,135,162 | 0 | 0 | 15.27 % |
| bfs | 500K | pcdep (collector-only) | 3,826,287 | 3,248,640 | 0 | 0 | 0 | 577,647 | 0 | 0 | 15.10 % |
| bfs | 500K | pcdep (scalar-clock) | 3,826,287 | 3,248,640 | 0 | 0 | 0 | 577,647 | 0 | 0 | 15.10 % |
| pathfinder | R1000 | pcdep (collector-only) | 7,058,581,010 | 4,830,892 | 19,983,324 | 0 | 6,393,600,000 | 640,166,794 | 0 | 0 | 99.65 % |
| pathfinder | R100 | pcdep (collector-only) | 72,236,330 | 479,932 | 1,979,724 | 0 | 63,360,000 | 6,416,674 | 0 | 0 | 96.59 % |
| pathfinder | R10 | pcdep (collector-only) | 865,862 | 44,836 | 179,364 | 0 | 576,000 | 65,662 | 0 | 0 | 74.11 % |
| pathfinder | R200 | pcdep (collector-only) | 285,296,850 | 963,372 | 3,980,124 | 0 | 254,720,000 | 25,633,354 | 0 | 0 | 98.27 % |
| pathfinder | R20 | pcdep (collector-only) | 3,163,914 | 93,180 | 379,404 | 0 | 2,432,000 | 259,330 | 0 | 0 | 85.06 % |
| stencil1d | L10 | pcdep (collector-only) | 859,832,310 | 94,371,830 | 681,574,400 | 0 | 41,943,040 | 41,943,040 | 0 | 0 | 9.76 % |
| stencil1d | L20 | pcdep (collector-only) | 1,719,664,620 | 188,743,660 | 1,363,148,800 | 0 | 83,886,080 | 83,886,080 | 0 | 0 | 9.76 % |
