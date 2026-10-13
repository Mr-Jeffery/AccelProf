#!/usr/bin/env bash
#SBATCH --job-name=t0-probe
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=02:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/wt-T0/eval/baselines/setup/build_logs/t0-probe-%j.log
# T0 step 1 -- BeeGFS facts measured on ONE node. Submit once per partition kind:
#   sbatch -p rtx4060ti16g eval/baselines/setup/t0_fs_probe.sh
#   sbatch -p normal       eval/baselines/setup/t0_fs_probe.sh
# Records: mount presence, df, beegfs-ctl quota, the per-user dir, a 20 GB dd
# write + read, a 100 000 x 4 KB small-file write/list/read (kernel_N.json-sized),
# and the deletes, all timed. Everything it creates is removed at the end.
set -u
U=${USER}
B=/mnt/beegfs/$U
PY=/home/fzheng4/AccelProf/.env/bin/python
now() { date +%s.%N; }
el() { $PY -c "print(f'{float(\"$2\")-float(\"$1\"):.1f}')"; }
echo "== host $(hostname)  date $(date -Is)  partition ${SLURM_JOB_PARTITION:-?}  job ${SLURM_JOB_ID:-?}"
echo "== gpu"; nvidia-smi --query-gpu=name,compute_cap --format=csv 2>&1 | head -3
echo "== mem"; free -g | head -2
echo "== kernel"; uname -r
echo "== mount"; mount | grep -i beegfs || echo "NO beegfs mount"
echo "== df"; df -h /mnt/beegfs /mnt/local /tmp /home/$U 2>&1
echo "== beegfs-ctl"; which beegfs-ctl 2>&1
beegfs-ctl --getquota --uid "$(id -u)" 2>&1 | head -8
beegfs-ctl --getquota --gid "$(id -g)" 2>&1 | head -8
echo "== userdir before"; ls -ld /mnt/beegfs "$B" 2>&1
mkdir -p "$B" && chmod 700 "$B"; ls -ld "$B"
echo "== stores"; ls -la "$B/" 2>&1
echo "== du stores (may take a while)"; t0=$(now); du -sh "$B"/cuvein_traces/* 2>&1; echo "du wall=$(el $t0 $(now)) s"
P=$B/t0_probe_$(hostname)_$$
mkdir -p "$P"
echo "== dd 20 GB write (bs=1M count=20480 conv=fsync)"
t0=$(now); dd if=/dev/zero of="$P/big.bin" bs=1M count=20480 conv=fsync 2>&1; echo "dd-write wall=$(el $t0 $(now)) s"
ls -l "$P/big.bin"
echo "== dd 20 GB read (iflag=direct, bypasses the page cache; falls back to a plain read)"
t0=$(now); dd if="$P/big.bin" of=/dev/null bs=1M iflag=direct 2>&1 || dd if="$P/big.bin" of=/dev/null bs=1M 2>&1; echo "dd-read wall=$(el $t0 $(now)) s"
echo "== 100000 x 4 KB files (100 dirs x 1000 files)"
$PY - "$P" <<'PYEOF'
import os, sys, time
root = sys.argv[1]
payload = (b'{"hb_events": [' + b'0,' * 2100 + b'0]}\n')[:4096]
t0 = time.time()
for d in range(100):
    dd = f"{root}/small/{d:03d}"
    os.makedirs(dd, exist_ok=True)
    for i in range(1000):
        with open(f"{dd}/kernel_{i}.json", "wb") as fh:
            fh.write(payload)
t1 = time.time()
print(f"write 100000 x 4KB: {t1-t0:.1f} s ({100000/(t1-t0):.0f} files/s)", flush=True)
t0 = time.time()
n = sum(len(os.listdir(f"{root}/small/{d:03d}")) for d in range(100))
t1 = time.time()
print(f"listdir 100 dirs ({n} entries): {t1-t0:.2f} s", flush=True)
t0 = time.time()
for d in range(100):
    dd = f"{root}/small/{d:03d}"
    for i in range(1000):
        with open(f"{dd}/kernel_{i}.json", "rb") as fh:
            fh.read()
t1 = time.time()
print(f"read 100000 x 4KB: {t1-t0:.1f} s ({100000/(t1-t0):.0f} files/s)", flush=True)
PYEOF
echo "== du probe dir"; du -sh "$P"
echo "== delete"
t0=$(now); rm -f "$P/big.bin"; echo "rm big wall=$(el $t0 $(now)) s"
t0=$(now); rm -rf "$P/small"; echo "rm 100000 small wall=$(el $t0 $(now)) s"
rmdir "$P"; ls -ld "$P" 2>&1
echo "== df after"; df -h /mnt/beegfs 2>&1
echo "== done $(date -Is)"
