# Sourced by the p_*.sh scripts (T-H, Phase 3): abort when home usage is above HOME_QUOTA_MAX_GB
# (default 35 of the 40 GB quota). If `quota` is unavailable the guard warns and continues.
_hq_gb=$(quota -s 2>/dev/null | awk '/\/home/ || /:\/home/ {print $2; exit}' | awk '
  /[0-9]+G$/ {sub(/G/,""); print $1; next}
  /[0-9]+M$/ {sub(/M/,""); print $1/1024; next}
  /[0-9]+T$/ {sub(/T/,""); print $1*1024; next}
  /^[0-9]+$/ {print $1/1048576}')
if [ -z "$_hq_gb" ]; then
  echo "home_quota_guard: could not read 'quota -s'; continuing" >&2
elif awk -v u="$_hq_gb" -v m="${HOME_QUOTA_MAX_GB:-35}" 'BEGIN{exit !(u>m)}'; then
  echo "home_quota_guard: home usage ${_hq_gb} GB > ${HOME_QUOTA_MAX_GB:-35} GB; aborting (see eval/HOME_CLEANUP.md)" >&2
  exit 1
fi
unset _hq_gb
