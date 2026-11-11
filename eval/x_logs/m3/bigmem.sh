#!/bin/bash
# the two P4 matrix-multiplication-large recordings that hit the 6 GB / 10 GB address-space cap: 70 GB, one at a time
cd /home/fzheng4/wt-m2
PY=/home/fzheng4/AccelProf/.env/bin/python
$PY eval/baselines/mode_pairs.py collect --out eval/results/r1-distance/mode-pairs-after --id-file eval/x_logs/m3/bigmem_ids.txt --force --mem-gb 70 --timeout 14400
CUVEIN_R1_OBSERVED_ONLY=1 $PY eval/baselines/mode_pairs.py collect --out eval/results/r1-distance/mode-pairs-before --id-file eval/x_logs/m3/bigmem_ids.txt --force --mem-gb 70 --timeout 14400
$PY eval/baselines/r1_distance.py collect --id-file eval/x_logs/m3/bigmem_ids.txt --force --workers 1 --mem-gb 70 --timeout 14400
