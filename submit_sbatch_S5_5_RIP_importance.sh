#!/bin/bash
set -euo pipefail

TOTAL_BATCHES=200
SAMPLES=20000
# Set START_BATCH to the first interrupted/failed batch when resuming.
START_BATCH=1
RESUME=0
# Batch jobs only run MC by default. Aggregation across all batches is done
# manually afterward by S5_5_3_Region-Item-Process_Importance_merge_batches.py.
POSTPROCESS=0
WORKDIR="/lustre/home/2606194130/Food/Code/bin/new"
PYTHON_SCRIPT="S5_5_2_Region-Item-Process_Importance_Gen_batches.py"
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
  job_name="rip${i}"
  script_name="sbatch_S5_5_rip_${i}.sh"

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
export RIPMC_BATCH_INDEX=${i}
export RIPMC_TOTAL_BATCHES=${TOTAL_BATCHES}
export RIPMC_SAMPLES=${SAMPLES}
export RIPMC_RESUME=${RESUME}
export RIPMC_POSTPROCESS=${POSTPROCESS}

cd ${WORKDIR}
echo "Running S5_5 batch \${RIPMC_BATCH_INDEX}/\${RIPMC_TOTAL_BATCHES} samples=\${RIPMC_SAMPLES} resume=\${RIPMC_RESUME} postprocess=\${RIPMC_POSTPROCESS} on \$(hostname) at \$(date)"
python ${PYTHON_SCRIPT}
echo "Finished S5_5 batch \${RIPMC_BATCH_INDEX} at \$(date)"
EOF

  chmod +x "$script_name"
  echo "[GEN] ${script_name}"
done

for i in $(seq "$START_BATCH" "$TOTAL_BATCHES"); do
  script_name="sbatch_S5_5_rip_${i}.sh"
  job_id=""
  echo "[SUBMIT] ${script_name}"
  job_id=$(sbatch --parsable "$script_name")
  echo "[JOB] ${script_name} -> ${job_id}"
done

echo "[DONE] Generated and submitted S5_5 Region/Item/Process batch jobs ${START_BATCH}..${TOTAL_BATCHES} of ${TOTAL_BATCHES}."
echo "[NOTE] Merge is not submitted by this script."
echo "[NOTE] Batch POSTPROCESS=${POSTPROCESS}. Set POSTPROCESS=1 only if per-batch structure tables are needed."
echo "[NOTE] Run aggregate extraction manually after all batches finish:"
echo "       python S5_5_3_Region-Item-Process_Importance_merge_batches.py"
