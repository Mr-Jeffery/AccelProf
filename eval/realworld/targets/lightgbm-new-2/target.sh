# lightgbm-new-2: EvalKernel<CUDA_METRIC, USE_WEIGHTS=true> -> ShuffleReduceSum<double> shared_mem_buffer reuse (cuda_pointwise_metric.cu L31/L39) (R1, T21c candidate).
# Pinned (buggy) c8be3579413199a6e0f769e74c15ee119735471c; no fix commit, only the buggy variant is built.  ONE CUDA build serves lightgbm-new-1 and -new-2: this
# target does not recompile, t_build copies the `lightgbm` CLI binary and the gcc-12.4 runtime libs from $RW/build/lightgbm-new-1/buggy (build lightgbm-new-1 first; its
# build-info.txt and status.json describe the build) and generates its own data.  The `lineinfo` phase is therefore not supported here (it would re-run this copy):
# the lineinfo check of the LightGBM build lives in lightgbm-new-1/lineinfo.check.
# Driver: the `lightgbm` CLI, 1,000-row training set, weighted 5,000-row validation set (valid.tsv + valid.tsv.weight, picked up by the CLI automatically), metric = l2,
# device_type=cuda, 3 gbdt iterations -> EvalKernel<l2, true> <<<5, 1024>>> once per iteration on the validation scores (blocks 0-3 full).
T_ROUTE=R1; T_KERNEL=EvalKernel; T_SPACE=shared; T_EXE=lightgbm; T_ARTIFACTS="lightgbm libstdc++.so.6 libgcc_s.so.1 libgomp.so.1 train.tsv valid.tsv valid.tsv.weight train.conf"
t_export() {   # login node: identical tarball to lightgbm-new-1 (same revision), copied
  local src=$INCOMING/export/lightgbm-new-1/buggy.tar.gz
  [ -s "$src" ] || { echo "run: rw.sh lightgbm-new-1 export first" >&2; return 1; }
  cp "$src" "$3"
}
t_build() {    # cwd = $OUT (node-local)
  local b=$RW/build/lightgbm-new-1/buggy
  [ -n "$RW_LINEINFO" ] || { echo "lightgbm-new-2 shares lightgbm-new-1's build; run the lineinfo phase on lightgbm-new-1" >&2; return 1; }
  for f in lightgbm libstdc++.so.6 libgcc_s.so.1 libgomp.so.1; do cp -a "$b/$f" . || return 1; done
  python3 "$TDIR/gen_data.py" . || return 1
  cat > train.conf <<CONF
task = train
boosting = gbdt
objective = regression
metric = l2
device_type = cuda
data = $ART/train.tsv
valid_data = $ART/valid.tsv
max_bin = 255
num_leaves = 15
num_iterations = 3
learning_rate = 0.1
min_data_in_leaf = 20
num_threads = 4
verbosity = 1
seed = 1
CONF
}
t_cmd() { echo "$ART/lightgbm config=$ART/train.conf output_model=model.txt"; }
