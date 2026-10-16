#!/usr/bin/env bash
#SBATCH --job-name=t22-pcmap
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=00:20:00
# T22 §2.2: the instructions (and source lines, if the binary has line info) at the pcs of the largest
# buckets -- bfs Kernel2 0x160, nbody accelerate_particles 0x230 and 0x290.
export PATH=/usr/local/cuda/bin:$PATH
T=$(mktemp -d); cd $T || exit 1
B=/home/fzheng4/AccelProf/eval/baselines/bin/P7
for prog in bfs-cuda:Kernel2:0160 nbody-cuda:accelerate_particles:0230,0290; do
  IFS=: read -r exe kern pcs <<< "$prog"
  mkdir -p $exe && (cd $exe && cuobjdump -xelf all $B/$exe > /dev/null)
  for cb in $exe/*.cubin; do
    nvdisasm -c --print-line-info -fun "$(cuobjdump -symbols $cb 2>/dev/null | grep -o "_Z[0-9]*${kern}[A-Za-z0-9_]*" | head -1)" $cb > $exe.sass 2>/dev/null || continue
    [ -s $exe.sass ] || continue
    echo "== $exe $kern ($cb)"
    for pc in ${pcs//,/ }; do
      grep -n -B3 "/\*$pc\*/" $exe.sass | sed "s/^/   /" | tail -6
    done
  done
done
rm -rf $T
