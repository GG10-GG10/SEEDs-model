#!/bin/bash
set -euo pipefail

# S5.8 country-local intervention grid for Figure 3d.
# With 190 countries and nine interventions, the unique grid contains 1,710
# model scenarios. Each isolated batch also runs one matched reference.

TOTAL_BATCHES=32
START_BATCH=1
SUBMIT_MERGE=1

RESUME=1
CLEAR_EXISTING_RUNS=0
STOP_ON_ERROR=1
BATCH_ASSIGNMENT="round_robin"
MAX_COUNTRIES=""
COUNTRIES=""

WORKDIR="/lustre/home/2606194130/Food/Code/bin/new"
OUTPUT_ROOT="/lustre/home/2606194130/Food/Code/output/Country_Dominant_Mitigation_Intervention"
BATCH_SCRIPT="S5_8_1_country_strategy_map_sensitivity_batches.py"
MERGE_SCRIPT="S5_8_2_country_strategy_map_merge_batches.py"
PREP_SCRIPT="S5_8_3_prepare_country_dominant_mitigation_intervention.py"

CONDA_ENV="gurobi_env"
PARTITION="C064M1024G"
QOS="normal"
TIME_LIMIT="120:00:00"
CPUS_PER_TASK=3
LICENSE_FILE="/lustre/home/2606194130/1.tools/licenses/gurobi.lic"

case "$OUTPUT_ROOT" in
  */Code/output/*) ;;
  *)
    echo "[S5_8_SUBMIT][ERROR] OUTPUT_ROOT must be a child of Code/output: $OUTPUT_ROOT"
    exit 1
    ;;
esac

if ! command -v sbatch >/dev/null 2>&1; then
  echo "[S5_8_SUBMIT][ERROR] sbatch not found in PATH"
  exit 1
fi
if (( TOTAL_BATCHES < 1 || TOTAL_BATCHES > 190 )); then
  echo "[S5_8_SUBMIT][ERROR] TOTAL_BATCHES must be within 1..190"
  exit 1
fi
if (( START_BATCH < 1 || START_BATCH > TOTAL_BATCHES )); then
  echo "[S5_8_SUBMIT][ERROR] START_BATCH must be within 1..${TOTAL_BATCHES}"
  exit 1
fi

SCHEDULER_DIR="${OUTPUT_ROOT}/scheduler"
LOG_DIR="${SCHEDULER_DIR}/logs"
SCRIPT_DIR="${SCHEDULER_DIR}/scripts"
mkdir -p "$LOG_DIR" "$SCRIPT_DIR"

JOB_IDS=()
for i in $(seq "$START_BATCH" "$TOTAL_BATCHES"); do
  tag=$(printf "batch_%02d_of_%02d" "$i" "$TOTAL_BATCHES")
  job_script="${SCRIPT_DIR}/sbatch_s58_${tag}.sh"
  cat > "$job_script" <<EOF
#!/bin/bash
#SBATCH --job-name=s58_${i}
#SBATCH --output=${LOG_DIR}/log_%x_%j.out
#SBATCH --error=${LOG_DIR}/log_%x_%j.err
#SBATCH --partition=${PARTITION}
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=${CPUS_PER_TASK}
#SBATCH --qos=${QOS}
#SBATCH --time=${TIME_LIMIT}

set -euo pipefail
source ~/.bashrc
conda activate ${CONDA_ENV}
export GRB_LICENSE_FILE="${LICENSE_FILE}"
export S58_BATCH_INDEX="${i}"
export S58_TOTAL_BATCHES="${TOTAL_BATCHES}"
export S58_BATCH_ASSIGNMENT="${BATCH_ASSIGNMENT}"
export S58_OUTPUT_DIR="${OUTPUT_ROOT}"
export S58_RESUME="${RESUME}"
export S58_CLEAR_EXISTING_RUNS="${CLEAR_EXISTING_RUNS}"
export S58_STOP_ON_ERROR="${STOP_ON_ERROR}"
export S58_THREADS="${CPUS_PER_TASK}"
export S58_MAX_COUNTRIES="${MAX_COUNTRIES}"
export S58_COUNTRIES="${COUNTRIES}"

cd "${WORKDIR}"
python -B "${BATCH_SCRIPT}"
EOF
  chmod +x "$job_script"
  job_id=$(sbatch --parsable "$job_script")
  job_id="${job_id%%;*}"
  JOB_IDS+=("$job_id")
  echo "[S5_8_SUBMIT] submitted ${tag}: ${job_id}"
done

dependency=$(IFS=:; echo "${JOB_IDS[*]}")
merge_script="${SCRIPT_DIR}/sbatch_s58_merge_and_plot.sh"
cat > "$merge_script" <<EOF
#!/bin/bash
#SBATCH --job-name=s58_merge
#SBATCH --output=${LOG_DIR}/log_%x_%j.out
#SBATCH --error=${LOG_DIR}/log_%x_%j.err
#SBATCH --partition=${PARTITION}
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=${CPUS_PER_TASK}
#SBATCH --qos=${QOS}
#SBATCH --time=12:00:00

set -euo pipefail
source ~/.bashrc
conda activate ${CONDA_ENV}
export GRB_LICENSE_FILE="${LICENSE_FILE}"
cd "${WORKDIR}"
python -B "${MERGE_SCRIPT}" \
  --output-dir "${OUTPUT_ROOT}" \
  --total-batches "${TOTAL_BATCHES}" \
  --strict
python -B "${PREP_SCRIPT}" \
  --input-dir "${OUTPUT_ROOT}/merged" \
  --output-dir "${OUTPUT_ROOT}/merged/figure3d" \
  --metric domestic \
  --strict \
  --plot
EOF
chmod +x "$merge_script"

if [[ "$SUBMIT_MERGE" == "1" ]]; then
  merge_job_id=$(sbatch --parsable --dependency="afterok:${dependency}" "$merge_script")
  merge_job_id="${merge_job_id%%;*}"
  echo "[S5_8_SUBMIT] merge/plot job ${merge_job_id} depends on ${dependency}"
else
  echo "[S5_8_SUBMIT] merge/plot script generated but not submitted: ${merge_script}"
fi

echo "[S5_8_SUBMIT] all scheduler files are under ${SCHEDULER_DIR}"
