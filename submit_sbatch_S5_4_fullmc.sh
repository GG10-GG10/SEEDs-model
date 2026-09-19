#!/bin/bash
set -euo pipefail

TOTAL_BATCHES=200
# Set START_BATCH to the first interrupted/failed batch when resuming.
START_BATCH=1
RESUME=0
CLEAR_EXISTING_RUNS=1
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="${WORKDIR:-${SCRIPT_DIR}}"
PYTHON_SCRIPT="S5_4_1_monte_carlo_full_variables_batches.py"
CONDA_ENV="gurobi_env"
PARTITION="C064M1024G"
QOS="normal"
TIME_LIMIT="120:00:00"
CPUS_PER_TASK=4
LOG_DIR="./log"
LICENSE_FILE="/lustre/home/2606194130/1.tools/licenses/gurobi.lic"

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
  job_name="f${i}"
  script_name="sbatch_fullmc_${i}.sh"

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
export FULLMC_BATCH_ENABLED=1
export FULLMC_BATCH_INDEX=${i}
export FULLMC_TOTAL_BATCHES=${TOTAL_BATCHES}
export FULLMC_RESUME=${RESUME}
export FULLMC_CLEAR_EXISTING_RUNS=${CLEAR_EXISTING_RUNS}
export FULLMC_REQUIRE_EF_CO2EQ_INTENSITY=1
# Optional, use this if the CFG['base_case']/Emis path is not visible on the server:
# export FULLMC_EF_INTENSITY_BASELINE_EMISSIONS_CSV=/path/to/emissions_summary_By_Country_Process_Item.csv

cd ${WORKDIR}
echo "Running batch \${FULLMC_BATCH_INDEX}/\${FULLMC_TOTAL_BATCHES} resume=\${FULLMC_RESUME} clear_existing_runs=\${FULLMC_CLEAR_EXISTING_RUNS} on \$(hostname) at \$(date)"
python ${PYTHON_SCRIPT}

echo "Finished at \$(date)"
EOF

  chmod +x "$script_name"
  echo "[GEN] ${script_name}"
done

for i in $(seq "$START_BATCH" "$TOTAL_BATCHES"); do
  script_name="sbatch_fullmc_${i}.sh"
  echo "[SUBMIT] ${script_name}"
  sbatch "$script_name"
done

echo "[DONE] Generated and submitted full-MC batch jobs ${START_BATCH}..${TOTAL_BATCHES} of ${TOTAL_BATCHES}."
echo "[NOTE] Merge is not submitted by this script."
echo "[NOTE] Run merge manually after all batches finish:"
echo "       python S5_4_2_merge_batches.py --total-batches ${TOTAL_BATCHES} --strict"
