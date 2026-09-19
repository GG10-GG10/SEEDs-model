#!/bin/bash
set -euo pipefail

TOTAL_BATCHES=100
SAMPLES_PER_LEVEL=2000
RESUME=1
WORKDIR="/lustre/home/2606194130/Food/Code/bin/new"
PYTHON_SCRIPT="S5_1_1_sensitivity_mc_variable_effect_batches.py"
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

for i in $(seq 1 "$TOTAL_BATCHES"); do
  job_name="ve${i}"
  script_name="sbatch_S5_1_1_variable_effect_${i}.sh"

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
export VAREFFECT_BATCH_ENABLED=1
export VAREFFECT_BATCH_INDEX=${i}
export VAREFFECT_TOTAL_BATCHES=${TOTAL_BATCHES}
export VAREFFECT_SAMPLES_PER_LEVEL=${SAMPLES_PER_LEVEL}
export VAREFFECT_RESUME=${RESUME}

cd ${WORKDIR}
echo "Running S5_1_1 batch \${VAREFFECT_BATCH_INDEX}/\${VAREFFECT_TOTAL_BATCHES} resume=\${VAREFFECT_RESUME} on \$(hostname) at \$(date)"
python ${PYTHON_SCRIPT}
echo "Finished batch \${VAREFFECT_BATCH_INDEX} at \$(date)"
EOF

  chmod +x "$script_name"
  echo "[GEN] ${script_name}"
done

for i in $(seq 1 "$TOTAL_BATCHES"); do
  script_name="sbatch_S5_1_1_variable_effect_${i}.sh"
  job_id=""
  echo "[SUBMIT] ${script_name}"
  job_id=$(sbatch --parsable "$script_name")
  echo "[JOB] ${script_name} -> ${job_id}"
done

echo "[DONE] Generated and submitted ${TOTAL_BATCHES} S5_1_1 variable-effect batch jobs."
echo "[NOTE] Merge is not submitted by this script."
echo "[NOTE] Run merge manually after all batches finish:"
echo "       python S5_1_3_merge_variable_effect_batches.py --total-batches ${TOTAL_BATCHES}"
