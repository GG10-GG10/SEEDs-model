#!/bin/bash
set -euo pipefail

TOTAL_BATCHES=200
# Full rerun mode: submit every batch from scratch and clear old batch outputs first.
START_BATCH=1
FULL_RERUN=1
RESUME=0
CLEAR_EXISTING_RUNS=1
SKIP_COMPLETED_BATCHES=0
CLEAR_BATCH_OUTPUT_DIRS_BEFORE_SUBMIT=1
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="${WORKDIR:-${SCRIPT_DIR}}"
PYTHON_SCRIPT="S5_3_1_sensitivity_panel_yield_ef_batches.py"
CONDA_ENV="gurobi_env"
PARTITION="C064M1024G"
QOS="normal"
TIME_LIMIT="120:00:00"
CPUS_PER_TASK=6
LOG_DIR="./log"
LICENSE_FILE="/lustre/home/2606194130/1.tools/licenses/gurobi.lic"
BATCHES_SUBDIR="batches"
PROJECT_ROOT="$(cd "${WORKDIR}/../.." && pwd)"
CONFIG_OUTPUT_BASE="$(cd "${WORKDIR}" && python - <<'PY'
from config_paths import get_results_base
print(get_results_base())
PY
)"
if [[ -n "${NZF_OUTPUT_DIR:-}" && "${NZF_OUTPUT_DIR}" != /* ]]; then
  echo "[ERROR] NZF_OUTPUT_DIR must be an absolute path, got: ${NZF_OUTPUT_DIR}"
  exit 1
fi
if [[ -n "${PANEL_OUTPUT_DIR:-}" && "${PANEL_OUTPUT_DIR}" != /* ]]; then
  echo "[ERROR] PANEL_OUTPUT_DIR must be an absolute path, got: ${PANEL_OUTPUT_DIR}"
  exit 1
fi
if [[ -n "${PANEL_OUTPUT_DIR:-}" ]]; then
  OUTPUT_DIR_ROOT="${PANEL_OUTPUT_DIR}"
  OUTPUT_BASE="$(dirname "${OUTPUT_DIR_ROOT}")"
else
  OUTPUT_BASE="${NZF_OUTPUT_DIR:-${CONFIG_OUTPUT_BASE}}"
  OUTPUT_DIR_ROOT="${OUTPUT_BASE}/Panel_Yield_EF"
fi
RESULTS_CSV="figure_panel_dataset_long.csv"
SUBMIT_BATCHES=()

clear_batch_dir_if_requested() {
  local batch_tag="$1"
  local batch_dir="${OUTPUT_DIR_ROOT}/${BATCHES_SUBDIR}/${batch_tag}"
  if (( CLEAR_BATCH_OUTPUT_DIRS_BEFORE_SUBMIT != 1 )); then
    return 0
  fi
  if (( FULL_RERUN != 1 )); then
    echo "[ERROR] Refusing to clear batch dir unless FULL_RERUN=1"
    exit 1
  fi
  if [[ "${OUTPUT_DIR_ROOT}" != /* || -z "${batch_tag}" || "${batch_tag}" != batch_*_of_* ]]; then
    echo "[ERROR] Unsafe batch cleanup target: OUTPUT_DIR_ROOT=${OUTPUT_DIR_ROOT}, batch_tag=${batch_tag}"
    exit 1
  fi
  case "${batch_dir}" in
    "${OUTPUT_DIR_ROOT}/${BATCHES_SUBDIR}/${batch_tag}") ;;
    *)
      echo "[ERROR] Refusing to clear unexpected batch dir: ${batch_dir}"
      exit 1
      ;;
  esac
  if [[ -d "${batch_dir}" ]]; then
    echo "[FULL-RERUN] removing old batch output dir: ${batch_dir}"
    rm -rf -- "${batch_dir}"
  fi
}

if ! command -v sbatch >/dev/null 2>&1; then
  echo "[ERROR] sbatch not found in PATH"
  exit 1
fi
if (( FULL_RERUN == 1 )) && command -v squeue >/dev/null 2>&1; then
  active_panel_jobs=$(squeue -h -u "${USER}" -o "%j" | grep -E '^pnl[0-9]+$' || true)
  if [[ -n "${active_panel_jobs}" ]]; then
    echo "[ERROR] Active S5_3 panel jobs are still in queue; cancel or wait before full rerun:"
    echo "${active_panel_jobs}"
    echo "        Use: squeue -u ${USER} -o \"%.18i %.20j %.8T\""
    echo "        Then cancel the old pnl* job IDs with: scancel <job_id...>"
    exit 1
  fi
fi

cd "$WORKDIR"
mkdir -p "$LOG_DIR"
if (( FULL_RERUN == 1 )); then
  mkdir -p "${OUTPUT_DIR_ROOT}"
  for old_file in \
    "${RESULTS_CSV}" \
    "figure_panel_global_emissions_detail_long.csv" \
    "figure_panel_dataset_long_rebuilt.csv" \
    "figure_panel_dataset_long_plot_ready.csv" \
    "figure_panel_global_emissions_detail_long_rebuilt.csv" \
    "figure_panel_missing_points_audit.csv" \
    "figure_panel_data_summary.csv" \
    "batch_completion_audit.csv" \
    "run_meta.csv"; do
    if [[ -f "${OUTPUT_DIR_ROOT}/${old_file}" ]]; then
      echo "[FULL-RERUN] removing old root output: ${OUTPUT_DIR_ROOT}/${old_file}"
      rm -f -- "${OUTPUT_DIR_ROOT}/${old_file}"
    fi
  done
fi

if (( START_BATCH < 1 || START_BATCH > TOTAL_BATCHES )); then
  echo "[ERROR] START_BATCH must be within 1..${TOTAL_BATCHES}, got ${START_BATCH}"
  exit 1
fi

for i in $(seq "$START_BATCH" "$TOTAL_BATCHES"); do
  printf -v batch_tag "batch_%02d_of_%02d" "$i" "$TOTAL_BATCHES"
  if (( SKIP_COMPLETED_BATCHES == 1 )); then
    meta_path="${OUTPUT_DIR_ROOT}/${BATCHES_SUBDIR}/${batch_tag}/run_meta.csv"
    results_path="${OUTPUT_DIR_ROOT}/${BATCHES_SUBDIR}/${batch_tag}/${RESULTS_CSV}"
    if [[ -f "$meta_path" && -f "$results_path" ]]; then
      echo "[SKIP] batch ${i} already completed (run_meta and results found: ${meta_path})"
      continue
    fi
  fi
  clear_batch_dir_if_requested "${batch_tag}"

  job_name="pnl${i}"
  script_name="sbatch_S5_3_1_panel_${i}.sh"

  SUBMIT_BATCHES+=("$i")

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
export PANEL_BATCH_ENABLED=1
export PANEL_BATCH_INDEX=${i}
export PANEL_TOTAL_BATCHES=${TOTAL_BATCHES}
export NZF_OUTPUT_DIR="${OUTPUT_BASE}"
export PANEL_OUTPUT_DIR="${OUTPUT_DIR_ROOT}"
export PANEL_RESUME=${RESUME}
export PANEL_CLEAR_EXISTING_RUNS=${CLEAR_EXISTING_RUNS}

cd "${WORKDIR}"
echo "Running S5_3_1 batch \${PANEL_BATCH_INDEX}/\${PANEL_TOTAL_BATCHES} resume=\${PANEL_RESUME} clear_existing_runs=\${PANEL_CLEAR_EXISTING_RUNS} on \$(hostname) at \$(date)"
echo "NZF_OUTPUT_DIR=\${NZF_OUTPUT_DIR}"
echo "PANEL_OUTPUT_DIR=\${PANEL_OUTPUT_DIR}"
python ${PYTHON_SCRIPT} --batch-index "\${PANEL_BATCH_INDEX}" --total-batches "\${PANEL_TOTAL_BATCHES}" --output-dir "\${PANEL_OUTPUT_DIR}" --no-resume --clear-existing-runs
echo "Finished batch \${PANEL_BATCH_INDEX} at \$(date)"
EOF

  chmod +x "$script_name"
  echo "[GEN] ${script_name}"
done

if (( ${#SUBMIT_BATCHES[@]} == 0 )); then
  echo "[DONE] No batches to submit (all completed or skipped)."
  exit 0
fi

for i in "${SUBMIT_BATCHES[@]}"; do
  script_name="sbatch_S5_3_1_panel_${i}.sh"
  job_id=""
  echo "[SUBMIT] ${script_name}"
  job_id=$(sbatch --parsable "$script_name")
  echo "[JOB] ${script_name} -> ${job_id}"
done

echo "[DONE] Generated and submitted S5_3_1 panel batch jobs: ${SUBMIT_BATCHES[*]}"
echo "[NOTE] FULL_RERUN=${FULL_RERUN}; PANEL_RESUME=${RESUME}; PANEL_CLEAR_EXISTING_RUNS=${CLEAR_EXISTING_RUNS}."
echo "[NOTE] SKIP_COMPLETED_BATCHES=${SKIP_COMPLETED_BATCHES}; CLEAR_BATCH_OUTPUT_DIRS_BEFORE_SUBMIT=${CLEAR_BATCH_OUTPUT_DIRS_BEFORE_SUBMIT}."
echo "[NOTE] Merge is not submitted by this script."
echo "[NOTE] Run merge manually after all batches finish:"
echo "       python S5_3_3_merge_panel_yield_ef_batches.py --output-dir \"${OUTPUT_DIR_ROOT}\" --total-batches ${TOTAL_BATCHES}"
echo "[NOTE] Then rebuild plot-ready data:"
echo "       python S5_3_2_panel_data_summary.py --output-dir \"${OUTPUT_DIR_ROOT}\""
