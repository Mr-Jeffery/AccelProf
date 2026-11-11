#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH -t 01:00:00
#SBATCH -J m5-pack
#SBATCH -o /home/fzheng4/wt-m5/eval/x_logs/m5/pack-%j.log
# M5: pack the loose confirm/ record directories and the step-3 probe dirs of eval/results/closure-atomic-hop into one tarball each (the directories are removed after a successful tar -tzf).
cd /home/fzheng4/wt-m5/eval/results/closure-atomic-hop || exit 1
for d in $(find . -type d \( -name confirm -o -name probes \) -not -path "./pairs-invalid*"); do
  tar czf $d.tgz -C $d . && tar tzf $d.tgz > /dev/null && rm -rf $d && echo "packed $d"
done
rm -rf pairs-invalid-beegfs-error
du -sh . ; find . -type f | wc -l
