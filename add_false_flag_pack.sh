#!/data/data/com.termux/files/usr/bin/sh
set -eu

run() {
  tag="$1"; case_name="$2"; query="$3"; prio="${4:-3}"
  sh ./safe_run.sh python3 watchlist_ctl.py add \
    --tag "$tag" \
    --query "$query" \
    --urlfilter "%" \
    --case "$case_name" \
    --priority "$prio" || true
}

# Core synonym block (no quotes to keep FTS happy)
BASE="(false flag OR staged OR psyop OR provocation OR agent provocateur OR manufactured OR engineered)"

# 1) Mass shootings
run "FF/Shooting" "False Flag / Shooting" \
"$BASE AND (shoot* OR firearm* OR gunman OR active shooter OR massacre)"

# 2) Bombings / explosions
run "FF/Bombing" "False Flag / Bombing" \
"$BASE AND (bomb* OR explosion OR IED OR blast)"

# 3) Stabbings / bladed attacks
run "FF/Stabbing" "False Flag / Stabbing" \
"$BASE AND (stab* OR knife OR machete)"

# 4) Aircraft crashes
run "FF/Aviation" "False Flag / Aviation" \
"$BASE AND (plane OR flight OR airliner OR aircraft OR crash OR downed)"

# 5) Train derailments
run "FF/Rail" "False Flag / Rail" \
"$BASE AND (derail* OR train OR rail)"

# 6) Chemical / bio / hazmat
run "FF/ChemBio" "False Flag / Chem-Bio" \
"$BASE AND (chemical OR hazmat OR toxic OR biolab OR pathogen)"

# 7) Energy / infrastructure (pipeline, refinery, grid)
run "FF/Infra" "False Flag / Infrastructure" \
"$BASE AND (pipeline OR refinery OR substation OR grid OR blackout OR power outage OR transformer)"

# 8) Cyber / comms outages
run "FF/Cyber" "False Flag / Cyber-Outage" \
"$BASE AND (cyber* OR ransomware OR DDoS OR outage OR internet OR cellular OR blackout)"

# 9) Assassinations / VIP attacks
run "FF/Assassination" "False Flag / Assassination" \
"$BASE AND (assassin* OR attempt* OR plot OR gunman OR sniper)"

# 10) Riots / unrest / provocation at protests
run "FF/Unrest" "False Flag / Unrest" \
"$BASE AND (riot* OR unrest OR protest* OR demonstration* OR crowd OR clash* OR agitator)"

# (Optional) Generic catch-all – broad but noisy
run "FF/Generic" "False Flag / Generic" \
"$BASE AND (attack OR incident OR operation OR event OR terror OR emergency)" 2

echo "[ok] false-flag watchlist pack added"
