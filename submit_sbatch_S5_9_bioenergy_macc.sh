#!/bin/bash
set -euo pipefail

# S5.9 bioenergy-scenario marginal-abatement-cost batch submission and merge.
# Exact mode has 512 unique plans per panel. Because every isolated batch
# carries its own matched BASE, 32 batches execute (512 + 31) * 3 = 1629
# model evaluations. Quick mode is normally run with TOTAL_BATCHES=3 and
# executes (11 + 2) * 3 = 39 evaluations.

MODE="exact"                 # quick | exact
TOTAL_BATCHES=32             # recommended: quick=3, exact=32
START_BATCH=1                # first interrupted/missing batch when resuming
SUBMIT_MERGE=1               # 1: submit afterok merge job; 0: merge manually

DRY_RUN=0
RESUME=1
CLEAR_EXISTING_RUNS=0
STOP_ON_ERROR=1
BATCH_ASSIGNMENT="round_robin"  # round_robin | contiguous
CASES="low,medium,high"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="${WORKDIR:-${SCRIPT_DIR}}"
CODE_ROOT="$(cd "${WORKDIR}/../.." && pwd)"
OUTPUT_ROOT="${OUTPUT_ROOT:-${CODE_ROOT}/output/Bioenergy_Scenario_MACC_Exact_TS}"
BATCH_SCRIPT="S5_9_1_bioenergy_scenario_marginal_abatement_cost_curves_batches.py"
MERGE_SCRIPT="S5_9_2_bioenergy_scenario_marginal_abatement_cost_curves_merge_batches.py"

CONDA_ENV="gurobi_env"
PARTITION="C064M1024G"
QOS="normal"
TIME_LIMIT="120:00:00"
CPUS_PER_TASK=3
LICENSE_FILE="/lustre/home/2606194130/1.tools/licenses/gurobi.lic"

if ! command -v sbatch >/dev/null 2>&1; then
  echo "[S5_9_SUBMIT][ERROR] sbatch not found in PATH"
  exit 1
fi

case "$MODE" in
  quick) MAX_BATCHES=11 ;;
  exact) MAX_BATCHES=512 ;;
  *)
    echo "[S5_9_SUBMIT][ERROR] MODE must be quick or exact"
    exit 1
    ;;
esac

if [[ "$OUTPUT_ROOT" != /* ]]; then
  echo "[S5_9_SUBMIT][ERROR] OUTPUT_ROOT must be an absolute path"
  exit 1
fi
case "$OUTPUT_ROOT" in
  */Code/output/*) ;;
  *)
    echo "[S5_9_SUBMIT][ERROR] OUTPUT_ROOT must be a child of Code/output"
    exit 1
    ;;
esac
if (( TOTAL_BATCHES < 1 || TOTAL_BATCHES > MAX_BATCHES )); then
  echo "[S5_9_SUBMIT][ERROR] TOTAL_BATCHES must be within 1..${MAX_BATCHES} for ${MODE}"
  exit 1
fi
if (( START_BATCH < 1 || START_BATCH > TOTAL_BATCHES )); then
  echo "[S5_9_SUBMIT][ERROR] START_BATCH must be within 1..${TOTAL_BATCHES}"
  exit 1
fi
if (( DRY_RUN == 1 && SUBMIT_MERGE == 1 )); then
  echo "[S5_9_SUBMIT][WARN] disabling merge submission because DRY_RUN=1"
  SUBMIT_MERGE=0
fi

SCHEDULER_ROOT="${OUTPUT_ROOT}/scheduler"
LOG_DIR="${SCHEDULER_ROOT}/logs"
GENERATED_DIR="${SCHEDULER_ROOT}/scripts"
mkdir -p "$LOG_DIR" "$GENERATED_DIR"
cd "$WORKDIR"

bool_flag() {
  local enabled="$1"
  local positive="$2"
  local negative="$3"
  if [[ "$enabled" == "1" ]]; then
    printf '%s' "$positive"
  else
    printf '%s' "$negative"
  fi
}

DRY_FLAG=$(bool_flag "$DRY_RUN" "--dry-run" "--no-dry-run")
RESUME_FLAG=$(bool_flag "$RESUME" "--resume" "--no-resume")
CLEAR_FLAG=$(bool_flag "$CLEAR_EXISTING_RUNS" "--clear-existing-runs" "--no-clear-existing-runs")
STOP_FLAG=$(bool_flag "$STOP_ON_ERROR" "--stop-on-error" "--no-stop-on-error")

job_ids=()
for i in $(seq "$START_BATCH" "$TOTAL_BATCHES"); do
  tag=$(printf 'batch_%02d_of_%02d' "$i" "$TOTAL_BATCHES")
  job_name="s59_${MODE}_${i}"
  script_name="${GENERATED_DIR}/sbatch_s59_${MODE}_${tag}.sh"

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

set -euo pipefail
source ~/.bashrc
conda activate ${CONDA_ENV}
export GRB_LICENSE_FILE="${LICENSE_FILE}"
export NZF_OUTPUT_DIR="${OUTPUT_ROOT}"

cd "${WORKDIR}"
echo "Running S5.9 ${MODE} batch ${i}/${TOTAL_BATCHES} on \$(hostname) at \$(date)"
python "${BATCH_SCRIPT}" \
  --output-root "${OUTPUT_ROOT}" \
  --mode "${MODE}" \
  --cases "${CASES}" \
  --batch-index "${i}" \
  --total-batches "${TOTAL_BATCHES}" \
  --assignment "${BATCH_ASSIGNMENT}" \
  --threads "${CPUS_PER_TASK}" \
  ${DRY_FLAG} \
  ${RESUME_FLAG} \
  ${CLEAR_FLAG} \
  ${STOP_FLAG}
echo "Finished S5.9 batch ${i}/${TOTAL_BATCHES} at \$(date)"
EOF

  chmod +x "$script_name"
  echo "[S5_9_SUBMIT] generated ${script_name}"
  submitted=$(sbatch --parsable "$script_name")
  job_id=${submitted%%;*}
  job_ids+=("$job_id")
  echo "[S5_9_SUBMIT] submitted ${tag} as job ${job_id}"
done

merge_command=(
  python "$MERGE_SCRIPT"
  --output-root "$OUTPUT_ROOT"
  --mode "$MODE"
  --cases "$CASES"
  --total-batches "$TOTAL_BATCHES"
  --strict
  --input-audit
  --plot
)

if (( SUBMIT_MERGE == 1 )); then
  dependency=$(IFS=:; echo "${job_ids[*]}")
  merge_job="${GENERATED_DIR}/sbatch_s59_${MODE}_merge.sh"
  cat > "$merge_job" <<EOF
#!/bin/bash
#SBATCH --job-name=s59_${MODE}_merge
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
export NZF_OUTPUT_DIR="${OUTPUT_ROOT}"
cd "${WORKDIR}"
python "${MERGE_SCRIPT}" \
  --output-root "${OUTPUT_ROOT}" \
  --mode "${MODE}" \
  --cases "${CASES}" \
  --total-batches "${TOTAL_BATCHES}" \
  --strict \
  --input-audit \
  --plot
EOF
  chmod +x "$merge_job"
  merge_submit=$(sbatch --parsable --dependency="afterok:${dependency}" "$merge_job")
  echo "[S5_9_SUBMIT] merge job ${merge_submit%%;*} depends on ${dependency}"
else
  printf '[S5_9_SUBMIT] merge manually after every batch is complete:'
  printf ' %q' "${merge_command[@]}"
  printf '\n'
fi

echo "[S5_9_SUBMIT] all scheduler scripts and logs are under ${SCHEDULER_ROOT}"
