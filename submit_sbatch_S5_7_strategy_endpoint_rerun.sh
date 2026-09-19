#!/bin/bash
set -euo pipefail

# S5.7 Strategy endpoint rerun batch submission.
# This script only submits batch jobs. Merge manually after all batches finish:
# python S5_7_2_strategy_endpoint_rerun_merge_batches.py --total-batches ${TOTAL_BATCHES} --shapley

# Shapley with the current 9-strategy package runs 512 model evaluations including baseline.
TOTAL_BATCHES=32
# Set START_BATCH to the first interrupted/failed batch when resuming.
START_BATCH=1

RUN_SHAPLEY=1
SHAPLEY_KEEP_STANDARD=0
SHAPLEY_MAX_STRATEGIES=12

DRY_RUN=0
RESUME=1
CLEAR_EXISTING_RUNS=0
WRITE_SUMMARY_OUTPUTS=0

WORKDIR="/lustre/home/2606194130/Food/Code/bin/new"
PYTHON_SCRIPT="S5_7_1_strategy_endpoint_rerun_max_reduction_potential_batches.py"
CONDA_ENV="gurobi_env"
PARTITION="C064M1024G"
QOS="normal"
TIME_LIMIT="120:00:00"
CPUS_PER_TASK=3
LOG_DIR="./log"
LICENSE_FILE="/lustre/home/2606194130/1.tools/licenses/gurobi.lic"

# Optional root output override. Empty means the script default:
# <NZF_OUTPUT_DIR>/Strategy_Endpoint_Max_Reduction_Potential
OUTPUT_DIR=""

# Batch scenario-plan assignment: round_robin | contiguous
BATCH_ASSIGNMENT="round_robin"

# Optional diagnostics / limits.
STOP_ON_ERROR=0
THREADS=""

# Country scenarios are off by default for S5.7 Strategy potential.
COUNTRY_RUNS=0
COUNTRY_INDIVIDUAL_LEVERS=0
COUNTRIES=""
MAX_COUNTRIES=""
DETAILED_COUNTRY_ACCOUNTING=0

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
  job_name="s57_${i}"
  script_name="sbatch_s57_strategy_endpoint_${i}.sh"

  cat > "$script_name" <<EOF
#!/bin/bash
#SBATCH --job-name=${job_name}
#SBATCH --output=${LOG_DIR}/log_%x_%j.out
#SBATCH --error=${LOG_DIR}/log_%x_%j.err
#SBATCH --partition=${PARTITION}
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=${CPUS_PER_TASK}
#SBATCH --qos=${QOS}
#SBATCH --time=${TIME_LIMIT}

source ~/.bashrc
conda activate ${CONDA_ENV}
export GRB_LICENSE_FILE=${LICENSE_FILE}
export S57_BATCH_INDEX=${i}
export S57_TOTAL_BATCHES=${TOTAL_BATCHES}
export S57_BATCH_ASSIGNMENT=${BATCH_ASSIGNMENT}
export S57_SHAPLEY=${RUN_SHAPLEY}
export S57_SHAPLEY_KEEP_STANDARD=${SHAPLEY_KEEP_STANDARD}
export S57_SHAPLEY_MAX_STRATEGIES=${SHAPLEY_MAX_STRATEGIES}
export S57_DRY_RUN=${DRY_RUN}
export S57_RESUME=${RESUME}
export S57_CLEAR_EXISTING_RUNS=${CLEAR_EXISTING_RUNS}
export S57_WRITE_SUMMARY_OUTPUTS=${WRITE_SUMMARY_OUTPUTS}
export S57_STOP_ON_ERROR=${STOP_ON_ERROR}
export S57_COUNTRY_RUNS=${COUNTRY_RUNS}
export S57_COUNTRY_INDIVIDUAL_LEVERS=${COUNTRY_INDIVIDUAL_LEVERS}
export S57_DETAILED_COUNTRY_ACCOUNTING=${DETAILED_COUNTRY_ACCOUNTING}
EOF

  if [[ -n "${OUTPUT_DIR}" ]]; then
    echo "export S57_OUTPUT_DIR=${OUTPUT_DIR}" >> "$script_name"
  fi
  if [[ -n "${THREADS}" ]]; then
    echo "export S57_THREADS=${THREADS}" >> "$script_name"
  fi
  if [[ -n "${COUNTRIES}" ]]; then
    echo "export S57_COUNTRIES=${COUNTRIES}" >> "$script_name"
  fi
  if [[ -n "${MAX_COUNTRIES}" ]]; then
    echo "export S57_MAX_COUNTRIES=${MAX_COUNTRIES}" >> "$script_name"
  fi

  cat >> "$script_name" <<EOF

cd ${WORKDIR}
echo "Running S5.7 batch \${S57_BATCH_INDEX}/\${S57_TOTAL_BATCHES} shapley=\${S57_SHAPLEY} resume=\${S57_RESUME} clear_existing_runs=\${S57_CLEAR_EXISTING_RUNS} on \$(hostname) at \$(date)"
python ${PYTHON_SCRIPT}

echo "Finished S5.7 batch \${S57_BATCH_INDEX} at \$(date)"
EOF

  chmod +x "$script_name"
  echo "[GEN] ${script_name}"
done

for i in $(seq "$START_BATCH" "$TOTAL_BATCHES"); do
  script_name="sbatch_s57_strategy_endpoint_${i}.sh"
  echo "[SUBMIT] ${script_name}"
  sbatch "$script_name"
done

echo "[DONE] Generated and submitted S5.7 Strategy endpoint rerun batch jobs ${START_BATCH}..${TOTAL_BATCHES} of ${TOTAL_BATCHES}."
echo "[NOTE] Merge is not submitted by this script."
echo "[NOTE] Run merge manually after all batches finish:"
if [[ "${RUN_SHAPLEY}" == "1" ]]; then
  if [[ -n "${OUTPUT_DIR}" ]]; then
    echo "       python S5_7_2_strategy_endpoint_rerun_merge_batches.py --out-dir \"${OUTPUT_DIR}\" --total-batches ${TOTAL_BATCHES} --shapley"
  else
    echo "       python S5_7_2_strategy_endpoint_rerun_merge_batches.py --total-batches ${TOTAL_BATCHES} --shapley"
  fi
else
  if [[ -n "${OUTPUT_DIR}" ]]; then
    echo "       python S5_7_2_strategy_endpoint_rerun_merge_batches.py --out-dir \"${OUTPUT_DIR}\" --total-batches ${TOTAL_BATCHES}"
  else
    echo "       python S5_7_2_strategy_endpoint_rerun_merge_batches.py --total-batches ${TOTAL_BATCHES}"
  fi
fi
