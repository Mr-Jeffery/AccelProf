/*
 * SPDX-FileCopyrightText: Copyright (c) 2019 NVIDIA CORPORATION & AFFILIATES.
 * All rights reserved.
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 * list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 * this list of conditions and the following disclaimer in the documentation
 * and/or other materials provided with the distribution.
 *
 * 3. Neither the name of the copyright holder nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include <stdint.h>

/* T13 atom_after: one record per lane per instrumentation call, pushed to
 * the host channel. seq is taken by atomicAdd on one global counter, so the
 * records of all threads are totally ordered in one sequence. */
enum {
    REC_MEM_BEFORE = 0,  /* non-atomic memory instruction, IPOINT_BEFORE */
    REC_ATOM_BEFORE = 1, /* ATOM* instruction, IPOINT_BEFORE (address) */
    REC_ATOM_AFTER = 2,  /* ATOM* instruction, IPOINT_AFTER (dest reg value) */
    REC_ATOM_NEXT = 3,   /* ATOM* dest reg read at the next instr's BEFORE */
};

typedef struct {
    uint64_t grid_launch_id;
    uint64_t seq;
    uint64_t addr; /* BEFORE records only */
    uint32_t val;  /* AFTER / NEXT records only: destination register */
    uint32_t pc;   /* instruction offset within the function */
    int32_t cta;   /* linear block id */
    int32_t tid;   /* linear thread id within the block */
    int32_t kind;
    int32_t opcode_id;
} atom_rec_t;
