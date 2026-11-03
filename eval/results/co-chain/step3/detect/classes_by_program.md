| suite | class | pairs | programs |
|---|---|---|---|
| P4 | edge/chain cross-thread, judged not reported | 1 | 1 |
| P4 | edge/chain only thread-local | 4 | 4 |
| P4 | only via a non-read hop (intervening write/atomic) | 8 | 4 |
| P5 | edge/chain cross-thread, judged not reported | 1 | 1 |
| P5 | only via a non-read hop (intervening write/atomic) | 1 | 1 |
| P6 | edge/chain cross-thread, judged not reported | 1 | 1 |
| P6 | edge/chain only thread-local | 19 | 3 |
| P6 | only via a non-read hop (intervening write/atomic) | 52 | 2 |
| P9 | edge/chain only thread-local | 4 | 1 |
| PI | edge/chain only thread-local | 35 | 23 |
| PI | not reachable: dropped-word deficit at a or c | 74 | 34 |
| PI | not reachable: no gap evidence | 18 | 9 |
| PI | only via a non-read hop (intervening write/atomic) | 3558 | 303 |
| PI | pcs not both recorded | 227 | 15 |

- all suites: edge/chain cross-thread, judged not reported: 3 pairs in 3 programs
- all suites: edge/chain only thread-local: 62 pairs in 31 programs
- all suites: not reachable: dropped-word deficit at a or c: 74 pairs in 34 programs
- all suites: not reachable: no gap evidence: 18 pairs in 9 programs
- all suites: only via a non-read hop (intervening write/atomic): 3619 pairs in 310 programs
- all suites: pcs not both recorded: 227 pairs in 15 programs

Dispositions of the 'judged not reported' pairs: {'judged ORDERED(,edge)': 1, 'skipped rmw_pair_morally_strong': 1, 'judged RACE(,edge)': 1}

not reachable: dropped-word deficit at a or c: PI-conditional_edge_neighbors_boundsBug-DAG_100n_100e, PI-conditional_edge_neighbors_boundsBug_atomicBug_break-DAG_100n_100e, PI-conditional_edge_neighbors_boundsBug_break-DAG_100n_100e, PI-conditional_edge_neighbors_boundsBug_break-counterDAG_5n_5e, PI-conditional_edge_neighbors_boundsBug_cond-DAG_100n_100e, PI-conditional_edge_neighbors_boundsBug_cond-DAG_200n_400e, PI-conditional_edge_neighbors_boundsBug_cond-power_law_200n_1000e, PI-conditional_edge_neighbors_boundsBug_cond_atomicBug-DAG_100n_100e, PI-conditional_edge_neighbors_boundsBug_cond_guardBug-DAG_100n_100e, PI-conditional_edge_neighbors_boundsBug_cond_guardBug_atomicBug-DAG_10, PI-conditional_edge_neighbors_boundsBug_cond_guardBug_atomicBug-DAG_20, PI-conditional_edge_neighbors_boundsBug_guardBug-DAG_100n_100e

not reachable: no gap evidence: PI-conditional_edge_neighbors_persistent_reverse_cond_guardBug_atomicB, PI-conditional_edge_neighbors_reverse_guardBug_atomicBug-DAG_200n_400e, PI-populate_worklist_neighbors_atomicBug-DAG_100n_200e, PI-populate_worklist_neighbors_persistent_atomicBug-DAG_100n_200e, PI-populate_worklist_neighbors_persistent_atomicBug-DAG_200n_400e, PI-populate_worklist_neighbors_persistent_reverse_atomicBug-DAG_200n_4, PI-populate_worklist_neighbors_persistent_reverse_atomicBug-counterDAG, PI-populate_worklist_neighbors_persistent_reverse_atomicBug-power_law_, PI-populate_worklist_neighbors_warp_persistent_atomicBug-power_law_200
