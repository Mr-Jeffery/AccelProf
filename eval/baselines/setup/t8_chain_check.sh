#!/usr/bin/env bash
#SBATCH --job-name=t8-chain
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=03:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/wt-T8/eval/baselines/setup/t8_check/chain-%j.log
# T8 step 4/5: the p_final2 analysis chain (classify_residuals, classify_endpoints,
# classify_fp_causes, make_tables) BEFORE (pre-T8 code in the T0 worktree, whose tree
# == cuVein, on the unmigrated home stores) and AFTER (T8 worktree, strict: every
# legacy name is an error, on migrated private BeeGFS copies of confirm/ and
# traces_keep/ -- the shared home stores are only read), then compare_fpfix in both.
set -u
PY=/home/fzheng4/AccelProf/.env/bin/python
W0=/home/fzheng4/wt-T0; W8=/home/fzheng4/wt-T8; A=/home/fzheng4/AccelProf
C=/mnt/beegfs/$USER/t8_stores
echo "== host $(hostname) $(date -Is)"
echo "== BEFORE chain (pre-T8 code, $W0 @ $(git -C $W0 rev-parse --short HEAD))"
cd $W0
for s in classify_residuals classify_endpoints classify_fp_causes make_tables; do
  echo "-- $s"; $PY eval/baselines/$s.py 2>&1 | tail -4
done
$PY eval/baselines/compare_fpfix.py > $W8/eval/baselines/setup/t8_check/compare_fpfix.before.txt 2>&1; echo "compare_fpfix before rc=$?"
echo "== copy + migrate confirm/ traces_keep/ into $C"
rm -rf $C; mkdir -p $C
cp -a $A/eval/baselines/confirm $C/confirm && cp -a $A/eval/baselines/traces_keep $C/traces_keep
du -sh $C/*
$PY $W8/eval/baselines/migrate_mode_names.py --results '' --store "$C/traces_keep" --confirm "$C/confirm" --apply \
    --log $W8/eval/baselines/setup/migrate_logs/stores.private-copy.apply.txt | tail -1
$PY $W8/eval/baselines/migrate_mode_names.py --results '' --store "$C/traces_keep" --confirm "$C/confirm" | tail -1
echo "== AFTER chain (T8 code, $W8 @ $(git -C $W8 rev-parse --short HEAD), CUVEIN_NO_LEGACY_NAMES=1)"
cd $W8
rm -f eval/baselines/confirm eval/baselines/traces_keep
ln -s $C/confirm eval/baselines/confirm; ln -s $C/traces_keep eval/baselines/traces_keep
export CUVEIN_NO_LEGACY_NAMES=1
for s in classify_residuals classify_endpoints classify_fp_causes make_tables; do
  echo "-- $s"; $PY eval/baselines/$s.py 2>&1 | tail -4; echo "   rc=${PIPESTATUS[0]}"
done
$PY eval/baselines/compare_fpfix.py > $W8/eval/baselines/setup/t8_check/compare_fpfix.after.txt 2>&1; echo "compare_fpfix after rc=$?"
grep -l "DEPRECATED\|LegacyNameError" $W8/eval/baselines/setup/t8_check/compare_fpfix.after.txt && echo "LEGACY PATH TOUCHED" || echo "no legacy name met in compare_fpfix"
echo "== done $(date -Is)"
