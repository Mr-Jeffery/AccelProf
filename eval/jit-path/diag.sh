#!/bin/bash
#SBATCH -J m3-diag -p rtx4060ti16g -N1 -t 00:10:00 --exclude=c0,c1,c2,c37,c54,c79 -o /home/fzheng4/m3work/diag-%j.log
hostname; nvidia-smi | sed -n 3,4p; ls -d /usr/local/cuda*
export LD_LIBRARY_PATH=/usr/local/cuda-13.4/lib64:$LD_LIBRARY_PATH
cd /home/fzheng4/m3work/out/litmus_ptx; ./race_interwarp_none-atom_waw; echo "native rc=$?"
head -5 $(cuobjdump -lptx race_interwarp_none-atom_waw >/dev/null; echo /dev/null) 2>/dev/null
cuobjdump -ptx race_interwarp_none-atom_waw | grep -E '^\.version|^\.target'
for v in /usr/local/cuda-13.0 /usr/local/cuda-12.9; do [ -x $v/bin/nvcc ] && echo "have $v $($v/bin/nvcc --version | tail -1)"; done
ls ~/spack/opt/spack/*/ 2>/dev/null | grep -i cuda
