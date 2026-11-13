#!/usr/bin/env python3
"""TOOLS_ON_STREAMK, vector clock: follow one producer store -> consumer load instance of the dossier's pair through the
vector-clock replay of a dump (python/hb_oracle.py, the specification HbClock is checked against; NOT modified: the file is
read, a hook call is inserted at the top of its event loop in an in-memory copy, and the copy is exec'd as a new module).

  1. the unmodified oracle on the dump: its races / races_sync_only on <a_pc, b_pc> (agreement with the dump's HbClock keys)
  2. instance: the first load at b_pc whose 16-byte granule was last written at a_pc by a thread of ANOTHER block, both
     threads outside warp 0 (else the first such load at all) -> producer thread P (store), consumer thread L (load);
     P0 / C0 = thread 0 of the producer / consumer block (the thread that runs the flag RMWs)
  3. replay with the hook: after every event, vc[x][P] and vs[x][P] (barrier-only clock) for x in {P, P0, C0, L} and every
     released[loc] clock's P component; logged: the store, every barrier / syncwarp record of the two blocks, every warp-0
     atomic record of the two blocks, any event after which one of these first holds P's store epoch (repeats folded);
     at L's load the comparison vc[L][P] vs e (the state the load's Check reads)
  4. the gate table rows (fenced() on the release / acquire side) of the flag RMW pcs
usage: x9_tools_vc_trace.py <python dir> <cfg.dot> <kernel_0.json> <a_pc> <b_pc>"""
import json, sys, types
PYD, DOT, TR, A_PC, B_PC = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4], 0), int(sys.argv[5], 0)
sys.path.insert(0, PYD)
import hb_oracle as ORIG
tid = ORIG.tid_of
def who(t): return f"b{t >> 10}.w{(t >> 5) & 31}.l{t & 31}"

# --- 1. the unmodified oracle
trace = json.load(open(TR))
rep = ORIG.analyze(DOT, TR)
on = [r for r in rep["races"] if (r["a_pc"], r["b_pc"]) == (A_PC, B_PC)]
so = [x for x in rep["races_sync_only"] if (x[0], x[1]) == (min(A_PC, B_PC), max(A_PC, B_PC))]
dump_on = [r for r in (trace.get("hb_races") or []) if (r.get("a_pc"), r.get("b_pc")) == (A_PC, B_PC)]
dump_so = [x for x in (trace.get("hb_races_sync_only") or []) if (x[0], x[1]) == (min(A_PC, B_PC), max(A_PC, B_PC))]
print(f"ORACLE gate={rep['gate']} policy={rep['gate_policy']} races_total={len(rep['races'])} on_pair={[(r['class'], r['count']) for r in on]} "
      f"sync_only_on_pair={so} | DUMP(HbClock) hb_races_total={len(trace.get('hb_races') or [])} on_pair={[(r.get('class'), r.get('count')) for r in dump_on]} "
      f"sync_only_on_pair={dump_so}")
atom = {int(k, 16) for k in rep["atomic_pcs"]}
print("ATOMIC_PCS", len(atom), sorted(hex(x) for x in atom)[:6], "... chain", rep["chain"])

# --- 2. the instance
ev = sorted(trace["hb_events"], key=lambda e: e["seq"])
last_w = {}; inst = None; inst0 = None; shape = {}
for e in ev:
    if e.get("space") != "global" or "lanes" not in e: continue
    if e["pc"] in (A_PC, B_PC) and e["pc"] not in shape:
        shape[e["pc"]] = dict({k: v for k, v in e.items() if k != "lanes"}, lane0=e["lanes"][0])
    for ln in e["lanes"]:
        t = tid(e["block"], e["warp"], ln["lane"]); ch = ln["addr"] & ~15
        if e["pc"] == A_PC: last_w[ch] = (t, e["seq"], ln["addr"])
        elif e["pc"] == B_PC and ch in last_w and (last_w[ch][0] >> 10) != e["block"]:
            c = dict(addr=ln["addr"], store_addr=last_w[ch][2], P=last_w[ch][0], store_seq=last_w[ch][1], L=t, load_seq=e["seq"])
            if inst0 is None: inst0 = c
            if inst is None and (c["P"] >> 5) & 31 and (t >> 5) & 31: inst = c
    if inst: break
print("SHAPE", {hex(k): v for k, v in shape.items()})
inst = inst or inst0
if not inst: print("NO cross-block instance on the pair"); sys.exit(0)
P, L = inst["P"], inst["L"]; P0, C0 = tid(P >> 10, 0, 0), tid(L >> 10, 0, 0)
print(f"INSTANCE store addr={hex(inst['store_addr'])} seq {inst['store_seq']} by P={who(P)} | load addr={hex(inst['addr'])} seq {inst['load_seq']} "
      f"by L={who(L)} | P0={who(P0)} C0={who(C0)}")

# --- 3. replay with the hook
src = open(ORIG.__file__).read()
assert src.count("    for e in events:\n") == 1
src = src.replace("    for e in events:\n", "    for e in events:\n        _TRACE_HOOK(e, vc, vs, released)\n")
assert src.count("    for t in sorted(wins):") == 1
src = src.replace("    for t in sorted(wins):", "    _TRACE_HOOK(None, vc, vs, released)\n    for t in sorted(wins):")
M = types.ModuleType("hb_oracle_traced"); M.__file__ = ORIG.__file__
S = dict(prev=None, e=None, known={}, rel_known=set(), last=None, rep=0, lastseq=None)
TRK = {"P": P, "P0": P0, "C0": C0, "L": L}
def snap(vc, vs):
    return " ".join(f"{n}:vc={vc[x].get(P, 0)}/vs={vs[x].get(P, 0)}" for n, x in TRK.items())
def emit(seq, body):
    if body == S["last"]:
        S["rep"] += 1
    else:
        if S["rep"]: print(f"           ... the line above repeated {S['rep']} more times (to seq {S['lastseq']})")
        S["rep"] = 0; print(f"  seq {seq:>6} {body}")
    S["last"], S["lastseq"] = body, seq
def hook(e, vc, vs, released):
    p = S["prev"]
    if p is not None:
        if S["e"] is None and p["seq"] == inst["store_seq"]:
            S["e"] = vc[P].get(P, 0)
            emit(p["seq"], f"   STORE pc={hex(p['pc'])} by {who(P)}: e = vc[P][P] = {S['e']} | {snap(vc, vs)}")
        elif S["e"] is not None:
            E = S["e"]; why = []
            for n, x in TRK.items():
                k = vc[x].get(P, 0) >= E
                if k and not S["known"].get(n): why.append(f"{n} now holds P>={E}")
                S["known"][n] = k
            for loc, rel in released.items():
                if rel[0] is not None and rel[0].get(P, 0) >= E and loc not in S["rel_known"]:
                    S["rel_known"].add(loc); why.append(f"released[{loc[0]}:{hex(loc[1]) if isinstance(loc[1], int) else loc[1]}] now holds P={rel[0].get(P, 0)}")
            inb = p.get("block") in (P >> 10, L >> 10)
            if (inb and (p.get("type") in ("barrier", "syncwarp") or (p.get("warp") == 0 and p.get("pc") in atom))) or why:
                rels = {hex(l[1]) if isinstance(l[1], int) else str(l): r[0].get(P, 0) for l, r in released.items()
                        if r[0] is not None and r[0].get(P, 0)}
                emit(p["seq"], f"{p.get('type'):>8} pc={hex(p['pc'])} b{p.get('block')}.w{p.get('warp')} mask={p.get('active_mask', 0):#x}"
                     f"{' ATOMIC' if p.get('pc') in atom else ''}{(' bar' + str(p.get('bar_index'))) if p.get('type') == 'barrier' else ''}"
                     f" | {snap(vc, vs)} | released P>0: {rels}{' | ' + '; '.join(why) if why else ''}")
    if e is not None and e["seq"] == inst["load_seq"]:
        E = S["e"]; S["last"] = None
        if S["rep"]: print(f"           ... the line above repeated {S['rep']} more times (to seq {S['lastseq']})"); S["rep"] = 0
        print(f"  seq {e['seq']:>6}     LOAD pc={hex(e['pc'])} by {who(L)} (state the load's Check reads): vc[L][P]={vc[L].get(P, 0)} "
              f"vs[L][P]={vs[L].get(P, 0)}, store epoch e={E} -> vector clock holds the store: {vc[L].get(P, 0) >= E}; "
              f"barrier-only clock holds it: {vs[L].get(P, 0) >= E}")
        S["done"] = True
    S["prev"] = e if not S.get("done") else None
M._TRACE_HOOK = hook
exec(compile(src, ORIG.__file__ + "<traced>", "exec"), M.__dict__)
M.analyze(DOT, TR)
if S["rep"]: print(f"           ... the line above repeated {S['rep']} more times (to seq {S['lastseq']})")

# --- 4. the gate table rows of the flag RMW pcs (the CAS spin of wait_eq_reset, the RED of arrive_inc)
sd = M.sd
gr = sd.HBGraph(*sd.parse_dot(DOT)[sd.select_kernel(sd.parse_dot(DOT), trace["kernel"]["kernel_name"])])
g = gr.gate_table()
flag_pcs = sorted({x["pc"] for x in ev if x.get("pc") in atom and x.get("block") in (P >> 10, L >> 10) and x.get("warp") == 0
                   and x.get("active_mask") == 1})
for pc in flag_pcs:
    print(f"GATE {hex(pc)} {gr.pc_opcode.get(pc)}: {repr(g.get(pc))[:700]}")
