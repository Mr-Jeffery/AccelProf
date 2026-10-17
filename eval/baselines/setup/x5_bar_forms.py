"""X5: what the dots of the X1 store contain that the CFG binning relies on.

  * the BAR* / WARPSYNC instruction forms (opcode, operand shapes) -- whether any BAR carries a
    count operand;
  * where EXIT / RET sit in their basic block (barrier_ordered_bins' region graph assumes a
    predicated EXIT ends its block, as nvdisasm writes it: the `exit0` port).
Plain python3, regex over the dot text; run on a compute node (BeeGFS)."""
import collections
import glob
import re
import sys

STORE = sys.argv[1] if len(sys.argv) > 1 else "/mnt/beegfs/fzheng4/cuvein_traces/final-2026-10"
BS_SP = "\\ "
forms = collections.Counter()
files = withbar = 0
insn = re.compile(r"[0-9a-f]{4}:\\ \\ \\ ((?:@!?U?P[T0-9]+\\ )?)((?:BAR|WARPSYNC|BARRIER)[A-Za-z._0-9]*)([^;]*);")
node = re.compile(r'\[label="\{(.*?)\}"\]', re.S)
ins_in_block = re.compile(r"[0-9a-f]{4}:\\ \\ \\ ((?:@!?U?P[T0-9]+\\ )?)([A-Z][A-Z0-9._]*)")
exits = collections.Counter()
seen = set()
for f in glob.glob(f"{STORE}/*/dots/*.dot"):
    t = open(f, errors="replace").read()
    if t in seen:                                  # the same cubin dot is stored once per program
        continue
    seen.add(t)
    files += 1
    hit = False
    for m in insn.finditer(t):
        pred, op, rest = m.groups()
        rest = rest.replace(BS_SP, " ").strip()
        ops = [o.strip() for o in rest.split(",")] if rest else []
        shape = []
        for o in ops:
            if re.fullmatch(r"0x0+|0", o):
                shape.append("imm0")
            elif re.fullmatch(r"0x[0-9a-f]+|\d+", o):
                shape.append("immN")
            elif re.fullmatch(r"!?P[T0-9]+", o):
                shape.append("pred")
            elif re.fullmatch(r"U?R\d+(\.\w+)?|RZ|URZ", o):
                shape.append("reg")
            else:
                shape.append("other:" + o)
        forms[(("pred@" if pred else "") + op, tuple(shape))] += 1
        hit = True
    withbar += hit
    for nm in node.finditer(t):
        body = nm.group(1)
        insns = ins_in_block.findall(body)
        for i, (pred, op) in enumerate(insns):
            if op.split(".")[0] in ("EXIT", "RET"):
                exits[("guarded" if pred else "plain", "last" if i == len(insns) - 1 else "NOT last")] += 1
print(f"distinct dot files {files}, with BAR/WARPSYNC {withbar}")
for k, n in sorted(forms.items(), key=lambda x: -x[1]):
    print(n, k)
print("EXIT/RET placement (guarded/plain, position in the basic block):")
for k, n in sorted(exits.items()):
    print(n, k)
