# X15 prep (login node, once): harness copies in /home/fzheng4/x15rw/t21c (archive of study/realworld-candidates eval/realworld + eval/baselines)
HX=/home/fzheng4/x15rw/t21c; HD=$HX/eval/realworld/harness
# C6's rw_attribute.py / rw_score.py (eval/co-offline, rw_t21c, C4's RW_MODES edit), taken from the repo
git -C /home/fzheng4/wt-c6b show origin/eval/co-offline:eval/baselines/setup/co_offline/rw_t21c/rw_attribute.py > $HD/rw_attribute_sc.py || exit 1
git -C /home/fzheng4/wt-c6b show origin/eval/co-offline:eval/baselines/setup/co_offline/rw_t21c/rw_score.py > $HD/rw_score.py || exit 1
# S2 copy: C6's two edits (c6_rw_setup.sh) plus the S2 switches of C6b (co_async=True, co_r3="off") on the same call
cp $HD/rw_attribute_sc.py $HD/rw_attribute_s2.py
sed -i 's/rep = sd.analyze(dot, kj)/rep = sd.analyze(dot, kj, chain_closure=True, co_async=True, co_r3="off")/' $HD/rw_attribute_s2.py
sed -i 's/model_bug=kk in mbug,/model_bug=kk in mbug, chain_src=("chain" if v.get("chain") else ("chain_rescue" if v.get("chain_rescue") else "edge")), chain_path=v.get("chain_path"),/' $HD/rw_attribute_s2.py
echo "s2 edits applied: $(grep -c 'chain_closure=True, co_async=True, co_r3="off"' $HD/rw_attribute_s2.py) $(grep -c chain_src $HD/rw_attribute_s2.py)"
diff $HD/rw_attribute_sc.py $HD/rw_attribute_s2.py | cut -c1-200
