#!/bin/bash
set -euo pipefail

# S5.6 batch submission. This script only submits batch jobs.
# Run merge manually after all batches finish:
# python S5_6_2_merge_batches.py

TOTAL_BATCHES=10
# Set START_BATCH to the first interrupted/failed batch when resuming.
START_BATCH=1
RESUME=0
CLEAR_EXISTING_RUNS=1
WORKDIR="/lustre/home/2606194130/Food/Code/bin/new"
PYTHON_SCRIPT="S5_6_1_max_emission_reduction_potential_batches.py"
CONDA_ENV="gurobi_env"
PARTITION="C064M1024G"
QOS="normal"
TIME_LIMIT="120:00:00"
CPUS_PER_TASK=3
LOG_DIR="./log"
LICENSE_FILE="/lustre/home/2606194130/1.tools/licenses/gurobi.lic"

# Optional root output override. Empty means the script default:
# <NZF_OUTPUT_DIR>/Max_Emission_Reduction_Potential
OUTPUT_DIR=""

# Batch country assignment: round_robin | contiguous
BATCH_ASSIGNMENT="round_robin"

# Optional limits for smoke tests.
MAX_COUNTRIES=""
COUNTRIES=""

# Keep global single-lever diagnostics in batch_01.
GLOBAL_INDIVIDUAL_LEVERS=1
# Country single-lever diagnostics are expensive: 190 * 8 extra model runs.
COUNTRY_INDIVIDUAL_LEVERS=0
# Only batch_01 uses detailed country accounting for BASE vs global max.
DETAILED_COUNTRY_ACCOUNTING=1

if ! command -v sbatch >/dev/null 2>&1; then
  echo "[ERROR] sbatch not found in PATH"
  exit 1
fi

cd "$WORKDIR"
mkdir -p "$LOG_DIR"

if (( START_BATCH < 1 || START_BATCH > TOTAL_BATCHES )); then
  echo "[ERROR] START_BATCH must be within 1..${TOTAL_BATCHES}, got ${START_BATCH}"
  exit 1
fi

for i in $(seq "$START_BATCH" "$TOTAL_BATCHES"); do
  job_name="s56_${i}"
  script_name="sbatch_s56_maxred_${i}.sh"

  cat > "$script_name" <<EOF
# !/bin/bash
# SBATCH --job-name=${job_name}
# SBATCH --output=${LOG_DIR}/log_%x_%j.out
# SBATCH --error=${LOG_DIR}/log_%x_%j.err
# SBATCH --partition=${PARTITION}
# SBATCH --nodes=1
# SBATCH --ntasks-per-node=1
# SBATCH --cpus-per-task=${CPUS_PER_TASK}
# SBATCH --qos=${QOS}
# SBATCH --time=${TIME_LIMIT}

source ~/.bashrc
conda activate ${CONDA_ENV}
export GRB_LICENSE_FILE=${LICENSE_FILE}
export S56_BATCH_INDEX=${i}
export S56_TOTAL_BATCHES=${TOTAL_BATCHES}
export S56_BATCH_ASSIGNMENT=${BATCH_ASSIGNMENT}
export S56_RESUME=${RESUME}
export S56_CLEAR_EXISTING_RUNS=${CLEAR_EXISTING_RUNS}
export S56_GLOBAL_INDIVIDUAL_LEVERS=${GLOBAL_INDIVIDUAL_LEVERS}
export S56_COUNTRY_INDIVIDUAL_LEVERS=${COUNTRY_INDIVIDUAL_LEVERS}
export S56_DETAILED_COUNTRY_ACCOUNTING=${DETAILED_COUNTRY_ACCOUNTING}
EOF

  if [[ -n "${OUTPUT_DIR}" ]]; then
    echo "export S56_OUTPUT_DIR=${OUTPUT_DIR}" >> "$script_name"
  fi
  if [[ -n "${MAX_COUNTRIES}" ]]; then
    echo "export S56_MAX_COUNTRIES=${MAX_COUNTRIES}" >> "$script_name"
  fi
  if [[ -n "${COUNTRIES}" ]]; then
    echo "export S56_COUNTRIES=${COUNTRIES}" >> "$script_name"
  fi

  cat >> "$script_name" <<EOF

cd ${WORKDIR}
echo "Running S5.6 batch \${S56_BATCH_INDEX}/\${S56_TOTAL_BATCHES} resume=\${S56_RESUME} clear_existing_runs=\${S56_CLEAR_EXISTING_RUNS} on \$(hostname) at \$(date)"
python ${PYTHON_SCRIPT}

echo "Finished at \$(date)"
EOF

  chmod +x "$script_name"
  echo "[GEN] ${script_name}"
done

for i in $(seq "$START_BATCH" "$TOTAL_BATCHES"); do
  script_name="sbatch_s56_maxred_${i}.sh"
  echo "[SUBMIT] ${script_name}"
  sbatch "$script_name"
done

echo "[DONE] Generated and submitted S5.6 batch jobs ${START_BATCH}..${TOTAL_BATCHES} of ${TOTAL_BATCHES}."
echo "[NOTE] Merge is not submitted by this script."
echo "[NOTE] Run merge manually after all batches finish:"
echo "       python S5_6_2_merge_batches.py"
