# rtx4060ti8g nodes carry a 4060 Ti (sm_89) AND a 2080 SUPER (sm_75): expose only the sm_89 one
export CUDA_VISIBLE_DEVICES=$(nvidia-smi --query-gpu=uuid,compute_cap --format=csv,noheader | awk -F', ' '$2=="8.9"{print $1; exit}')
