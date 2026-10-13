/*
 * T13 atom_after: device functions injected by atom_after.cu.
 * Derived from NVBit 1.8 tools/mem_trace/inject_funcs.cu (BSD-3-Clause,
 * Copyright (c) 2019 NVIDIA CORPORATION & AFFILIATES).
 */
#include <stdint.h>
#include <stdio.h>

#include "utils/utils.h"
#include "utils/channel.hpp"
#include "common.h"

static __device__ __forceinline__ void emit(int kind, int opcode_id,
                                            uint32_t pc, uint64_t addr,
                                            uint32_t val, uint64_t launch,
                                            uint64_t pcounter,
                                            uint64_t pchannel_dev) {
    atom_rec_t r;
    r.grid_launch_id = launch;
    r.seq = atomicAdd((unsigned long long*)pcounter, 1ULL);
    r.addr = addr;
    r.val = val;
    r.pc = pc;
    r.cta = blockIdx.x + gridDim.x * (blockIdx.y + gridDim.y * blockIdx.z);
    r.tid = threadIdx.x + blockDim.x * (threadIdx.y + blockDim.y * threadIdx.z);
    r.kind = kind;
    r.opcode_id = opcode_id;
    ((ChannelDev*)pchannel_dev)->push(&r, sizeof(atom_rec_t));
}

/* BEFORE point of a memory instruction (atomic or not): address + seq. */
extern "C" __device__ __noinline__ void aa_before(int pred, int kind,
                                                  int opcode_id, uint32_t pc,
                                                  uint64_t addr,
                                                  uint64_t launch,
                                                  uint64_t pcounter,
                                                  uint64_t pchannel_dev) {
    if (!pred) return;
    emit(kind, opcode_id, pc, addr, 0, launch, pcounter, pchannel_dev);
}

/* AFTER point of an ATOM* (or BEFORE of the next instruction): the value of
 * the atomic's destination register, i.e. the value the RMW read. */
extern "C" __device__ __noinline__ void aa_value(int pred, int kind,
                                                 int opcode_id, uint32_t pc,
                                                 uint32_t val,
                                                 uint64_t launch,
                                                 uint64_t pcounter,
                                                 uint64_t pchannel_dev) {
    if (!pred) return;
    emit(kind, opcode_id, pc, 0, val, launch, pcounter, pchannel_dev);
}
