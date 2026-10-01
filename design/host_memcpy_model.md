# Host copies and cross-stream kernels: the ordering model (T2)

Task T2, step 2 (Claude.md): the model, written before the prototype. Evidence it rests on:
`eval/HOST_MEMCPY_STUDY.md` §1 (what the Compute Sanitizer API reports and in which order).
Location: `docs/` is the AccelProf documentation site (a git submodule of the upstream
`AccelProf/docs` repository), so cuVein design notes live in `design/` in this repository.

## 1. What goes wrong today

A host copy (`cudaMemcpy*`, `cudaMemset*`) is not a kernel instruction: it has no pc, no
thread and no place in any kernel's event stream. The collector sees it — the Sanitizer
calls `SANITIZER_CBID_MEMCPY_STARTING` / `MEMSET_STARTING` at API-call time, in host program
order with the kernel `LAUNCH_BEGIN`/`LAUNCH_END` callbacks — and forwards a `MemCpy_t` event
to every tool, but `PcDependency` drops it (no case in `evt_callback`), and the HB engine
resets its state at every kernel launch. So a copy racing a kernel, or two kernels racing
across streams, is invisible to both modes. What orders these operations is not in-kernel
synchronization but the host API: stream order, events, and synchronize calls.

## 2. Agents and operations

* **Host agent `H`**: issues API calls in program order. One host thread per process
  (assumption A1).
* **One stream agent per stream** `s`, including the legacy default stream `s0` (`NULL`,
  `cudaStreamLegacy`) and a per-thread default stream (`cudaStreamPerThread`) if used.
* **Stream operations**, each issued by `H` onto one stream: kernel launch `K`, copy `M`
  (`cudaMemcpy*`), set `S` (`cudaMemset*`), event record `rec(E)`, stream wait
  `wait(s, E)`. **Host waits**: `cudaStreamSynchronize(s)`, `cudaEventSynchronize(E)`,
  `cudaDeviceSynchronize` / context synchronize, and the implicit wait of a blocking copy
  (§2.2).

### 2.1 Clocks

Vector clocks indexed by stream (the host needs no component of its own: it is a waiter,
not an accessor, in this model). Every stream operation `X` on stream `s` gets the index
`n(X)` = number of operations issued to `s` so far, including `X`.

| event | update |
|---|---|
| issue `X` on stream `s` | `start(X) = C_s ⊔ C_H`; then `C_s[s] = n(X)` |
| issue `X` on `s0` (legacy default stream) | as above, but also `start(X) ⊔= C_b` for every blocking stream `b`, and afterwards `C_b[s0] = n(X)` for every blocking stream `b` |
| `rec(E)` on `s` | `clk(E) = C_s ⊔ C_H` (then as an issue on `s`) |
| `wait(s, E)` | `C_s ⊔= clk(E)` |
| `cudaStreamSynchronize(s)` | `C_H ⊔= C_s` |
| `cudaEventSynchronize(E)` | `C_H ⊔= clk(E)` |
| device / context synchronize | `C_H ⊔= ⊔_s C_s` |
| blocking copy `M` (§2.2) | `C_H ⊔= C_s` after the issue |

`X` happens before `Y` iff `start(Y)[stream(X)] ≥ n(X)`. Stream order gives FIFO for free,
because `C_s[s] = n(X)` is part of every later operation's start clock on `s`. The host
term `C_H` in every start clock carries the host's waits: after `cudaStreamSynchronize(s)`,
every later operation on any stream is ordered after everything issued to `s` before it.

"Blocking" streams are the ones created without `cudaStreamNonBlocking`: they synchronize
with the legacy default stream (the rows for `s0` above). Non-blocking streams do not. The
Sanitizer's `RESOURCE_STREAM_CREATED` callback carries the stream but not its flags, so the
collector reads them with `cuStreamGetFlags` (prototype detail; unverified that the call is
allowed inside the callback).

### 2.2 What each copy/set call guarantees (CUDA Runtime "API synchronization behavior")

| call | host waits for completion? | model |
|---|---|---|
| `cudaMemcpy` pinned host → device, device → host (any host memory), host → host | yes | blocking: `C_H ⊔= C_s` |
| `cudaMemcpy` pageable host → device | returns after staging; the DMA to the destination may still be running | not blocking (the destination write stays concurrent until a later wait) |
| `cudaMemcpy` device → device | no | not blocking |
| `cudaMemcpyAsync` (any) | "might be synchronous" for pageable memory; otherwise no | not blocking (a program cannot rely on "might") |
| `cudaMemset` (device memory) | no ("asynchronous with respect to the host except when the target is pinned host memory") | not blocking |

Every synchronous (non-`Async`) call is issued on the stream the Sanitizer reports as its
API stream, normally `s0`. Whether host memory is pinned is known from the collector's
`cudaMallocHost` / `cudaHostAlloc` callbacks (address ranges).

**Two readings.** The table is the *spec* reading, and it is the verdict. It has a practical
consequence the test suites do not share: a program that initializes device memory with a
synchronous `cudaMemcpy` from pageable memory, or with `cudaMemset`, and then launches on a
**non-blocking** stream races with its own initialization (the kernel's stream does not wait
for the legacy stream, and the copy/set may still be running when the call returns). The
cuHadron `interkernel/*` and `asyncmemcpy/kernel_memcpy_dtoh_race` programs do exactly this
in their *fixed* builds. The *practical* reading treats every synchronous copy/set as
complete when it returns; `python/host_hb.py` computes both and tags a race found only under
the spec reading as `spec_only` (report class `host-spec-only`), so a table can count either.
Which one the paper uses is part of decision D5.

## 3. Accesses and the race condition

* A copy `M` **reads** `[src, src+size)` and **writes** `[dst, dst+size)`; a 2D/3D copy reads
  and writes `height·depth` rows of `width` bytes at the given pitches. Host memory is
  included on purpose: a kernel can touch mapped pinned host memory through its device
  address.
* A set `S` **writes** its range (rows for 2D/3D).
* A kernel `K` reads and writes the global-space addresses its threads access (shared and
  local memory are private to the kernel and cannot conflict with a copy or another
  kernel). An access covers `[addr, addr + size)`.

Operations `X ≠ Y` **race** iff some address is accessed by both, at least one access writes,
and neither happens before the other (§2.1). A report names the address, the two operations
(copy/set: its API call index, direction and range; kernel: its kernel index, and a pc and
thread of one conflicting access) and the kind (RAW / WAR / WAW from the host call order).

## 4. Algorithm

State that survives kernel launches (the in-kernel engine's per-kernel reset does not touch
it): the clocks of §2.1, the list of copy/set operations that are not yet ordered before the
host (`C_H[stream(X)] < n(X)`), and, for every kernel `K` not yet ordered before the host,
its **footprint** `F_K = (W_K, R_K)`: interval sets of the global addresses it wrote and the
ones it only read.

1. **Kernel end** (`K` has run; its dump holds its accesses): build `F_K`. Check it against
   every retained copy/set/kernel `X` with `¬(X hb K)` (issued earlier, not ordered before
   `K`): an overlap with a conflicting access kind is a race. Retain `F_K`.
2. **Copy/set issue** `M`: check `M`'s ranges against every retained footprint `F_K` with
   `¬(K hb M)`. Retain `M`.
3. **Any host wait**: drop every retained operation that is now ordered before the host
   (`C_H[stream(X)] ≥ n(X)`) — it is ordered before everything issued later.

Both directions are needed. The two shipped cuHadron tests issue the copy *after* the kernel
(`memcpy_htod_kernel_race`: kernel on stream 2, then the H2D copy on stream 1;
`kernel_memcpy_dtoh_race`: kernel on stream 1, then the D2H copy on stream 2), which only
step 2 can see; the brief's first sketch (an interval set of *earlier* copies checked
inside the kernel) covers step 1 only.

Cost: the footprint is an interval set; coalesced and strided-but-complete access patterns
collapse into few intervals, scattered ones do not (bounded by the number of distinct
addresses). Retention lasts until the next host wait that covers the kernel; a program that
never synchronizes retains every footprint (then one merged footprint per stream would do,
at the price of kernel identity in reports — not needed for the prototype).

Kernel vs kernel on two streams is the same test with two footprints (step 1 with `X` a
kernel); the `interkernel/*` cuHadron cases need nothing else.

## 5. Where it runs

The per-kernel `HbEngine` resets at every launch and knows nothing of other kernels, and
steps 2 and 3 happen between kernels, so the check is program-level either way. The
prototype therefore splits it:

* **Collector + tool (behind `YOSEMITE_HB_HOST_MEMCPY=1`, additive):** the collector forwards
  the stream of every launch, copy and set, enables the Sanitizer's `EVENTS` domain (record,
  stream wait, event synchronize), and forwards stream creation flags and synchronize
  callbacks; `PcDependency` appends every host operation, in API order, to a program-level
  `host_ops.json` in the dump directory, each launch carrying its `kernel_N` index.
* **Analysis (Python, both modes):** `python/host_hb.py` replays `host_ops.json` with each
  kernel's footprint taken from its `hb_events` (global-space lanes and sizes) and returns
  the races; the harness adds them to the program's reports. Nothing in `sync_dominance.py`
  changes (a copy has no pc), and nothing in `HbEngine` / `hb_oracle.py` changes, so the
  engine = oracle invariant is untouched.

An online variant inside the engine (footprints from the end-of-kernel `last_write` /
`last_reads` maps, as the brief suggested) would avoid parsing `hb_events` offline. It is
worth building only once `hb_events` stop being dumped (T4); until then it would be a second
implementation of the same check and would need its own parity test.

## 6. Assumptions and known gaps

* A1 one host thread issues all CUDA calls (several host threads: each is an agent, and API
  calls from different threads are unordered unless the host program orders them — not
  modelled).
* A2 polling (`cudaStreamQuery` / `cudaEventQuery` spun until done) orders the host in reality
  but raises no Sanitizer synchronize callback: such programs get false reports. Unverified
  whether the Sanitizer reports a successful query.
* A3 per-thread default stream (`--default-stream per-thread`), CUDA graphs, host callbacks
  (`cudaLaunchHostFunc`), stream priorities, multiple devices and peer copies, managed
  memory migration and `cudaMemPrefetchAsync`: not modelled.
* A4 the observed schedule plays no part: under the tool every launch is serialized (the
  collector drains the kernel's buffer before `LAUNCH_END` returns), so every run *looks*
  ordered; the verdict is the API-level order above, i.e. a race is reported whether or not
  the two operations overlapped in this run.
* A5 accesses are known per lane start address and size; a copy range is exact.
