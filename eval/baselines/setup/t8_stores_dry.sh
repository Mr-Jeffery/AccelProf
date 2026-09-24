#!/usr/bin/env bash
#SBATCH --job-name=t8-sdry
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/wt-T8/eval/baselines/setup/t8_check/stores-dry-%j.log
# T8 step 3: migrate_mode_names.py over every kept-trace store and confirm directory in
# home and on BeeGFS. Default: DRY RUN (nothing is changed). APPLY=1 applies it;
# REVERSE=1 APPLY=1 rolls the stores back. Log: setup/migrate_logs/stores.<kind>.txt
A=/home/fzheng4/AccelProf; B=/mnt/beegfs/$USER/cuvein_traces
KIND=dry; [ -n "${APPLY:-}" ] && KIND=apply
[ -n "${REVERSE:-}" ] && KIND=reverse-$KIND   # rollback: REVERSE=1 APPLY=1
/home/fzheng4/AccelProf/.env/bin/python /home/fzheng4/wt-T8/eval/baselines/migrate_mode_names.py --results '' \
    --store "$A/eval/baselines/traces_keep*" --store "$B/*" \
    --confirm "$A/eval/baselines/confirm*" \
    ${APPLY:+--apply} ${REVERSE:+--reverse} --log /home/fzheng4/wt-T8/eval/baselines/setup/migrate_logs/stores.$KIND.txt | tail -1
