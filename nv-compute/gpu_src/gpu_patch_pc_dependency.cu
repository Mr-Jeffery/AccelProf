#include "gpu_patch.h"

#include <sanitizer_patching.h>

#include "gpu_utils.h"
#include <cstdio>


static __device__ __inline__
uint32_t GetBufferIndex(MemoryAccessTracker* pTracker) {
    uint32_t idx = MEMORY_ACCESS_BUFFER_SIZE;

    while (idx >= MEMORY_ACCESS_BUFFER_SIZE) {
        idx = atomicAdd(&(pTracker->currentEntry), 1);

        if (idx >= MEMORY_ACCESS_BUFFER_SIZE) {
            // buffer is full, wait for last writing thread to flush
            while (*(volatile uint32_t*)&(pTracker->currentEntry) >= MEMORY_ACCESS_BUFFER_SIZE);
            __threadfence();
        }
    }

    return idx;
}

static __device__ __inline__
void IncrementNumEntries(MemoryAccessTracker* pTracker) {
    DoorBell* doorbell = pTracker->doorBell;
    __threadfence();
    const uint32_t numEntries = atomicAdd((int*)&(pTracker->numEntries), 1);

    if (numEntries == MEMORY_ACCESS_BUFFER_SIZE - 1) {
        // make sure everything is visible in memory
        __threadfence_system();
        doorbell->full = true;
        __threadfence_system();
        while (doorbell->full);

        // pTracker->numEntries = 0;
        atomicExch((uint32_t*)&(pTracker->numEntries), static_cast<uint32_t>(0));
        __threadfence();
        // pTracker->currentEntry = 0;
        atomicExch((uint32_t*)&(pTracker->currentEntry), static_cast<uint32_t>(0));
    }
}

// T15 (eval/LATE_SEQ.md): the late ordering key. The buffer index (GetBufferIndex) is drawn
// at the start of a callback; between it and the instruction lie the record writes, two
// __syncwarps, the address shuffle, a __threadfence and the numEntries atomic. With
// tracker->late_keys set (YOSEMITE_HB_TRACE + YOSEMITE_HB_LATE_SEQ, pc_dependency only), the
// committing lane draws a second key after the commit, as its last action, and stores it in
// late_keys[slot] -- a side array parallel to the record buffer; MemoryAccess is unchanged,
// so no reader of the record sees a new field. The host waits for every slot's key before
// it drains a buffer. The one exception is the lane whose commit fills the buffer: it draws
// its key before ringing the doorbell and waiting for the drain (it must: the drain needs
// the key), so its key precedes that wait -- one record per MEMORY_ACCESS_BUFFER_SIZE.
// T18: compiled only into the late-key variant (gpu_patch_pc_dependency_late.cu defines
// HB_LATE_SEQ); the default fatbin has no late-key code, no tracker-field load and no extra
// __syncwarp in the record callback. The collector loads the variant at module load, by
// YOSEMITE_HB_LATE_SEQ.
#ifdef HB_LATE_SEQ
static __device__ __inline__
uint64_t DrawLateKey(MemoryAccessTracker* pTracker) {
    if (pTracker->late_mode == 2) {
        uint64_t t;
        asm volatile("mov.u64 %0, %%globaltimer;" : "=l"(t));
        return t | 1ull;          // never 0 (0 = "not yet written" for the host)
    }
    return atomicAdd((unsigned long long*)pTracker->late_counter, 1ull) + 1ull;
}

static __device__ __inline__
void CommitRecord(MemoryAccessTracker* pTracker, uint32_t idx) {
    if (pTracker->late_keys == nullptr) {
        IncrementNumEntries(pTracker);
        return;
    }
    DoorBell* doorbell = pTracker->doorBell;
    __threadfence();
    const uint32_t numEntries = atomicAdd((int*)&(pTracker->numEntries), 1);
    ((volatile uint64_t*)pTracker->late_keys)[idx] = DrawLateKey(pTracker);

    if (numEntries == MEMORY_ACCESS_BUFFER_SIZE - 1) {
        __threadfence_system();
        doorbell->full = true;
        __threadfence_system();
        while (doorbell->full);

        atomicExch((uint32_t*)&(pTracker->numEntries), static_cast<uint32_t>(0));
        __threadfence();
        atomicExch((uint32_t*)&(pTracker->currentEntry), static_cast<uint32_t>(0));
    }
}
#else
static __device__ __inline__
void CommitRecord(MemoryAccessTracker* pTracker, uint32_t) {
    IncrementNumEntries(pTracker);
}
#endif

static __device__
SanitizerPatchResult CommonCallback(
    void* userdata,
    uint64_t pc,
    void* ptr,
    uint32_t accessSize,
    uint32_t flags,
    MemoryType type)
{
    auto* pTracker = (MemoryAccessTracker*)userdata;
    if (!pTracker->enabled_instrumenting) {
        return SANITIZER_PATCH_SUCCESS;
    }

    uint32_t active_mask = __activemask();
    uint32_t laneid = get_laneid();
    uint32_t first_laneid = __ffs(active_mask) - 1;

    MemoryAccess* accesses = nullptr;
    uint32_t idx = 0;

    uint32_t distinct_sector_count = get_distint_sector_count((uint64_t)(uintptr_t)ptr/32, active_mask); // sector size is 32 bytes so we divide by 32 to get the sector tag
    uint32_t unique_address_mask = get_unique_address_mask((uint64_t)(uintptr_t)ptr, active_mask);

    if (laneid == first_laneid) {
        idx = GetBufferIndex(pTracker);
        accesses = &pTracker->access_buffer[idx];
        accesses->accessSize = accessSize;
        accesses->flags = flags;
        accesses->distinct_sector_count = distinct_sector_count;
        accesses->unique_address_mask = unique_address_mask;
        accesses->warpId = get_flat_thread_id() / GPU_WARP_SIZE;
        accesses->ctaId = get_ctaid_as_uint64();
        accesses->type = type;
        accesses->pc = pc - pTracker->kernel_pc; // for in-gpu pc offset calculation, so that the pc in corresponding analysis tool can be saved only in uint32_t
        accesses->active_mask = active_mask;
    }

    __syncwarp(active_mask);

    accesses = (MemoryAccess*) shfl((uint64_t)accesses, first_laneid, active_mask);
    if (accesses) {
        if(type == MemoryType::Local){
            accesses->addresses[laneid] = ((get_flat_thread_id()) << 54) |((uint64_t)(uintptr_t)ptr); // use high 10 bits to store thread id for local memory access
        } else {
            accesses->addresses[laneid] = (uint64_t)(uintptr_t)ptr;
        }
    }

    __syncwarp(active_mask);

    if (laneid == first_laneid) {
        CommitRecord(pTracker, idx);
    }
    // T15: with the late key, no lane may leave before its record's key is drawn -- else a
    // non-committing lane could reach its next record (and its key) first, breaking W0.
#ifdef HB_LATE_SEQ
    if (pTracker->late_keys != nullptr) {
        __syncwarp(active_mask);
    }
#endif

    return SANITIZER_PATCH_SUCCESS;
}

extern "C" __device__ __noinline__
SanitizerPatchResult MemoryGlobalAccessCallback(
    void* userdata,
    uint64_t pc,
    void* ptr,
    uint32_t accessSize,
    uint32_t flags,
    const void *pData)
{
    return CommonCallback(userdata, pc, ptr, accessSize, flags, MemoryType::Global);
}

extern "C" __device__ __noinline__
SanitizerPatchResult MemorySharedAccessCallback(
    void* userdata,
    uint64_t pc,
    void* ptr,
    uint32_t accessSize,
    uint32_t flags,
    const void *pData)
{
    return CommonCallback(userdata, pc, ptr, accessSize, flags, MemoryType::Shared);
}

extern "C" __device__ __noinline__
SanitizerPatchResult MemoryLocalAccessCallback(
    void* userdata,
    uint64_t pc,
    void* ptr,
    uint32_t accessSize,
    uint32_t flags,
    const void *pData)
{
    return CommonCallback(userdata, pc, ptr, accessSize, flags, MemoryType::Local);
}

//For the future use of async memcpy
extern "C" __device__ __noinline__
SanitizerPatchResult MemcpyAsyncCallback(void* userdata, uint64_t pc, void* src, uint32_t dst, uint32_t accessSize)
{
    if (src)
    {
        CommonCallback(userdata, pc, src, accessSize, SANITIZER_MEMORY_DEVICE_FLAG_READ, MemoryType::Global);
    }

    return CommonCallback(userdata, pc, (void*)dst, accessSize, SANITIZER_MEMORY_DEVICE_FLAG_WRITE, MemoryType::Shared);
}

// Phase 2: emit one sync event per warp per sync instance into the trace stream.
// First active lane writes the record; carries no per-lane addresses, so no shfl
// fan-out and no doorbell thread-count change (a sync is not a block exit).
static __device__ __inline__
void EmitSyncEvent(MemoryAccessTracker* tracker, uint64_t pc, MemoryType type,
                   uint32_t aux_size, uint32_t aux_flags)
{
    if (!tracker->enabled_instrumenting) {
        return;
    }
    uint32_t active_mask = __activemask();
    uint32_t laneid = get_laneid();
    uint32_t first_laneid = __ffs(active_mask) - 1;
    if (laneid == first_laneid) {
        uint32_t idx = GetBufferIndex(tracker);
        MemoryAccess* access = &tracker->access_buffer[idx];
        access->accessSize = aux_size;
        access->flags = aux_flags;
        access->distinct_sector_count = 0;
        access->unique_address_mask = 0;
        access->warpId = get_flat_thread_id() / GPU_WARP_SIZE;
        access->ctaId = get_ctaid_as_uint64();
        access->type = type;
        access->pc = pc - tracker->kernel_pc;
        access->active_mask = active_mask;
        CommitRecord(tracker, idx);
    }
    __syncwarp(active_mask);
}

extern "C" __device__ __noinline__
SanitizerPatchResult BarrierCallback(void* userdata, uint64_t pc, uint32_t barIndex,
                                     uint32_t threadCount, uint32_t flags)
{
    EmitSyncEvent((MemoryAccessTracker*)userdata, pc, MemoryType::Barrier,
                  threadCount, barIndex);
    return SANITIZER_PATCH_SUCCESS;
}

extern "C" __device__ __noinline__
SanitizerPatchResult SyncwarpCallback(void* userdata, uint64_t pc, uint32_t mask)
{
    EmitSyncEvent((MemoryAccessTracker*)userdata, pc, MemoryType::Syncwarp, mask, 0);
    return SANITIZER_PATCH_SUCCESS;
}

// T1a (eval/CP_ASYNC_REPORT.md): the completion points of cp.async copies. Registered only
// for HB-trace runs; one record per warp like a barrier (active_mask = the lanes).
extern "C" __device__ __noinline__
SanitizerPatchResult PipelineCommitCallback(void* userdata, uint64_t pc)
{
    EmitSyncEvent((MemoryAccessTracker*)userdata, pc, MemoryType::PipelineCommit, 0, 0);
    return SANITIZER_PATCH_SUCCESS;
}

extern "C" __device__ __noinline__
SanitizerPatchResult PipelineWaitCallback(void* userdata, uint64_t pc, uint32_t groups)
{
    EmitSyncEvent((MemoryAccessTracker*)userdata, pc, MemoryType::PipelineWait, groups, 0);
    return SANITIZER_PATCH_SUCCESS;
}

extern "C" __device__ __noinline__
SanitizerPatchResult BlockExitCallback(void* userdata, uint64_t pc)
{

    MemoryAccessTracker* tracker = (MemoryAccessTracker*)userdata;
    if (!tracker->enabled_instrumenting) {
        return SANITIZER_PATCH_SUCCESS;
    }
    DoorBell* doorbell = tracker->doorBell;

    uint32_t active_mask = __activemask();
    uint32_t laneid = get_laneid();
    uint32_t first_laneid = __ffs(active_mask) - 1;
    int32_t pop_count = __popc(active_mask);

    if (laneid == first_laneid) {
        uint32_t idx = GetBufferIndex(tracker);
        MemoryAccess* access = &tracker->access_buffer[idx];
        access->accessSize = 0;
        access->flags = 0;
        access->distinct_sector_count = 0;
        access->warpId = get_flat_thread_id() / GPU_WARP_SIZE;
        access->ctaId = get_ctaid_as_uint64();
        access->type = MemoryType::BlockExit;
        access->pc = pc - tracker->kernel_pc;
        access->active_mask = active_mask;
        CommitRecord(tracker, idx);
        atomicSub((uint32_t*)&doorbell->num_threads, static_cast<uint32_t>(pop_count));
        // uint32_t new_num_threads = atomicSub((uint32_t*)&doorbell->num_threads, static_cast<uint32_t>(pop_count));
        // printf("BlockExitCallback:Block id %lu, warp id %d, num_threads = %d, decrement = %d\n", access->ctaId, access->warpId, new_num_threads, pop_count);
        __threadfence_system();
    }
    __syncwarp(active_mask);

    return SANITIZER_PATCH_SUCCESS;
}
