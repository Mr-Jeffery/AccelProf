// T24 positive control (eval/SYNCWARP_INSTANCE.md): testdata/syncwarp_diverged_waw.cu with ECL-CC's
// first __syncwarp() put back. That one is reached converged (one syncwarp record, active mask
// 0xffffffff) between lane 0's clear and lane 16's set, so it orders the WAW: CLEAN in both modes.
// The second __syncwarp() still runs in two groups, as in the race kernel.
#define FIRST_SYNCWARP 1
#include "syncwarp_diverged_waw.cu"
