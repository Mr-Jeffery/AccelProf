// CPU access-logging oracle shim for the IndigoSuite 1.3 CUDA codes (eval/baselines/oracle_pi).
// Stands in for include/indigo_cuda.h: same main() protocol (graph, init values, launch
// geometry), but test_kernel runs on the CPU, one fiber per GPU thread, and every access to
// a data_t object is logged. The source is compiled UNMODIFIED on disk; the driver pipes it
// through sed to turn `typedef int data_t;` into the logging type L below.
// Reports whether two different threads make unordered conflicting accesses (>=1 write, not
// both atomic) to one location. Ordered = same block and a __syncthreads barrier between
// them, or same warp and a warp collective between them.
#include <ucontext.h>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <vector>
#include <map>
#include <algorithm>
#include <random>

struct Dim { int x, y, z; };
struct Fiber {
  ucontext_t ctx; char* stack; Dim t, b; int gid; bool done = false;
  int wait = 0;            // 0 none, 1 block barrier, 2 warp collective
  int coll_kind = 0; long coll_val = 0; int coll_arg = 0; long coll_res = 0;
  int bphase = 0, wphase = 0;
};
static Fiber* cur = nullptr;
static ucontext_t sched_ctx;
static Dim g_blockDim, g_gridDim;
#define threadIdx (cur->t)
#define blockIdx (cur->b)
#define blockDim g_blockDim
#define gridDim g_gridDim
#define __global__
#define __device__
#define __host__
#define __noinline__
#define __inline__ inline
#define __shared__ static

struct Acc { int gid, block, warp, bphase, wphase; char kind; /* R W A(atomic rmw/write) a(atomic read) */ };
struct Key { int arr; long idx; int block; bool operator<(const Key& o) const {
  return arr != o.arr ? arr < o.arr : idx != o.idx ? idx < o.idx : block < o.block; } };
static std::map<Key, std::vector<Acc>> LOG;
static const void *R1b, *R1e, *R2b, *R2e;
static std::vector<std::pair<char*, char*>> STACKS;
static bool g_atomic = false;

static void logacc(const void* p, char kind) {
  if (!cur) return;
  Key k;
  if (p >= R1b && p < R1e) k = {1, (long)((const int*)p - (const int*)R1b), -1};
  else if (p >= R2b && p < R2e) k = {2, (long)((const int*)p - (const int*)R2b), -1};
  else {
    for (auto& s : STACKS) if ((const char*)p >= s.first && (const char*)p < s.second) return;  // thread-private local
    k = {3, (long)(uintptr_t)p, cur->b.x};        // __shared__ (static storage here): per block
  }
  if (g_atomic) kind = (kind == 'R') ? 'a' : 'A';
  LOG[k].push_back({cur->gid, cur->b.x, cur->t.x / 32, cur->bphase, cur->wphase, kind});
}

struct L;
static std::map<std::pair<const void*, int>, int> SHV;   // value of a __shared__ slot per block
static bool is_shared(const void* p) {
  if (!cur) return false;
  if ((p >= R1b && p < R1e) || (p >= R2b && p < R2e)) return false;
  for (auto& s : STACKS) if ((const char*)p >= s.first && (const char*)p < s.second) return false;
  return true;
}
struct L {   // logging int
  int v;
  int get() const { return is_shared(this) ? SHV[{this, cur->b.x}] : v; }
  void set(int x) { if (is_shared(this)) SHV[{this, cur->b.x}] = x; else v = x; }
  L() : v(0) {}
  L(int x) : v(x) {}
  L(const L& o) : v((int)o) {}
  operator int() const { logacc(this, 'R'); return get(); }
  L& operator=(int x) { logacc(this, 'W'); set(x); return *this; }
  L& operator=(const L& o) { int t = o; return *this = t; }
  L& operator+=(int x) { int t = *this; return *this = t + x; }
  L& operator-=(int x) { int t = *this; return *this = t - x; }
  L& operator|=(int x) { int t = *this; return *this = t | x; }
  L& operator&=(int x) { int t = *this; return *this = t & x; }
  L& operator++() { return *this += 1; }
  int operator++(int) { int t = *this; *this = t + 1; return t; }
  L& operator--() { return *this -= 1; }
  int operator--(int) { int t = *this; *this = t - 1; return t; }
};
static inline int max(int a, int b) { return a > b ? a : b; }
static inline int min(int a, int b) { return a < b ? a : b; }

struct AtomG { AtomG() { g_atomic = true; } ~AtomG() { g_atomic = false; } };
// atomicRead/atomicWrite: the two path_compression codes define their own on top of atomicOr/atomicExch
static inline int atomicMax(L* p, int v) { AtomG g; int o = *p; *p = o > v ? o : v; return o; }
static inline int atomicMin(L* p, int v) { AtomG g; int o = *p; *p = o < v ? o : v; return o; }
static inline int atomicAdd(L* p, int v) { AtomG g; int o = *p; *p = o + v; return o; }
static inline int atomicOr(L* p, int v) { AtomG g; int o = *p; *p = o | v; return o; }
static inline int atomicExch(L* p, int v) { AtomG g; int o = *p; *p = v; return o; }

static void yield_wait(int w) { cur->wait = w; Fiber* f = cur; swapcontext(&f->ctx, &sched_ctx); }
static inline void __syncthreads() { cur->coll_kind = 0; yield_wait(1); }
enum { C_XOR = 1, C_UP, C_ANY, C_BALLOT, C_SOR, C_SCOUNT };
static long coll(int kind, long val, int arg, int w) {
  cur->coll_kind = kind; cur->coll_val = val; cur->coll_arg = arg; yield_wait(w); return cur->coll_res; }
static inline int __shfl_xor_sync(unsigned, int val, int d) { return (int)coll(C_XOR, val, d, 2); }
static inline int __shfl_up_sync(unsigned, int val, int d) { return (int)coll(C_UP, val, d, 2); }
static inline bool __any_sync(unsigned, bool p) { return coll(C_ANY, p, 0, 2) != 0; }
static inline unsigned __ballot_sync(unsigned, bool p) { return (unsigned)coll(C_BALLOT, p, 0, 2); }
static inline bool __syncthreads_or(bool p) { return coll(C_SOR, p, 0, 1) != 0; }
static inline int __syncthreads_count(bool p) { return (int)coll(C_SCOUNT, p, 0, 1); }
static inline int __popc(unsigned x) { return __builtin_popcount(x); }

struct ECLgraph { int nodes, edges; int* nindex; int* nlist; };
static ECLgraph readECLgraph(const char* fname) {
  ECLgraph g; FILE* f = fopen(fname, "rb"); if (!f) { fprintf(stderr, "ERROR: open %s\n", fname); exit(-1); }
  if (fread(&g.nodes, 4, 1, f) != 1 || fread(&g.edges, 4, 1, f) != 1) exit(-1);
  g.nindex = (int*)malloc((g.nodes + 1) * 4); g.nlist = (int*)malloc((g.edges > 0 ? g.edges : 1) * 4);
  if (fread(g.nindex, 4, g.nodes + 1, f) != (size_t)g.nodes + 1) exit(-1);
  if (fread(g.nlist, 4, g.edges, f) != (size_t)g.edges) exit(-1);
  fclose(f); return g;
}

typedef L data_t;
void test_kernel(int* nindex, int* nlist, L* data1, L* data2, int n);

struct KArgs { int* ni; int* nl; L* d1; L* d2; int n; };
static KArgs KA;
static void tramp() { test_kernel(KA.ni, KA.nl, KA.d1, KA.d2, KA.n); cur->done = true; cur->wait = 0;
  Fiber* f = cur; swapcontext(&f->ctx, &sched_ctx); }

static const char* kname(char k) { return k == 'R' ? "read" : k == 'W' ? "write" : k == 'A' ? "atomic-write" : "atomic-read"; }

int main(int argc, char* argv[]) {
  if (argc < 4) { fprintf(stderr, "USAGE: %s graph threads_per_block num_blocks [schedule_seed]\n", argv[0]); return 2; }
  ECLgraph g = readECLgraph(argv[1]);
  int tpb = atoi(argv[2]), nb = atoi(argv[3]); long seed = argc > 4 ? atol(argv[4]) : 0;
  int n = g.nodes, e = g.edges ? g.edges : 1, s = n > e ? n : e;
  L* data1 = new L[s]; L* data2 = new L[s];
  data1[0].v = 0; data2[0].v = 0;                      // same init protocol as indigo_cuda.h
  int* h1 = (int*)malloc(s * 4);
  for (int i = 1; i < s; i++) { data1[i].v = rand() % n; h1[i] = data1[i].v; }
  for (int i = 1; i < s; i++) data2[i].v = rand() % e;
  R1b = data1; R1e = data1 + s; R2b = data2; R2e = data2 + s;
  g_blockDim = {tpb, 1, 1}; g_gridDim = {nb, 1, 1};
  // threads of blocks >= max(n,e) are inactive in every pattern (i >= numv): not emulated
  int eb = std::min(nb, std::max(n, e));
  std::vector<Fiber*> F;
  const size_t SS = 32 * 1024;
  for (int b = 0; b < eb; b++) for (int t = 0; t < tpb; t++) {
    Fiber* f = new Fiber; f->stack = (char*)malloc(SS); f->t = {t, 0, 0}; f->b = {b, 0, 0}; f->gid = b * tpb + t;
    getcontext(&f->ctx); f->ctx.uc_stack.ss_sp = f->stack; f->ctx.uc_stack.ss_size = SS; f->ctx.uc_link = &sched_ctx;
    makecontext(&f->ctx, tramp, 0); STACKS.push_back({f->stack, f->stack + SS}); F.push_back(f);
  }
  KA = {g.nindex, g.nlist, data1, data2, n};
  std::vector<int> order(F.size()); for (size_t i = 0; i < F.size(); i++) order[i] = (int)i;
  if (seed == 1) std::reverse(order.begin(), order.end());
  else if (seed > 1) { std::mt19937 rng((unsigned)seed); std::shuffle(order.begin(), order.end(), rng); }
  for (;;) {
    bool progressed = false;
    for (int oi : order) { Fiber* f = F[oi]; if (f->done || f->wait) continue;
      cur = f; swapcontext(&sched_ctx, &f->ctx); cur = nullptr; progressed = true; }
    // release warp collectives: every unfinished lane of the warp is waiting on one
    std::map<std::pair<int,int>, std::vector<Fiber*>> W; std::map<int, std::vector<Fiber*>> B;
    for (Fiber* f : F) { W[{f->b.x, f->t.x / 32}].push_back(f); B[f->b.x].push_back(f); }
    for (auto& kv : W) { auto& v = kv.second; bool all = true, any = false;
      for (Fiber* f : v) { if (f->done) continue; if (f->wait != 2) all = false; else any = true; }
      if (!all || !any) continue;
      long agg_any = 0, ballot = 0;
      for (Fiber* f : v) if (!f->done) { if (f->coll_val) { agg_any = 1; ballot |= 1L << (f->t.x % 32); } }
      for (Fiber* f : v) { if (f->done) continue; int lane = f->t.x % 32; long r = 0;
        if (f->coll_kind == C_XOR || f->coll_kind == C_UP) {
          int pl = f->coll_kind == C_XOR ? (lane ^ f->coll_arg) : (lane + f->coll_arg);
          r = 0; for (Fiber* p : v) if (!p->done && p->t.x % 32 == pl && pl < 32) r = p->coll_val;
        } else if (f->coll_kind == C_ANY) r = agg_any; else if (f->coll_kind == C_BALLOT) r = ballot;
        f->coll_res = r; }
      for (Fiber* f : v) if (!f->done) { f->wait = 0; f->wphase++; }
      progressed = true; }
    for (auto& kv : B) { auto& v = kv.second; bool all = true, any = false;
      for (Fiber* f : v) { if (f->done) continue; if (f->wait != 1) all = false; else any = true; }
      if (!all || !any) continue;
      long orv = 0, cnt = 0; for (Fiber* f : v) if (!f->done && f->coll_kind >= C_SOR && f->coll_val) { orv = 1; cnt++; }
      for (Fiber* f : v) if (!f->done) { f->coll_res = f->coll_kind == C_SCOUNT ? cnt : orv; f->coll_kind = 0; f->wait = 0; f->bphase++; f->wphase = 0; }
      progressed = true; }
    bool alldone = true; for (Fiber* f : F) if (!f->done) alldone = false;
    if (alldone) break;
    if (!progressed) { printf("ORACLE deadlock\n"); return 3; }
  }
  // conflicts
  long pairs = 0; std::string ex;
  for (auto& kv : LOG) { auto& v = kv.second;
    for (size_t a = 0; a < v.size(); a++) for (size_t b = a + 1; b < v.size(); b++) {
      const Acc &x = v[a], &y = v[b];
      if (x.gid == y.gid) continue;
      bool xw = x.kind == 'W' || x.kind == 'A', yw = y.kind == 'W' || y.kind == 'A';
      if (!xw && !yw) continue;
      bool xa = x.kind == 'A' || x.kind == 'a', ya = y.kind == 'A' || y.kind == 'a';
      if (xa && ya) continue;
      if (x.block == y.block && x.bphase != y.bphase) continue;
      if (x.block == y.block && x.warp == y.warp && x.wphase != y.wphase) continue;
      if (!pairs) { char buf[256]; snprintf(buf, sizeof buf, "%s[%ld] %s by thread %d (block %d) vs %s by thread %d (block %d)",
        kv.first.arr == 1 ? "data1" : kv.first.arr == 2 ? "data2" : "shared", kv.first.arr == 3 ? 0 : kv.first.idx,
        kname(x.kind), x.gid, x.block, kname(y.kind), y.gid, y.block); ex = buf; }
      pairs++; if (pairs > 1000000) goto out;
    } }
out:
  long touched = 0, writers = 0;
  for (auto& kv : LOG) { touched++; for (auto& a : kv.second) if (a.kind == 'W' || a.kind == 'A') { writers++; break; } }
  printf("ORACLE %s pairs=%ld locations=%ld written_locations=%ld emulated_threads=%zu %s\n",
         pairs ? "CONFLICT" : "NO-CONFLICT", pairs, touched, writers, F.size(), ex.c_str());
  return 0;
}
