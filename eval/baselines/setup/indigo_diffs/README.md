# Indigo3 build diff (CUDA 13 compat)

Required to build P1/P3 at all on CUDA 13.3: `cudaDeviceProp::clockRate` and
`::memoryClockRate` were REMOVED in CUDA 13.x. Indigo3's `lib/indigo_*_cuda.h`
use them only in a one-line diagnostic printf ("... %.1f MHz and %.1f MHz",
deviceProp.clockRate*0.001, deviceProp.memoryClockRate*0.001). Patched to 0 in
13 cuda headers via:
  sed -i 's/[A-Za-z_]*\.memoryClockRate/0/g; s/[A-Za-z_]*\.clockRate/0/g' lib/*_cuda.h
Affects only the GPU-info printout, NOT kernel/race behavior. Original lines in
clockRate_before.txt. This is the only benchmark-source edit (a toolchain-compat
fix, not a semantic change).
