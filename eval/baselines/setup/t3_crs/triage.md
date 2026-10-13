# P9-crs-cuda triage (store /mnt/beegfs/fzheng4/cuvein_traces/full-2026-09-22)

## vector-clock: 50 kernel dumps, 155 deduped reports (harness dedup key: pc pair + space)

| dump | kernel | grid×block | MB | events | reports | tv_violation | barrier instances fired / released short / left open | threads never seen per block |
|---|---|---|---|---|---|---|---|---|
| kernel_0.json | gcrs_m_1_w_4 | [1024, 1, 1]×[128, 1, 1] | 47 | 45056 | 0 |  | 2048 / 0 {} / 0 | {'0': 1024} |
| kernel_1.json | gcrs_m_1_w_4 | [1024, 1, 1]×[128, 1, 1] | 89 | 86016 | 0 |  | 4096 / 0 {} / 0 | {'0': 1024} |
| kernel_2.json | gcrs_m_1_w_4 | [1024, 1, 1]×[128, 1, 1] | 130 | 126976 | 0 |  | 6144 / 0 {} / 0 | {'0': 1024} |
| kernel_3.json | gcrs_m_1_w_4 | [1024, 1, 1]×[128, 1, 1] | 172 | 167936 | 0 |  | 8192 / 0 {} / 0 | {'0': 1024} |
| kernel_4.json | gcrs_m_1_w_5 | [1093, 1, 1]×[128, 1, 1] | 135 | 62925 | 5 | TV-barrier-completion-order: block 66 warp 3 issues a post-b | 0 / 2098 {'75/128': 2, '125/128': 2096} / 0 | {'3': 1048, '53': 1} |
| kernel_5.json | gcrs_m_1_w_5 | [1093, 1, 1]×[128, 1, 1] | 333 | 121655 | 15 | TV-barrier-completion-order: block 76 warp 2 issues a post-b | 0 / 4196 {'75/128': 4, '125/128': 4192} / 0 | {'3': 1048, '53': 1} |
| kernel_6.json | gcrs_m_1_w_5 | [1093, 1, 1]×[128, 1, 1] | 531 | 180385 | 25 | TV-barrier-completion-order: block 76 warp 2 issues a post-b | 0 / 6294 {'75/128': 6, '125/128': 6288} / 0 | {'3': 1048, '53': 1} |
| kernel_7.json | gcrs_m_1_w_5 | [1093, 1, 1]×[128, 1, 1] | 521 | 239115 | 20 | TV-barrier-completion-order: block 76 warp 2 issues a post-b | 0 / 8392 {'75/128': 8, '125/128': 8384} / 0 | {'3': 1048, '53': 1} |
| kernel_8.json | gcrs_m_1_w_6 | [1093, 1, 1]×[128, 1, 1] | 162 | 70754 | 6 | TV-barrier-completion-order: block 42 warp 2 issues a post-b | 0 / 2082 {'36/128': 2, '126/128': 2080} / 0 | {'2': 1040, '92': 1} |
| kernel_9.json | gcrs_m_1_w_6 | [1093, 1, 1]×[128, 1, 1] | 404 | 137346 | 18 | TV-barrier-completion-order: block 58 warp 3 issues a post-b | 0 / 4164 {'36/128': 4, '126/128': 4160} / 0 | {'2': 1040, '92': 1} |
| kernel_10.json | gcrs_m_1_w_6 | [1093, 1, 1]×[128, 1, 1] | 648 | 203938 | 30 | TV-barrier-completion-order: block 84 warp 2 issues a post-b | 0 / 6246 {'36/128': 6, '126/128': 6240} / 0 | {'2': 1040, '92': 1} |
| kernel_11.json | gcrs_m_1_w_6 | [1093, 1, 1]×[128, 1, 1] | 629 | 270530 | 24 | TV-barrier-completion-order: block 24 warp 3 issues a post-b | 0 / 8328 {'36/128': 8, '126/128': 8320} / 0 | {'2': 1040, '92': 1} |
| kernel_12.json | gcrs_m_1_w_7 | [1171, 1, 1]×[128, 1, 1] | 188 | 79078 | 7 | TV-barrier-completion-order: block 84 warp 0 issues a post-b | 0 / 2082 {'42/128': 2, '126/128': 2080} / 0 | {'2': 1040, '86': 1} |
| kernel_13.json | gcrs_m_1_w_7 | [1171, 1, 1]×[128, 1, 1] | 369 | 153994 | 7 | TV-barrier-completion-order: block 84 warp 2 issues a post-b | 0 / 4164 {'42/128': 4, '126/128': 4160} / 0 | {'2': 1040, '86': 1} |
| kernel_14.json | gcrs_m_1_w_7 | [1171, 1, 1]×[128, 1, 1] | 448 | 228910 | 7 | TV-barrier-completion-order: block 94 warp 2 issues a post-b | 0 / 6246 {'42/128': 6, '126/128': 6240} / 0 | {'2': 1040, '86': 1} |
| kernel_15.json | gcrs_m_1_w_7 | [1171, 1, 1]×[128, 1, 1] | 527 | 303826 | 7 | TV-barrier-completion-order: block 84 warp 2 issues a post-b | 0 / 8328 {'42/128': 8, '126/128': 8320} / 0 | {'2': 1040, '86': 1} |
| kernel_16.json | gcrs_m_1_w_8 | [1025, 1, 1]×[128, 1, 1] | 78 | 69649 | 4 | TV-barrier-completion-order: block 1024 warp 0 issues a post | 2048 / 2 {'16/128': 2} / 0 | {'0': 1024, '112': 1} |
| kernel_17.json | gcrs_m_1_w_8 | [1025, 1, 1]×[128, 1, 1] | 150 | 135201 | 4 | TV-barrier-completion-order: block 1024 warp 0 issues a post | 4096 / 4 {'16/128': 4} / 0 | {'0': 1024, '112': 1} |
| kernel_18.json | gcrs_m_1_w_8 | [1025, 1, 1]×[128, 1, 1] | 223 | 200753 | 4 | TV-barrier-completion-order: block 1024 warp 0 issues a post | 6144 / 6 {'16/128': 6} / 0 | {'0': 1024, '112': 1} |
| kernel_19.json | gcrs_m_1_w_8 | [1025, 1, 1]×[128, 1, 1] | 295 | 266305 | 4 | TV-barrier-completion-order: block 1024 warp 0 issues a post | 8192 / 8 {'16/128': 8} / 0 | {'0': 1024, '112': 1} |
| kernel_20.json | gcrs_m_2_w_4 | [1025, 1, 1]×[128, 1, 1] | 94 | 90134 | 6 | TV-barrier-completion-order: block 1024 warp 0 issues a post | 4096 / 4 {'16/128': 4} / 0 | {'0': 1024, '112': 1} |
| kernel_21.json | gcrs_m_2_w_4 | [1025, 1, 1]×[128, 1, 1] | 136 | 131104 | 10 | TV-barrier-completion-order: block 1024 warp 0 issues a post | 6144 / 6 {'16/128': 6} / 0 | {'0': 1024, '112': 1} |
| kernel_22.json | gcrs_m_2_w_4 | [1025, 1, 1]×[128, 1, 1] | 178 | 172074 | 8 | TV-barrier-completion-order: block 1024 warp 0 issues a post | 8192 / 8 {'16/128': 8} / 0 | {'0': 1024, '112': 1} |
| kernel_23.json | gcrs_m_2_w_5 | [1093, 1, 1]×[128, 1, 1] | 268 | 125850 | 5 | TV-barrier-completion-order: block 33 warp 2 issues a post-b | 0 / 4196 {'90/128': 4, '125/128': 4192} / 0 | {'3': 1048, '38': 1} |
| kernel_24.json | gcrs_m_2_w_5 | [1093, 1, 1]×[128, 1, 1] | 327 | 184580 | 5 | TV-barrier-completion-order: block 93 warp 1 issues a post-b | 0 / 6294 {'90/128': 6, '125/128': 6288} / 0 | {'3': 1048, '38': 1} |
| kernel_25.json | gcrs_m_2_w_5 | [1093, 1, 1]×[128, 1, 1] | 387 | 243310 | 5 | TV-barrier-completion-order: block 84 warp 0 issues a post-b | 0 / 8392 {'90/128': 8, '125/128': 8384} / 0 | {'3': 1048, '38': 1} |
| kernel_26.json | gcrs_m_2_w_6 | [1093, 1, 1]×[128, 1, 1] | 322 | 141508 | 6 | TV-barrier-completion-order: block 76 warp 3 issues a post-b | 0 / 4164 {'54/128': 4, '126/128': 4160} / 0 | {'2': 1040, '74': 1} |
| kernel_27.json | gcrs_m_2_w_6 | [1093, 1, 1]×[128, 1, 1] | 391 | 208100 | 6 | TV-barrier-completion-order: block 84 warp 3 issues a post-b | 0 / 6246 {'54/128': 6, '126/128': 6240} / 0 | {'2': 1040, '74': 1} |
| kernel_28.json | gcrs_m_2_w_6 | [1093, 1, 1]×[128, 1, 1] | 460 | 274692 | 6 | TV-barrier-completion-order: block 58 warp 0 issues a post-b | 0 / 8328 {'54/128': 8, '126/128': 8320} / 0 | {'2': 1040, '74': 1} |
| kernel_29.json | gcrs_m_2_w_7 | [1171, 1, 1]×[128, 1, 1] | 377 | 158156 | 7 | TV-barrier-completion-order: block 15 warp 0 issues a post-b | 0 / 4164 {'56/128': 4, '126/128': 4160} / 0 | {'2': 1040, '72': 1} |
| kernel_30.json | gcrs_m_2_w_7 | [1171, 1, 1]×[128, 1, 1] | 456 | 233072 | 7 | TV-barrier-completion-order: block 15 warp 3 issues a post-b | 0 / 6246 {'56/128': 6, '126/128': 6240} / 0 | {'2': 1040, '72': 1} |
| kernel_31.json | gcrs_m_2_w_7 | [1171, 1, 1]×[128, 1, 1] | 535 | 307988 | 7 | TV-barrier-completion-order: block 15 warp 0 issues a post-b | 0 / 8328 {'56/128': 8, '126/128': 8320} / 0 | {'2': 1040, '72': 1} |
| kernel_32.json | gcrs_m_2_w_8 | [1025, 1, 1]×[128, 1, 1] | 156 | 139298 | 4 | TV-barrier-completion-order: block 1024 warp 0 issues a post | 4096 / 4 {'24/128': 4} / 0 | {'0': 1024, '104': 1} |
| kernel_33.json | gcrs_m_2_w_8 | [1025, 1, 1]×[128, 1, 1] | 228 | 204850 | 4 | TV-barrier-completion-order: block 1024 warp 0 issues a post | 6144 / 6 {'24/128': 6} / 0 | {'0': 1024, '104': 1} |
| kernel_34.json | gcrs_m_2_w_8 | [1025, 1, 1]×[128, 1, 1] | 301 | 270402 | 4 | TV-barrier-completion-order: block 1024 warp 0 issues a post | 8192 / 8 {'24/128': 8} / 0 | {'0': 1024, '104': 1} |
| kernel_35.json | gcrs_m_3_w_4 | [1025, 1, 1]×[128, 1, 1] | 142 | 135201 | 2 | TV-barrier-completion-order: block 1024 warp 0 issues a post | 6144 / 6 {'24/128': 6} / 0 | {'0': 1024, '104': 1} |
| kernel_36.json | gcrs_m_3_w_4 | [1025, 1, 1]×[128, 1, 1] | 183 | 176171 | 2 | TV-barrier-completion-order: block 1024 warp 0 issues a post | 8192 / 8 {'24/128': 8} / 0 | {'0': 1024, '104': 1} |
| kernel_37.json | gcrs_m_3_w_5 | [1093, 1, 1]×[128, 1, 1] | 334 | 188820 | 5 | TV-barrier-completion-order: block 66 warp 2 issues a post-b | 0 / 6294 {'100/128': 6, '125/128': 6288} / 0 | {'3': 1048, '28': 1} |
| kernel_38.json | gcrs_m_3_w_5 | [1093, 1, 1]×[128, 1, 1] | 393 | 247564 | 5 | TV-barrier-completion-order: block 34 warp 1 issues a post-b | 0 / 8392 {'100/128': 8, '125/128': 8384} / 0 | {'3': 1048, '28': 1} |
| kernel_39.json | gcrs_m_3_w_6 | [1093, 1, 1]×[128, 1, 1] | 397 | 212262 | 6 | TV-barrier-completion-order: block 66 warp 3 issues a post-b | 0 / 6246 {'60/128': 6, '126/128': 6240} / 0 | {'2': 1040, '68': 1} |
| kernel_40.json | gcrs_m_3_w_6 | [1093, 1, 1]×[128, 1, 1] | 467 | 278854 | 6 | TV-barrier-completion-order: block 15 warp 1 issues a post-b | 0 / 8328 {'60/128': 8, '126/128': 8320} / 0 | {'2': 1040, '68': 1} |
| kernel_41.json | gcrs_m_3_w_7 | [1171, 1, 1]×[128, 1, 1] | 461 | 237234 | 7 | TV-barrier-completion-order: block 76 warp 1 issues a post-b | 0 / 6246 {'63/128': 6, '126/128': 6240} / 0 | {'2': 1040, '65': 1} |
| kernel_42.json | gcrs_m_3_w_7 | [1171, 1, 1]×[128, 1, 1] | 540 | 312150 | 7 | TV-barrier-completion-order: block 42 warp 1 issues a post-b | 0 / 8328 {'63/128': 8, '126/128': 8320} / 0 | {'2': 1040, '65': 1} |
| kernel_43.json | gcrs_m_3_w_8 | [1025, 1, 1]×[128, 1, 1] | 234 | 208947 | 4 | TV-barrier-completion-order: block 1024 warp 0 issues a post | 6144 / 6 {'32/128': 6} / 0 | {'0': 1024, '96': 1} |
| kernel_44.json | gcrs_m_3_w_8 | [1025, 1, 1]×[128, 1, 1] | 306 | 274499 | 4 | TV-barrier-completion-order: block 1024 warp 0 issues a post | 8192 / 8 {'32/128': 8} / 0 | {'0': 1024, '96': 1} |
| kernel_45.json | gcrs_m_4_w_4 | [1025, 1, 1]×[128, 1, 1] | 189 | 180268 | 2 | TV-barrier-completion-order: block 1024 warp 0 issues a post | 8192 / 8 {'32/128': 8} / 0 | {'0': 1024, '96': 1} |
| kernel_46.json | gcrs_m_4_w_5 | [1093, 1, 1]×[128, 1, 1] | 399 | 251760 | 5 | TV-barrier-completion-order: block 66 warp 2 issues a post-b | 0 / 8392 {'105/128': 8, '125/128': 8384} / 0 | {'3': 1048, '23': 1} |
| kernel_47.json | gcrs_m_4_w_6 | [1093, 1, 1]×[128, 1, 1] | 472 | 283084 | 6 | TV-barrier-completion-order: block 84 warp 0 issues a post-b | 0 / 8328 {'66/128': 8, '126/128': 8320} / 0 | {'2': 1040, '62': 1} |
| kernel_48.json | gcrs_m_4_w_7 | [1171, 1, 1]×[128, 1, 1] | 546 | 316388 | 7 | TV-barrier-completion-order: block 66 warp 0 issues a post-b | 0 / 8328 {'70/128': 8, '126/128': 8320} / 0 | {'2': 1040, '58': 1} |
| kernel_49.json | gcrs_m_4_w_8 | [1025, 1, 1]×[128, 1, 1] | 312 | 278664 | 4 | TV-barrier-completion-order: block 1024 warp 0 issues a post | 8192 / 8 {'40/128': 8} / 0 | {'0': 1024, '88': 1} |

| kernel | anc pc (line) | cur pc (line) | space | type | dist | strength | hb_class | event_cand | chain | engine records (relation) |
|---|---|---|---|---|---|---|---|---|---|---|
| gcrs_m_1_w_5 | 0x970 (kernels.cu:88) | 0xa10 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'block': 8388, 'warp': 96472} |
| gcrs_m_1_w_5 | 0x970 (kernels.cu:88) | 0xa40 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 99616, 'block': 5244} |
| gcrs_m_1_w_5 | 0x970 (kernels.cu:88) | 0xa60 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x970 (kernels.cu:88) | 0xa70 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x970 (kernels.cu:88) | 0xa80 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 97518, 'block': 7342} |
| gcrs_m_1_w_5 | 0x3a0 (kernels.cu:88) | 0x3c0 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'block': 8388, 'warp': 96472} |
| gcrs_m_1_w_5 | 0x3a0 (kernels.cu:88) | 0x3d0 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 99616, 'block': 5244} |
| gcrs_m_1_w_5 | 0x3a0 (kernels.cu:88) | 0x3f0 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x3a0 (kernels.cu:88) | 0x410 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x3a0 (kernels.cu:88) | 0x4c0 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 97518, 'block': 7342} |
| gcrs_m_1_w_5 | 0x3c0 (kernels.cu:95) | 0x500 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 96472, 'block': 8388} |
| gcrs_m_1_w_5 | 0x3d0 (kernels.cu:95) | 0x500 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 99616, 'block': 5244} |
| gcrs_m_1_w_5 | 0x3f0 (kernels.cu:95) | 0x500 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x410 (kernels.cu:95) | 0x500 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x4c0 (kernels.cu:95) | 0x500 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 97518, 'block': 7342} |
| gcrs_m_1_w_5 | 0x500 (kernels.cu:88) | 0x570 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'block': 8388, 'warp': 96472} |
| gcrs_m_1_w_5 | 0x500 (kernels.cu:88) | 0x580 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'block': 5244, 'warp': 99616} |
| gcrs_m_1_w_5 | 0x500 (kernels.cu:88) | 0x5a0 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x500 (kernels.cu:88) | 0x640 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x500 (kernels.cu:88) | 0x690 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 97518, 'block': 7342} |
| gcrs_m_1_w_5 | 0x3a0 (kernels.cu:88) | 0x3c0 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'block': 8388, 'warp': 96472} |
| gcrs_m_1_w_5 | 0x3a0 (kernels.cu:88) | 0x3d0 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'block': 5244, 'warp': 99616} |
| gcrs_m_1_w_5 | 0x3a0 (kernels.cu:88) | 0x3f0 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x3a0 (kernels.cu:88) | 0x410 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x3a0 (kernels.cu:88) | 0x4c0 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 97518, 'block': 7342} |
| gcrs_m_1_w_5 | 0x3c0 (kernels.cu:95) | 0x500 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 96472, 'block': 8388} |
| gcrs_m_1_w_5 | 0x3d0 (kernels.cu:95) | 0x500 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 99616, 'block': 5244} |
| gcrs_m_1_w_5 | 0x3f0 (kernels.cu:95) | 0x500 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x410 (kernels.cu:95) | 0x500 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x4c0 (kernels.cu:95) | 0x500 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 97518, 'block': 7342} |
| gcrs_m_1_w_5 | 0x500 (kernels.cu:88) | 0x570 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'block': 8388, 'warp': 96472} |
| gcrs_m_1_w_5 | 0x500 (kernels.cu:88) | 0x580 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'block': 5244, 'warp': 99616} |
| gcrs_m_1_w_5 | 0x500 (kernels.cu:88) | 0x5a0 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x500 (kernels.cu:88) | 0x640 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x500 (kernels.cu:88) | 0x690 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 97518, 'block': 7342} |
| gcrs_m_1_w_5 | 0x570 (kernels.cu:95) | 0x970 (kernels.cu:88) | shared | WAR | block | none | structural | False |  | 104860 {'warp': 96472, 'block': 8388} |
| gcrs_m_1_w_5 | 0x580 (kernels.cu:95) | 0x970 (kernels.cu:88) | shared | WAR | block | none | structural | False |  | 104860 {'warp': 99616, 'block': 5244} |
| gcrs_m_1_w_5 | 0x5a0 (kernels.cu:95) | 0x970 (kernels.cu:88) | shared | WAR | block | none | structural | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x640 (kernels.cu:95) | 0x970 (kernels.cu:88) | shared | WAR | block | none | structural | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x690 (kernels.cu:95) | 0x970 (kernels.cu:88) | shared | WAR | block | none | structural | False |  | 104860 {'warp': 97518, 'block': 7342} |
| gcrs_m_1_w_5 | 0x970 (kernels.cu:88) | 0xa10 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 96472, 'block': 8388} |
| gcrs_m_1_w_5 | 0x970 (kernels.cu:88) | 0xa40 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'block': 5244, 'warp': 99616} |
| gcrs_m_1_w_5 | 0x970 (kernels.cu:88) | 0xa60 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x970 (kernels.cu:88) | 0xa70 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x970 (kernels.cu:88) | 0xa80 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 97518, 'block': 7342} |
| gcrs_m_1_w_5 | 0x570 (kernels.cu:95) | 0x3a0 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 96472, 'block': 8388} |
| gcrs_m_1_w_5 | 0x580 (kernels.cu:95) | 0x3a0 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 99616, 'block': 5244} |
| gcrs_m_1_w_5 | 0x5a0 (kernels.cu:95) | 0x3a0 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x640 (kernels.cu:95) | 0x3a0 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x690 (kernels.cu:95) | 0x3a0 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'block': 7342, 'warp': 97518} |
| gcrs_m_1_w_5 | 0x3a0 (kernels.cu:88) | 0x3c0 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'block': 8388, 'warp': 96472} |
| gcrs_m_1_w_5 | 0x3a0 (kernels.cu:88) | 0x3d0 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'block': 5244, 'warp': 99616} |
| gcrs_m_1_w_5 | 0x3a0 (kernels.cu:88) | 0x3f0 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'block': 4195, 'warp': 100665} |
| gcrs_m_1_w_5 | 0x3a0 (kernels.cu:88) | 0x410 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x3a0 (kernels.cu:88) | 0x4c0 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 97518, 'block': 7342} |
| gcrs_m_1_w_5 | 0x3c0 (kernels.cu:95) | 0x500 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 96472, 'block': 8388} |
| gcrs_m_1_w_5 | 0x3d0 (kernels.cu:95) | 0x500 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 99616, 'block': 5244} |
| gcrs_m_1_w_5 | 0x3f0 (kernels.cu:95) | 0x500 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x410 (kernels.cu:95) | 0x500 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x4c0 (kernels.cu:95) | 0x500 (kernels.cu:88) | shared | WAR | block | block | model_bug | False |  | 104860 {'warp': 97518, 'block': 7342} |
| gcrs_m_1_w_5 | 0x500 (kernels.cu:88) | 0x570 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 96472, 'block': 8388} |
| gcrs_m_1_w_5 | 0x500 (kernels.cu:88) | 0x580 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 99616, 'block': 5244} |
| gcrs_m_1_w_5 | 0x500 (kernels.cu:88) | 0x5a0 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x500 (kernels.cu:88) | 0x640 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 100665, 'block': 4195} |
| gcrs_m_1_w_5 | 0x500 (kernels.cu:88) | 0x690 (kernels.cu:95) | shared | RAW | block | block | model_bug | False |  | 104860 {'warp': 97518, 'block': 7342} |
| gcrs_m_1_w_6 | 0xaa0 (kernels.cu:140) | 0xb40 (kernels.cu:147) | shared | RAW | block | block | model_bug | False |  | 109230 {'block': 6244, 'warp': 102986} |
| gcrs_m_1_w_6 | 0xaa0 (kernels.cu:140) | 0xb70 (kernels.cu:147) | shared | RAW | block | block | model_bug | False |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0xaa0 (kernels.cu:140) | 0xba0 (kernels.cu:147) | shared | RAW | block | block | model_bug | False |  | 109230 {'block': 4162, 'warp': 105068} |
| gcrs_m_1_w_6 | 0xaa0 (kernels.cu:140) | 0xbc0 (kernels.cu:147) | shared | RAW | block | block | model_bug | False |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0xaa0 (kernels.cu:140) | 0xbd0 (kernels.cu:147) | shared | RAW | block | block | model_bug | False |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0xaa0 (kernels.cu:140) | 0xbe0 (kernels.cu:147) | shared | RAW | block | block | model_bug | False |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x3d0 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x3f0 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x420 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x480 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x500 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x540 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x3d0 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x3f0 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x420 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x480 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x500 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x540 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x620 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x630 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x660 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x680 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x730 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x790 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x3d0 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'block': 6244, 'warp': 102986} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x3f0 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x420 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x480 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x500 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x540 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x3d0 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x3f0 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x420 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x480 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x500 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x540 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x620 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x630 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x660 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x680 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'block': 4162, 'warp': 105068} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x730 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x790 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x620 (kernels.cu:147) | 0xaa0 (kernels.cu:140) | shared | WAR | block | none | structural | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x630 (kernels.cu:147) | 0xaa0 (kernels.cu:140) | shared | WAR | block | none | structural | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x660 (kernels.cu:147) | 0xaa0 (kernels.cu:140) | shared | WAR | block | none | structural | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x680 (kernels.cu:147) | 0xaa0 (kernels.cu:140) | shared | WAR | block | none | structural | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x730 (kernels.cu:147) | 0xaa0 (kernels.cu:140) | shared | WAR | block | none | structural | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x790 (kernels.cu:147) | 0xaa0 (kernels.cu:140) | shared | WAR | block | none | structural | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0xaa0 (kernels.cu:140) | 0xb40 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0xaa0 (kernels.cu:140) | 0xb70 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'block': 6244, 'warp': 102986} |
| gcrs_m_1_w_6 | 0xaa0 (kernels.cu:140) | 0xba0 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'block': 4162, 'warp': 105068} |
| gcrs_m_1_w_6 | 0xaa0 (kernels.cu:140) | 0xbc0 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0xaa0 (kernels.cu:140) | 0xbd0 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0xaa0 (kernels.cu:140) | 0xbe0 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x3d0 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x3f0 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x420 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x480 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x500 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x3b0 (kernels.cu:140) | 0x540 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x620 (kernels.cu:147) | 0x3b0 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x630 (kernels.cu:147) | 0x3b0 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x660 (kernels.cu:147) | 0x3b0 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x680 (kernels.cu:147) | 0x3b0 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x730 (kernels.cu:147) | 0x3b0 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x790 (kernels.cu:147) | 0x3b0 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x3d0 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x3f0 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x420 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x480 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x500 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x540 (kernels.cu:147) | 0x590 (kernels.cu:140) | shared | WAR | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x620 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x630 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102986, 'block': 6244} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x660 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x680 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 105068, 'block': 4162} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x730 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_6 | 0x590 (kernels.cu:140) | 0x790 (kernels.cu:147) | shared | RAW | block | block | model_bug | True |  | 109230 {'warp': 102988, 'block': 6242} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x370 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 112356 {'warp': 100913, 'block': 11443} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x380 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 112356 {'warp': 106113, 'block': 6243} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x390 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 112356 {'warp': 106113, 'block': 6243} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x3a0 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 112356 {'warp': 106113, 'block': 6243} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x3b0 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 112356 {'warp': 105072, 'block': 7284} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x3c0 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 112356 {'warp': 101952, 'block': 10404} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x460 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 112356 {'warp': 101952, 'block': 10404} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x370 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'block': 22886, 'warp': 201826} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x380 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'block': 12486, 'warp': 212226} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x390 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'warp': 212226, 'block': 12486} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x3a0 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'warp': 212226, 'block': 12486} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x3b0 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'warp': 210144, 'block': 14568} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x3c0 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'warp': 203904, 'block': 20808} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x460 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'warp': 203904, 'block': 20808} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x370 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'block': 22886, 'warp': 201826} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x380 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'warp': 212226, 'block': 12486} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x390 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'warp': 212226, 'block': 12486} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x3a0 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'block': 12486, 'warp': 212226} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x3b0 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'warp': 210144, 'block': 14568} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x3c0 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'warp': 203904, 'block': 20808} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x460 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'warp': 203904, 'block': 20808} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x370 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'block': 22886, 'warp': 201826} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x380 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'block': 12486, 'warp': 212226} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x390 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'block': 12486, 'warp': 212226} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x3a0 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'block': 12486, 'warp': 212226} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x3b0 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'block': 14568, 'warp': 210144} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x3c0 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'warp': 203904, 'block': 20808} |
| gcrs_m_1_w_7 | 0x2f0 (kernels.cu:192) | 0x460 (kernels.cu:199) | shared | RAW | block | block | model_bug | True |  | 224712 {'warp': 203904, 'block': 20808} |
| gcrs_m_1_w_8 | 0x270 (kernels.cu:244) | 0x320 (kernels.cu:251) | shared | RAW | warp | block | model_bug | True |  | 14 {'warp': 14} |
| gcrs_m_1_w_8 | 0x270 (kernels.cu:244) | 0x350 (kernels.cu:251) | shared | RAW | warp | block | model_bug | True |  | 14 {'warp': 14} |
| gcrs_m_1_w_8 | 0x270 (kernels.cu:244) | 0x380 (kernels.cu:251) | shared | RAW | warp | block | model_bug | True |  | 14 {'warp': 14} |
| gcrs_m_1_w_8 | 0x270 (kernels.cu:244) | 0x470 (kernels.cu:251) | shared | RAW | warp | block | model_bug | True |  | 14 {'warp': 14} |
| gcrs_m_1_w_8 | 0x270 (kernels.cu:244) | 0x320 (kernels.cu:251) | shared | RAW | warp | block | model_bug | True |  | 28 {'warp': 28} |
| gcrs_m_1_w_8 | 0x270 (kernels.cu:244) | 0x350 (kernels.cu:251) | shared | RAW | warp | block | model_bug | True |  | 28 {'warp': 28} |
| gcrs_m_1_w_8 | 0x270 (kernels.cu:244) | 0x380 (kernels.cu:251) | shared | RAW | warp | block | model_bug | True |  | 28 {'warp': 28} |
| gcrs_m_1_w_8 | 0x270 (kernels.cu:244) | 0x470 (kernels.cu:251) | shared | RAW | warp | block | model_bug | True |  | 28 {'warp': 28} |
| gcrs_m_1_w_8 | 0x270 (kernels.cu:244) | 0x320 (kernels.cu:251) | shared | RAW | warp | block | model_bug | True |  | 28 {'warp': 28} |
| gcrs_m_1_w_8 | 0x270 (kernels.cu:244) | 0x350 (kernels.cu:251) | shared | RAW | warp | block | model_bug | True |  | 28 {'warp': 28} |
| gcrs_m_1_w_8 | 0x270 (kernels.cu:244) | 0x380 (kernels.cu:251) | shared | RAW | warp | block | model_bug | True |  | 28 {'warp': 28} |
| gcrs_m_1_w_8 | 0x270 (kernels.cu:244) | 0x470 (kernels.cu:251) | shared | RAW | warp | block | model_bug | True |  | 28 {'warp': 28} |
| gcrs_m_1_w_8 | 0x270 (kernels.cu:244) | 0x320 (kernels.cu:251) | shared | RAW | warp | block | model_bug | True |  | 28 {'warp': 28} |
| gcrs_m_1_w_8 | 0x270 (kernels.cu:244) | 0x350 (kernels.cu:251) | shared | RAW | warp | block | model_bug | True |  | 28 {'warp': 28} |
| gcrs_m_1_w_8 | 0x270 (kernels.cu:244) | 0x380 (kernels.cu:251) | shared | RAW | warp | block | model_bug | True |  | 28 {'warp': 28} |
| gcrs_m_1_w_8 | 0x270 (kernels.cu:244) | 0x470 (kernels.cu:251) | shared | RAW | warp | block | model_bug | True |  | 28 {'warp': 28} |
| gcrs_m_2_w_4 | 0x350 (kernels.cu:299) | 0x370 (kernels.cu:306) | shared | RAW | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x350 (kernels.cu:299) | 0x4f0 (kernels.cu:306) | shared | RAW | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x370 (kernels.cu:306) | 0x550 (kernels.cu:299) | shared | WAR | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x4f0 (kernels.cu:306) | 0x550 (kernels.cu:299) | shared | WAR | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x550 (kernels.cu:299) | 0x610 (kernels.cu:306) | shared | RAW | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x550 (kernels.cu:299) | 0x740 (kernels.cu:306) | shared | RAW | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x350 (kernels.cu:299) | 0x370 (kernels.cu:306) | shared | RAW | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x350 (kernels.cu:299) | 0x4f0 (kernels.cu:306) | shared | RAW | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x370 (kernels.cu:306) | 0x550 (kernels.cu:299) | shared | WAR | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x4f0 (kernels.cu:306) | 0x550 (kernels.cu:299) | shared | WAR | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x550 (kernels.cu:299) | 0x610 (kernels.cu:306) | shared | RAW | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x550 (kernels.cu:299) | 0x740 (kernels.cu:306) | shared | RAW | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x610 (kernels.cu:306) | 0xb50 (kernels.cu:299) | shared | WAR | warp | none | structural | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x740 (kernels.cu:306) | 0xb50 (kernels.cu:299) | shared | WAR | warp | none | structural | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0xb50 (kernels.cu:299) | 0xc10 (kernels.cu:306) | shared | RAW | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0xb50 (kernels.cu:299) | 0xc30 (kernels.cu:306) | shared | RAW | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x350 (kernels.cu:299) | 0x370 (kernels.cu:306) | shared | RAW | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x350 (kernels.cu:299) | 0x4f0 (kernels.cu:306) | shared | RAW | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x610 (kernels.cu:306) | 0x350 (kernels.cu:299) | shared | WAR | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x740 (kernels.cu:306) | 0x350 (kernels.cu:299) | shared | WAR | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x370 (kernels.cu:306) | 0x550 (kernels.cu:299) | shared | WAR | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x4f0 (kernels.cu:306) | 0x550 (kernels.cu:299) | shared | WAR | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x550 (kernels.cu:299) | 0x610 (kernels.cu:306) | shared | RAW | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_4 | 0x550 (kernels.cu:299) | 0x740 (kernels.cu:306) | shared | RAW | warp | block | model_bug | True |  | 12 {'warp': 12} |
| gcrs_m_2_w_5 | 0x2e0 (kernels.cu:357) | 0x3a0 (kernels.cu:364) | shared | RAW | block | block | model_bug | True |  | 209744 {'block': 16776, 'warp': 192968} |
| gcrs_m_2_w_5 | 0x2e0 (kernels.cu:357) | 0x3c0 (kernels.cu:364) | shared | RAW | block | block | model_bug | True |  | 209744 {'warp': 199256, 'block': 10488} |
| gcrs_m_2_w_5 | 0x2e0 (kernels.cu:357) | 0x3e0 (kernels.cu:364) | shared | RAW | block | block | model_bug | True |  | 209744 {'warp': 201354, 'block': 8390} |
| gcrs_m_2_w_5 | 0x2e0 (kernels.cu:357) | 0x3f0 (kernels.cu:364) | shared | RAW | block | block | model_bug | True |  | 209744 {'warp': 201354, 'block': 8390} |
| gcrs_m_2_w_5 | 0x2e0 (kernels.cu:357) | 0x480 (kernels.cu:364) | shared | RAW | block | block | model_bug | True |  | 209744 {'warp': 195060, 'block': 14684} |
| gcrs_m_2_w_5 | 0x2e0 (kernels.cu:357) | 0x3a0 (kernels.cu:364) | shared | RAW | block | block | model_bug | True |  | 209744 {'block': 16776, 'warp': 192968} |
| gcrs_m_2_w_5 | 0x2e0 (kernels.cu:357) | 0x3c0 (kernels.cu:364) | shared | RAW | block | block | model_bug | True |  | 209744 {'warp': 199256, 'block': 10488} |
| gcrs_m_2_w_5 | 0x2e0 (kernels.cu:357) | 0x3e0 (kernels.cu:364) | shared | RAW | block | block | model_bug | True |  | 209744 {'warp': 201354, 'block': 8390} |
| gcrs_m_2_w_5 | 0x2e0 (kernels.cu:357) | 0x3f0 (kernels.cu:364) | shared | RAW | block | block | model_bug | True |  | 209744 {'block': 8390, 'warp': 201354} |
| gcrs_m_2_w_5 | 0x2e0 (kernels.cu:357) | 0x480 (kernels.cu:364) | shared | RAW | block | block | model_bug | True |  | 209744 {'warp': 195060, 'block': 14684} |
| gcrs_m_2_w_5 | 0x2e0 (kernels.cu:357) | 0x3a0 (kernels.cu:364) | shared | RAW | block | block | model_bug | True |  | 209744 {'warp': 192968, 'block': 16776} |
| gcrs_m_2_w_5 | 0x2e0 (kernels.cu:357) | 0x3c0 (kernels.cu:364) | shared | RAW | block | block | model_bug | True |  | 209744 {'warp': 199256, 'block': 10488} |
| gcrs_m_2_w_5 | 0x2e0 (kernels.cu:357) | 0x3e0 (kernels.cu:364) | shared | RAW | block | block | model_bug | True |  | 209744 {'warp': 201354, 'block': 8390} |
| gcrs_m_2_w_5 | 0x2e0 (kernels.cu:357) | 0x3f0 (kernels.cu:364) | shared | RAW | block | block | model_bug | True |  | 209744 {'warp': 201354, 'block': 8390} |
| gcrs_m_2_w_5 | 0x2e0 (kernels.cu:357) | 0x480 (kernels.cu:364) | shared | RAW | block | block | model_bug | True |  | 209744 {'warp': 195060, 'block': 14684} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x390 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'warp': 206002, 'block': 12488} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x3a0 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'block': 12488, 'warp': 206002} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x3b0 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'block': 8324, 'warp': 210166} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x3c0 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'warp': 210166, 'block': 8324} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x430 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'warp': 206006, 'block': 12484} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x540 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'warp': 206006, 'block': 12484} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x390 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'warp': 206002, 'block': 12488} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x3a0 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'block': 12488, 'warp': 206002} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x3b0 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'warp': 210166, 'block': 8324} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x3c0 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'warp': 210166, 'block': 8324} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x430 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'warp': 206006, 'block': 12484} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x540 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'warp': 206006, 'block': 12484} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x390 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'warp': 206002, 'block': 12488} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x3a0 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'warp': 206002, 'block': 12488} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x3b0 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'warp': 210166, 'block': 8324} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x3c0 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'warp': 210166, 'block': 8324} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x430 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'warp': 206006, 'block': 12484} |
| gcrs_m_2_w_6 | 0x2e0 (kernels.cu:415) | 0x540 (kernels.cu:422) | shared | RAW | block | block | model_bug | True |  | 218490 {'warp': 206006, 'block': 12484} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x410 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'warp': 201850, 'block': 22886} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x420 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'block': 12486, 'warp': 212250} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x430 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'block': 12486, 'warp': 212250} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x520 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'block': 12486, 'warp': 212250} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x5c0 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'block': 14568, 'warp': 210168} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x630 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'warp': 203928, 'block': 20808} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x6d0 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'warp': 203928, 'block': 20808} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x410 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'block': 22886, 'warp': 201850} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x420 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'block': 12486, 'warp': 212250} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x430 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'block': 12486, 'warp': 212250} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x520 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'block': 12486, 'warp': 212250} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x5c0 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'warp': 210168, 'block': 14568} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x630 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'warp': 203928, 'block': 20808} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x6d0 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'warp': 203928, 'block': 20808} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x410 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'warp': 201850, 'block': 22886} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x420 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'warp': 212250, 'block': 12486} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x430 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'warp': 212250, 'block': 12486} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x520 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'warp': 212250, 'block': 12486} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x5c0 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'warp': 210168, 'block': 14568} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x630 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'warp': 203928, 'block': 20808} |
| gcrs_m_2_w_7 | 0x380 (kernels.cu:473) | 0x6d0 (kernels.cu:480) | shared | RAW | block | block | model_bug | True |  | 224736 {'warp': 203928, 'block': 20808} |
| gcrs_m_2_w_8 | 0x2d0 (kernels.cu:531) | 0x380 (kernels.cu:538) | shared | RAW | warp | block | model_bug | True |  | 42 {'warp': 42} |
| gcrs_m_2_w_8 | 0x2d0 (kernels.cu:531) | 0x3a0 (kernels.cu:538) | shared | RAW | warp | block | model_bug | True |  | 42 {'warp': 42} |
| gcrs_m_2_w_8 | 0x2d0 (kernels.cu:531) | 0x4e0 (kernels.cu:538) | shared | RAW | warp | block | model_bug | True |  | 42 {'warp': 42} |
| gcrs_m_2_w_8 | 0x2d0 (kernels.cu:531) | 0x5a0 (kernels.cu:538) | shared | RAW | warp | block | model_bug | True |  | 42 {'warp': 42} |
| gcrs_m_2_w_8 | 0x2d0 (kernels.cu:531) | 0x380 (kernels.cu:538) | shared | RAW | warp | block | model_bug | True |  | 42 {'warp': 42} |
| gcrs_m_2_w_8 | 0x2d0 (kernels.cu:531) | 0x3a0 (kernels.cu:538) | shared | RAW | warp | block | model_bug | True |  | 42 {'warp': 42} |
| gcrs_m_2_w_8 | 0x2d0 (kernels.cu:531) | 0x4e0 (kernels.cu:538) | shared | RAW | warp | block | model_bug | True |  | 42 {'warp': 42} |
| gcrs_m_2_w_8 | 0x2d0 (kernels.cu:531) | 0x5a0 (kernels.cu:538) | shared | RAW | warp | block | model_bug | True |  | 42 {'warp': 42} |
| gcrs_m_2_w_8 | 0x2d0 (kernels.cu:531) | 0x380 (kernels.cu:538) | shared | RAW | warp | block | model_bug | True |  | 42 {'warp': 42} |
| gcrs_m_2_w_8 | 0x2d0 (kernels.cu:531) | 0x3a0 (kernels.cu:538) | shared | RAW | warp | block | model_bug | True |  | 42 {'warp': 42} |
| gcrs_m_2_w_8 | 0x2d0 (kernels.cu:531) | 0x4e0 (kernels.cu:538) | shared | RAW | warp | block | model_bug | True |  | 42 {'warp': 42} |
| gcrs_m_2_w_8 | 0x2d0 (kernels.cu:531) | 0x5a0 (kernels.cu:538) | shared | RAW | warp | block | model_bug | True |  | 42 {'warp': 42} |
| gcrs_m_3_w_4 | 0x2c0 (kernels.cu:591) | 0x370 (kernels.cu:598) | shared | RAW | warp | block | model_bug | True |  | 36 {'warp': 36} |
| gcrs_m_3_w_4 | 0x2c0 (kernels.cu:591) | 0x3d0 (kernels.cu:598) | shared | RAW | warp | block | model_bug | True |  | 36 {'warp': 36} |
| gcrs_m_3_w_4 | 0x2c0 (kernels.cu:591) | 0x370 (kernels.cu:598) | shared | RAW | warp | block | model_bug | True |  | 36 {'warp': 36} |
| gcrs_m_3_w_4 | 0x2c0 (kernels.cu:591) | 0x3d0 (kernels.cu:598) | shared | RAW | warp | block | model_bug | True |  | 36 {'warp': 36} |
| gcrs_m_3_w_5 | 0x360 (kernels.cu:653) | 0x420 (kernels.cu:660) | shared | RAW | block | block | model_bug | True |  | 209760 {'block': 16784, 'warp': 192976} |
| gcrs_m_3_w_5 | 0x360 (kernels.cu:653) | 0x450 (kernels.cu:660) | shared | RAW | block | block | model_bug | True |  | 209760 {'warp': 199270, 'block': 10490} |
| gcrs_m_3_w_5 | 0x360 (kernels.cu:653) | 0x480 (kernels.cu:660) | shared | RAW | block | block | model_bug | True |  | 209760 {'block': 8392, 'warp': 201368} |
| gcrs_m_3_w_5 | 0x360 (kernels.cu:653) | 0x580 (kernels.cu:660) | shared | RAW | block | block | model_bug | True |  | 209760 {'block': 8392, 'warp': 201368} |
| gcrs_m_3_w_5 | 0x360 (kernels.cu:653) | 0x670 (kernels.cu:660) | shared | RAW | block | block | model_bug | True |  | 209760 {'warp': 195074, 'block': 14686} |
| gcrs_m_3_w_5 | 0x360 (kernels.cu:653) | 0x420 (kernels.cu:660) | shared | RAW | block | block | model_bug | True |  | 209760 {'block': 16784, 'warp': 192976} |
| gcrs_m_3_w_5 | 0x360 (kernels.cu:653) | 0x450 (kernels.cu:660) | shared | RAW | block | block | model_bug | True |  | 209760 {'block': 10490, 'warp': 199270} |
| gcrs_m_3_w_5 | 0x360 (kernels.cu:653) | 0x480 (kernels.cu:660) | shared | RAW | block | block | model_bug | True |  | 209760 {'warp': 201368, 'block': 8392} |
| gcrs_m_3_w_5 | 0x360 (kernels.cu:653) | 0x580 (kernels.cu:660) | shared | RAW | block | block | model_bug | True |  | 209760 {'warp': 201368, 'block': 8392} |
| gcrs_m_3_w_5 | 0x360 (kernels.cu:653) | 0x670 (kernels.cu:660) | shared | RAW | block | block | model_bug | True |  | 209760 {'warp': 195074, 'block': 14686} |
| gcrs_m_3_w_6 | 0x370 (kernels.cu:715) | 0x430 (kernels.cu:722) | shared | RAW | block | block | model_bug | True |  | 218500 {'warp': 206012, 'block': 12488} |
| gcrs_m_3_w_6 | 0x370 (kernels.cu:715) | 0x460 (kernels.cu:722) | shared | RAW | block | block | model_bug | True |  | 218500 {'warp': 206012, 'block': 12488} |
| gcrs_m_3_w_6 | 0x370 (kernels.cu:715) | 0x4f0 (kernels.cu:722) | shared | RAW | block | block | model_bug | True |  | 218500 {'warp': 210176, 'block': 8324} |
| gcrs_m_3_w_6 | 0x370 (kernels.cu:715) | 0x590 (kernels.cu:722) | shared | RAW | block | block | model_bug | True |  | 218500 {'warp': 210176, 'block': 8324} |
| gcrs_m_3_w_6 | 0x370 (kernels.cu:715) | 0x680 (kernels.cu:722) | shared | RAW | block | block | model_bug | True |  | 218500 {'warp': 206016, 'block': 12484} |
| gcrs_m_3_w_6 | 0x370 (kernels.cu:715) | 0x7b0 (kernels.cu:722) | shared | RAW | block | block | model_bug | True |  | 218500 {'warp': 206016, 'block': 12484} |
| gcrs_m_3_w_6 | 0x370 (kernels.cu:715) | 0x430 (kernels.cu:722) | shared | RAW | block | block | model_bug | True |  | 218500 {'block': 12488, 'warp': 206012} |
| gcrs_m_3_w_6 | 0x370 (kernels.cu:715) | 0x460 (kernels.cu:722) | shared | RAW | block | block | model_bug | True |  | 218500 {'block': 12488, 'warp': 206012} |
| gcrs_m_3_w_6 | 0x370 (kernels.cu:715) | 0x4f0 (kernels.cu:722) | shared | RAW | block | block | model_bug | True |  | 218500 {'warp': 210176, 'block': 8324} |
| gcrs_m_3_w_6 | 0x370 (kernels.cu:715) | 0x590 (kernels.cu:722) | shared | RAW | block | block | model_bug | True |  | 218500 {'warp': 210176, 'block': 8324} |
| gcrs_m_3_w_6 | 0x370 (kernels.cu:715) | 0x680 (kernels.cu:722) | shared | RAW | block | block | model_bug | True |  | 218500 {'warp': 206016, 'block': 12484} |
| gcrs_m_3_w_6 | 0x370 (kernels.cu:715) | 0x7b0 (kernels.cu:722) | shared | RAW | block | block | model_bug | True |  | 218500 {'warp': 206016, 'block': 12484} |
| gcrs_m_3_w_7 | 0x380 (kernels.cu:777) | 0x440 (kernels.cu:784) | shared | RAW | block | block | model_bug | True |  | 224748 {'block': 22886, 'warp': 201862} |
| gcrs_m_3_w_7 | 0x380 (kernels.cu:777) | 0x460 (kernels.cu:784) | shared | RAW | block | block | model_bug | True |  | 224748 {'warp': 212262, 'block': 12486} |
| gcrs_m_3_w_7 | 0x380 (kernels.cu:777) | 0x510 (kernels.cu:784) | shared | RAW | block | block | model_bug | True |  | 224748 {'block': 12486, 'warp': 212262} |
| gcrs_m_3_w_7 | 0x380 (kernels.cu:777) | 0x5f0 (kernels.cu:784) | shared | RAW | block | block | model_bug | True |  | 224748 {'warp': 212262, 'block': 12486} |
| gcrs_m_3_w_7 | 0x380 (kernels.cu:777) | 0x6e0 (kernels.cu:784) | shared | RAW | block | block | model_bug | True |  | 224748 {'block': 14568, 'warp': 210180} |
| gcrs_m_3_w_7 | 0x380 (kernels.cu:777) | 0x7e0 (kernels.cu:784) | shared | RAW | block | block | model_bug | True |  | 224748 {'warp': 203940, 'block': 20808} |
| gcrs_m_3_w_7 | 0x380 (kernels.cu:777) | 0x8e0 (kernels.cu:784) | shared | RAW | block | block | model_bug | True |  | 224748 {'warp': 203940, 'block': 20808} |
| gcrs_m_3_w_7 | 0x380 (kernels.cu:777) | 0x440 (kernels.cu:784) | shared | RAW | block | block | model_bug | True |  | 224748 {'block': 22886, 'warp': 201862} |
| gcrs_m_3_w_7 | 0x380 (kernels.cu:777) | 0x460 (kernels.cu:784) | shared | RAW | block | block | model_bug | True |  | 224748 {'block': 12486, 'warp': 212262} |
| gcrs_m_3_w_7 | 0x380 (kernels.cu:777) | 0x510 (kernels.cu:784) | shared | RAW | block | block | model_bug | True |  | 224748 {'block': 12486, 'warp': 212262} |
| gcrs_m_3_w_7 | 0x380 (kernels.cu:777) | 0x5f0 (kernels.cu:784) | shared | RAW | block | block | model_bug | True |  | 224748 {'block': 12486, 'warp': 212262} |
| gcrs_m_3_w_7 | 0x380 (kernels.cu:777) | 0x6e0 (kernels.cu:784) | shared | RAW | block | block | model_bug | True |  | 224748 {'warp': 210180, 'block': 14568} |
| gcrs_m_3_w_7 | 0x380 (kernels.cu:777) | 0x7e0 (kernels.cu:784) | shared | RAW | block | block | model_bug | True |  | 224748 {'warp': 203940, 'block': 20808} |
| gcrs_m_3_w_7 | 0x380 (kernels.cu:777) | 0x8e0 (kernels.cu:784) | shared | RAW | block | block | model_bug | True |  | 224748 {'warp': 203940, 'block': 20808} |
| gcrs_m_3_w_8 | 0x320 (kernels.cu:839) | 0x380 (kernels.cu:846) | shared | RAW | warp | block | model_bug | True |  | 56 {'warp': 56} |
| gcrs_m_3_w_8 | 0x320 (kernels.cu:839) | 0x4f0 (kernels.cu:846) | shared | RAW | warp | block | model_bug | True |  | 56 {'warp': 56} |
| gcrs_m_3_w_8 | 0x320 (kernels.cu:839) | 0x6f0 (kernels.cu:846) | shared | RAW | warp | block | model_bug | True |  | 56 {'warp': 56} |
| gcrs_m_3_w_8 | 0x320 (kernels.cu:839) | 0x8d0 (kernels.cu:846) | shared | RAW | warp | block | model_bug | True |  | 56 {'warp': 56} |
| gcrs_m_3_w_8 | 0x320 (kernels.cu:839) | 0x380 (kernels.cu:846) | shared | RAW | warp | block | model_bug | True |  | 56 {'warp': 56} |
| gcrs_m_3_w_8 | 0x320 (kernels.cu:839) | 0x4f0 (kernels.cu:846) | shared | RAW | warp | block | model_bug | True |  | 56 {'warp': 56} |
| gcrs_m_3_w_8 | 0x320 (kernels.cu:839) | 0x6f0 (kernels.cu:846) | shared | RAW | warp | block | model_bug | True |  | 56 {'warp': 56} |
| gcrs_m_3_w_8 | 0x320 (kernels.cu:839) | 0x8d0 (kernels.cu:846) | shared | RAW | warp | block | model_bug | True |  | 56 {'warp': 56} |
| gcrs_m_4_w_4 | 0x330 (kernels.cu:901) | 0x3b0 (kernels.cu:908) | shared | RAW | warp | block | model_bug | True |  | 48 {'warp': 48} |
| gcrs_m_4_w_4 | 0x330 (kernels.cu:901) | 0x5c0 (kernels.cu:908) | shared | RAW | warp | block | model_bug | True |  | 48 {'warp': 48} |
| gcrs_m_4_w_5 | 0x3a0 (kernels.cu:965) | 0x430 (kernels.cu:972) | shared | RAW | block | block | model_bug | True |  | 209768 {'block': 16784, 'warp': 192984} |
| gcrs_m_4_w_5 | 0x3a0 (kernels.cu:965) | 0x450 (kernels.cu:972) | shared | RAW | block | block | model_bug | True |  | 209768 {'block': 10490, 'warp': 199278} |
| gcrs_m_4_w_5 | 0x3a0 (kernels.cu:965) | 0x630 (kernels.cu:972) | shared | RAW | block | block | model_bug | True |  | 209768 {'warp': 201376, 'block': 8392} |
| gcrs_m_4_w_5 | 0x3a0 (kernels.cu:965) | 0x790 (kernels.cu:972) | shared | RAW | block | block | model_bug | True |  | 209768 {'warp': 201376, 'block': 8392} |
| gcrs_m_4_w_5 | 0x3a0 (kernels.cu:965) | 0x8d0 (kernels.cu:972) | shared | RAW | block | block | model_bug | True |  | 209768 {'warp': 195082, 'block': 14686} |
| gcrs_m_4_w_6 | 0x370 (kernels.cu:1029) | 0x410 (kernels.cu:1036) | shared | RAW | block | block | model_bug | True |  | 218510 {'warp': 206018, 'block': 12492} |
| gcrs_m_4_w_6 | 0x370 (kernels.cu:1029) | 0x420 (kernels.cu:1036) | shared | RAW | block | block | model_bug | True |  | 218510 {'warp': 206018, 'block': 12492} |
| gcrs_m_4_w_6 | 0x370 (kernels.cu:1029) | 0x640 (kernels.cu:1036) | shared | RAW | block | block | model_bug | True |  | 218510 {'warp': 210182, 'block': 8328} |
| gcrs_m_4_w_6 | 0x370 (kernels.cu:1029) | 0x790 (kernels.cu:1036) | shared | RAW | block | block | model_bug | True |  | 218510 {'warp': 210182, 'block': 8328} |
| gcrs_m_4_w_6 | 0x370 (kernels.cu:1029) | 0x930 (kernels.cu:1036) | shared | RAW | block | block | model_bug | True |  | 218510 {'warp': 206018, 'block': 12492} |
| gcrs_m_4_w_6 | 0x370 (kernels.cu:1029) | 0xa30 (kernels.cu:1036) | shared | RAW | block | block | model_bug | True |  | 218510 {'warp': 206018, 'block': 12492} |
| gcrs_m_4_w_7 | 0x3a0 (kernels.cu:1093) | 0x3d0 (kernels.cu:1100) | shared | RAW | block | block | model_bug | True |  | 224760 {'block': 22898, 'warp': 201862} |
| gcrs_m_4_w_7 | 0x3a0 (kernels.cu:1093) | 0x570 (kernels.cu:1100) | shared | RAW | block | block | model_bug | True |  | 224760 {'warp': 212272, 'block': 12488} |
| gcrs_m_4_w_7 | 0x3a0 (kernels.cu:1093) | 0x700 (kernels.cu:1100) | shared | RAW | block | block | model_bug | True |  | 224760 {'warp': 212272, 'block': 12488} |
| gcrs_m_4_w_7 | 0x3a0 (kernels.cu:1093) | 0x7f0 (kernels.cu:1100) | shared | RAW | block | block | model_bug | True |  | 224760 {'warp': 212272, 'block': 12488} |
| gcrs_m_4_w_7 | 0x3a0 (kernels.cu:1093) | 0x920 (kernels.cu:1100) | shared | RAW | block | block | model_bug | True |  | 224760 {'warp': 210190, 'block': 14570} |
| gcrs_m_4_w_7 | 0x3a0 (kernels.cu:1093) | 0xab0 (kernels.cu:1100) | shared | RAW | block | block | model_bug | True |  | 224760 {'warp': 203950, 'block': 20810} |
| gcrs_m_4_w_7 | 0x3a0 (kernels.cu:1093) | 0xbf0 (kernels.cu:1100) | shared | RAW | block | block | model_bug | True |  | 224760 {'warp': 203950, 'block': 20810} |
| gcrs_m_4_w_8 | 0x300 (kernels.cu:1157) | 0x3a0 (kernels.cu:1164) | shared | RAW | warp | block | model_bug | True |  | 70 {'warp': 70} |
| gcrs_m_4_w_8 | 0x300 (kernels.cu:1157) | 0x650 (kernels.cu:1164) | shared | RAW | warp | block | model_bug | True |  | 70 {'warp': 70} |
| gcrs_m_4_w_8 | 0x300 (kernels.cu:1157) | 0x990 (kernels.cu:1164) | shared | RAW | warp | block | model_bug | True |  | 70 {'warp': 70} |
| gcrs_m_4_w_8 | 0x300 (kernels.cu:1157) | 0xc10 (kernels.cu:1164) | shared | RAW | warp | block | model_bug | True |  | 70 {'warp': 70} |

## scalar-clock: 50 kernel dumps, 7 deduped reports (harness dedup key: pc pair + space)

| dump | kernel | grid×block | MB | events | reports | tv_violation | barrier instances fired / released short / left open | threads never seen per block |
|---|---|---|---|---|---|---|---|---|
| kernel_0.json | gcrs_m_1_w_4 | [1024, 1, 1]×[128, 1, 1] | 47 | 45056 | 0 |  | 2048 / 0 {} / 0 | {'0': 1024} |
| kernel_1.json | gcrs_m_1_w_4 | [1024, 1, 1]×[128, 1, 1] | 89 | 86016 | 0 |  | 4096 / 0 {} / 0 | {'0': 1024} |
| kernel_2.json | gcrs_m_1_w_4 | [1024, 1, 1]×[128, 1, 1] | 130 | 126976 | 0 |  | 6144 / 0 {} / 0 | {'0': 1024} |
| kernel_3.json | gcrs_m_1_w_4 | [1024, 1, 1]×[128, 1, 1] | 172 | 167936 | 0 |  | 8192 / 0 {} / 0 | {'0': 1024} |
| kernel_4.json | gcrs_m_1_w_5 | [1093, 1, 1]×[128, 1, 1] | 65 | 62925 | 0 |  | 0 / 2098 {'75/128': 2, '125/128': 2096} / 0 | {'3': 1048, '53': 1} |
| kernel_5.json | gcrs_m_1_w_5 | [1093, 1, 1]×[128, 1, 1] | 125 | 121655 | 0 |  | 0 / 4196 {'75/128': 4, '125/128': 4192} / 0 | {'3': 1048, '53': 1} |
| kernel_6.json | gcrs_m_1_w_5 | [1093, 1, 1]×[128, 1, 1] | 184 | 180385 | 5 |  | 0 / 6294 {'75/128': 6, '125/128': 6288} / 0 | {'3': 1048, '53': 1} |
| kernel_7.json | gcrs_m_1_w_5 | [1093, 1, 1]×[128, 1, 1] | 244 | 239115 | 0 |  | 0 / 8392 {'75/128': 8, '125/128': 8384} / 0 | {'3': 1048, '53': 1} |
| kernel_8.json | gcrs_m_1_w_6 | [1093, 1, 1]×[128, 1, 1] | 75 | 70754 | 0 |  | 0 / 2082 {'36/128': 2, '126/128': 2080} / 0 | {'2': 1040, '92': 1} |
| kernel_9.json | gcrs_m_1_w_6 | [1093, 1, 1]×[128, 1, 1] | 144 | 137346 | 0 |  | 0 / 4164 {'36/128': 4, '126/128': 4160} / 0 | {'2': 1040, '92': 1} |
| kernel_10.json | gcrs_m_1_w_6 | [1093, 1, 1]×[128, 1, 1] | 213 | 203938 | 0 |  | 0 / 6246 {'36/128': 6, '126/128': 6240} / 0 | {'2': 1040, '92': 1} |
| kernel_11.json | gcrs_m_1_w_6 | [1093, 1, 1]×[128, 1, 1] | 283 | 270530 | 0 |  | 0 / 8328 {'36/128': 8, '126/128': 8320} / 0 | {'2': 1040, '92': 1} |
| kernel_12.json | gcrs_m_1_w_7 | [1171, 1, 1]×[128, 1, 1] | 85 | 79078 | 0 |  | 0 / 2082 {'42/128': 2, '126/128': 2080} / 0 | {'2': 1040, '86': 1} |
| kernel_13.json | gcrs_m_1_w_7 | [1171, 1, 1]×[128, 1, 1] | 164 | 153994 | 0 |  | 0 / 4164 {'42/128': 4, '126/128': 4160} / 0 | {'2': 1040, '86': 1} |
| kernel_14.json | gcrs_m_1_w_7 | [1171, 1, 1]×[128, 1, 1] | 243 | 228910 | 0 |  | 0 / 6246 {'42/128': 6, '126/128': 6240} / 0 | {'2': 1040, '86': 1} |
| kernel_15.json | gcrs_m_1_w_7 | [1171, 1, 1]×[128, 1, 1] | 321 | 303826 | 0 |  | 0 / 8328 {'42/128': 8, '126/128': 8320} / 0 | {'2': 1040, '86': 1} |
| kernel_16.json | gcrs_m_1_w_8 | [1025, 1, 1]×[128, 1, 1] | 78 | 69649 | 0 |  | 2048 / 2 {'16/128': 2} / 0 | {'0': 1024, '112': 1} |
| kernel_17.json | gcrs_m_1_w_8 | [1025, 1, 1]×[128, 1, 1] | 150 | 135201 | 0 |  | 4096 / 4 {'16/128': 4} / 0 | {'0': 1024, '112': 1} |
| kernel_18.json | gcrs_m_1_w_8 | [1025, 1, 1]×[128, 1, 1] | 222 | 200753 | 0 |  | 6144 / 6 {'16/128': 6} / 0 | {'0': 1024, '112': 1} |
| kernel_19.json | gcrs_m_1_w_8 | [1025, 1, 1]×[128, 1, 1] | 295 | 266305 | 0 |  | 8192 / 8 {'16/128': 8} / 0 | {'0': 1024, '112': 1} |
| kernel_20.json | gcrs_m_2_w_4 | [1025, 1, 1]×[128, 1, 1] | 94 | 90134 | 0 |  | 4096 / 4 {'16/128': 4} / 0 | {'0': 1024, '112': 1} |
| kernel_21.json | gcrs_m_2_w_4 | [1025, 1, 1]×[128, 1, 1] | 136 | 131104 | 2 |  | 6144 / 6 {'16/128': 6} / 0 | {'0': 1024, '112': 1} |
| kernel_22.json | gcrs_m_2_w_4 | [1025, 1, 1]×[128, 1, 1] | 178 | 172074 | 0 |  | 8192 / 8 {'16/128': 8} / 0 | {'0': 1024, '112': 1} |
| kernel_23.json | gcrs_m_2_w_5 | [1093, 1, 1]×[128, 1, 1] | 130 | 125850 | 0 |  | 0 / 4196 {'90/128': 4, '125/128': 4192} / 0 | {'3': 1048, '38': 1} |
| kernel_24.json | gcrs_m_2_w_5 | [1093, 1, 1]×[128, 1, 1] | 190 | 184580 | 0 |  | 0 / 6294 {'90/128': 6, '125/128': 6288} / 0 | {'3': 1048, '38': 1} |
| kernel_25.json | gcrs_m_2_w_5 | [1093, 1, 1]×[128, 1, 1] | 250 | 243310 | 0 |  | 0 / 8392 {'90/128': 8, '125/128': 8384} / 0 | {'3': 1048, '38': 1} |
| kernel_26.json | gcrs_m_2_w_6 | [1093, 1, 1]×[128, 1, 1] | 150 | 141508 | 0 |  | 0 / 4164 {'54/128': 4, '126/128': 4160} / 0 | {'2': 1040, '74': 1} |
| kernel_27.json | gcrs_m_2_w_6 | [1093, 1, 1]×[128, 1, 1] | 219 | 208100 | 0 |  | 0 / 6246 {'54/128': 6, '126/128': 6240} / 0 | {'2': 1040, '74': 1} |
| kernel_28.json | gcrs_m_2_w_6 | [1093, 1, 1]×[128, 1, 1] | 288 | 274692 | 0 |  | 0 / 8328 {'54/128': 8, '126/128': 8320} / 0 | {'2': 1040, '74': 1} |
| kernel_29.json | gcrs_m_2_w_7 | [1171, 1, 1]×[128, 1, 1] | 169 | 158156 | 0 |  | 0 / 4164 {'56/128': 4, '126/128': 4160} / 0 | {'2': 1040, '72': 1} |
| kernel_30.json | gcrs_m_2_w_7 | [1171, 1, 1]×[128, 1, 1] | 248 | 233072 | 0 |  | 0 / 6246 {'56/128': 6, '126/128': 6240} / 0 | {'2': 1040, '72': 1} |
| kernel_31.json | gcrs_m_2_w_7 | [1171, 1, 1]×[128, 1, 1] | 327 | 307988 | 0 |  | 0 / 8328 {'56/128': 8, '126/128': 8320} / 0 | {'2': 1040, '72': 1} |
| kernel_32.json | gcrs_m_2_w_8 | [1025, 1, 1]×[128, 1, 1] | 156 | 139298 | 0 |  | 4096 / 4 {'24/128': 4} / 0 | {'0': 1024, '104': 1} |
| kernel_33.json | gcrs_m_2_w_8 | [1025, 1, 1]×[128, 1, 1] | 228 | 204850 | 0 |  | 6144 / 6 {'24/128': 6} / 0 | {'0': 1024, '104': 1} |
| kernel_34.json | gcrs_m_2_w_8 | [1025, 1, 1]×[128, 1, 1] | 300 | 270402 | 0 |  | 8192 / 8 {'24/128': 8} / 0 | {'0': 1024, '104': 1} |
| kernel_35.json | gcrs_m_3_w_4 | [1025, 1, 1]×[128, 1, 1] | 142 | 135201 | 0 |  | 6144 / 6 {'24/128': 6} / 0 | {'0': 1024, '104': 1} |
| kernel_36.json | gcrs_m_3_w_4 | [1025, 1, 1]×[128, 1, 1] | 183 | 176171 | 0 |  | 8192 / 8 {'24/128': 8} / 0 | {'0': 1024, '104': 1} |
| kernel_37.json | gcrs_m_3_w_5 | [1093, 1, 1]×[128, 1, 1] | 196 | 188820 | 0 |  | 0 / 6294 {'100/128': 6, '125/128': 6288} / 0 | {'3': 1048, '28': 1} |
| kernel_38.json | gcrs_m_3_w_5 | [1093, 1, 1]×[128, 1, 1] | 255 | 247564 | 0 |  | 0 / 8392 {'100/128': 8, '125/128': 8384} / 0 | {'3': 1048, '28': 1} |
| kernel_39.json | gcrs_m_3_w_6 | [1093, 1, 1]×[128, 1, 1] | 225 | 212262 | 0 |  | 0 / 6246 {'60/128': 6, '126/128': 6240} / 0 | {'2': 1040, '68': 1} |
| kernel_40.json | gcrs_m_3_w_6 | [1093, 1, 1]×[128, 1, 1] | 294 | 278854 | 0 |  | 0 / 8328 {'60/128': 8, '126/128': 8320} / 0 | {'2': 1040, '68': 1} |
| kernel_41.json | gcrs_m_3_w_7 | [1171, 1, 1]×[128, 1, 1] | 254 | 237234 | 0 |  | 0 / 6246 {'63/128': 6, '126/128': 6240} / 0 | {'2': 1040, '65': 1} |
| kernel_42.json | gcrs_m_3_w_7 | [1171, 1, 1]×[128, 1, 1] | 333 | 312150 | 0 |  | 0 / 8328 {'63/128': 8, '126/128': 8320} / 0 | {'2': 1040, '65': 1} |
| kernel_43.json | gcrs_m_3_w_8 | [1025, 1, 1]×[128, 1, 1] | 234 | 208947 | 0 |  | 6144 / 6 {'32/128': 6} / 0 | {'0': 1024, '96': 1} |
| kernel_44.json | gcrs_m_3_w_8 | [1025, 1, 1]×[128, 1, 1] | 306 | 274499 | 0 |  | 8192 / 8 {'32/128': 8} / 0 | {'0': 1024, '96': 1} |
| kernel_45.json | gcrs_m_4_w_4 | [1025, 1, 1]×[128, 1, 1] | 189 | 180268 | 0 |  | 8192 / 8 {'32/128': 8} / 0 | {'0': 1024, '96': 1} |
| kernel_46.json | gcrs_m_4_w_5 | [1093, 1, 1]×[128, 1, 1] | 261 | 251760 | 0 |  | 0 / 8392 {'105/128': 8, '125/128': 8384} / 0 | {'3': 1048, '23': 1} |
| kernel_47.json | gcrs_m_4_w_6 | [1093, 1, 1]×[128, 1, 1] | 300 | 283084 | 0 |  | 0 / 8328 {'66/128': 8, '126/128': 8320} / 0 | {'2': 1040, '62': 1} |
| kernel_48.json | gcrs_m_4_w_7 | [1171, 1, 1]×[128, 1, 1] | 339 | 316388 | 0 |  | 0 / 8328 {'70/128': 8, '126/128': 8320} / 0 | {'2': 1040, '58': 1} |
| kernel_49.json | gcrs_m_4_w_8 | [1025, 1, 1]×[128, 1, 1] | 312 | 278664 | 0 |  | 8192 / 8 {'40/128': 8} / 0 | {'0': 1024, '88': 1} |

| kernel | anc pc (line) | cur pc (line) | space | type | dist | strength | hb_class | event_cand | chain | engine records (relation) |
|---|---|---|---|---|---|---|---|---|---|---|
| gcrs_m_1_w_5 | 0x570 (kernels.cu:95) | 0x970 (kernels.cu:88) | shared | WAR | block | none | None | False |  |  |
| gcrs_m_1_w_5 | 0x580 (kernels.cu:95) | 0x970 (kernels.cu:88) | shared | WAR | block | none | None | False |  |  |
| gcrs_m_1_w_5 | 0x5a0 (kernels.cu:95) | 0x970 (kernels.cu:88) | shared | WAR | block | none | None | False |  |  |
| gcrs_m_1_w_5 | 0x640 (kernels.cu:95) | 0x970 (kernels.cu:88) | shared | WAR | block | none | None | False |  |  |
| gcrs_m_1_w_5 | 0x690 (kernels.cu:95) | 0x970 (kernels.cu:88) | shared | WAR | block | none | None | False |  |  |
| gcrs_m_2_w_4 | 0x610 (kernels.cu:306) | 0xb50 (kernels.cu:299) | shared | WAR | warp | none | None | True |  |  |
| gcrs_m_2_w_4 | 0x740 (kernels.cu:306) | 0xb50 (kernels.cu:299) | shared | WAR | warp | none | None | True |  |  |

