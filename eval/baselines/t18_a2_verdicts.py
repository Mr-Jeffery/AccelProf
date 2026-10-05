import json,glob,sys
sys.path.insert(0,'/home/fzheng4/wt-t18/python')
import sync_dominance as sd
for late in ('0','atomic'):
  for prog in ('race_interblock_none-lock_rtraw','norace_interblock_lock_waw'):
    d=f'/mnt/beegfs/fzheng4/t18-green/LATE={late}/{prog}'
    dots=sorted(glob.glob(d+'/**/*.dot',recursive=True)); trs=sorted(glob.glob(d+'/dependency_*/kernel_*.json'))
    if not trs: print(late,prog,'missing'); continue
    tr=trs[-1]; t=json.load(open(tr))
    for dot in dots:
        try: rep=sd.analyze(dot,tr); break
        except sd.AlignmentError: pass
    print(f'LATE={late} {prog}: hb_events={len(t["hb_events"])} hb_late_seq={t.get("hb_late_seq")}')
    for v in rep['verdicts']:
        if v['verdict']!='ORDERED': print('   ',v['race_type'],v['verdict'],v['hb_class'],'a2=',v['a2_uncertain'])
    for r in t['hb_races']: print('    rec',r['kind'],r.get('class'),f"a2 {r.get('a2_uncertain')}/count {r.get('count')}")
