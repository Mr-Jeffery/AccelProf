| program | pass | sizes | lane max/total | ratio (larger / smaller size) | flag (>10 % apart) | warp max/total | ratio |
|---|---|---|---|---|---|---|---|
| atomicCAS | pcdep (collector-only) | r100 -> r200 | 65.63 % -> 34.01 % | 0.5182 | YES | 65.63 % -> 34.01 % | 0.5182 |
| bfs | pcdep (collector-only) | 500K -> 1M | 6.49 % -> 6.55 % | 1.0094 | no | 6.91 % -> 7.18 % | 1.0401 |
| bfs | pcdep (scalar-clock) | 500K -> 1M | 6.49 % -> 6.51 % | 1.0026 | no | 7.03 % -> 7.27 % | 1.0341 |
| bfs | sync (scalar-clock) | 500K -> 1M | 8.08 % -> 8.16 % | 1.0108 | no | 7.03 % -> 7.27 % | 1.0341 |
| pathfinder | pcdep (collector-only) | R10 -> R20 | 6.96 % -> 6.93 % | 0.9949 | no | 6.85 % -> 6.82 % | 0.9957 |
| stencil1d | pcdep (collector-only) | L10 -> L20 | 7.46 % -> 7.38 % | 0.9892 | no | 7.43 % -> 7.36 % | 0.9902 |
