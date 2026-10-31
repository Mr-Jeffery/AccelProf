#!/bin/bash
# assemble eval/CAP_84600.md from the generated tables and the two hand-written parts
set -e
cd /home/fzheng4/wt-x7b; PY=/home/fzheng4/AccelProf/.env/bin/python; S=eval/baselines/setup/cap_doc
N=eval/results/cap-84600
$PY eval/baselines/setup/cap_report.py 2> $N/tables/changed_counts.txt | sed 's/^## /### /' > /tmp/x7b_r1.md
$PY eval/baselines/setup/cap_report2.py > /tmp/x7b_r2.md
{ cat $S/cap_head.md
  # report2 section 1 (before "## 2.")
  sed -n '1,/^## 2\. /p' /tmp/x7b_r2.md | sed '$d'
  echo "## 2. Cells that change in the paper's tables"; echo
  echo "Old = the state before the merge (section Inputs), new = after; cells of the other columns and rows do not change."; echo
  cat /tmp/x7b_r1.md
  echo
  sed -n '/^## 2\. cuRace cost/,$p' /tmp/x7b_r2.md | sed 's/^## 2\. cuRace cost/## 3. cuRace cost/; s/^## 3\. Where the time goes: five programs/### Where the time goes: five programs/; s/^## 5\. Rows still TIMEOUT/## 6. Rows still TIMEOUT/' | awk '/^## 6\. /{hold=1} hold{h=h $0 "\n"; next} {print} END{printf "%s", h > "/tmp/x7b_to.md"}'
  cat $S/cap_tail_a.md
  cat /tmp/x7b_to.md; echo
  cat $S/cap_tail_b.md
} > eval/CAP_84600.md
wc -l eval/CAP_84600.md
