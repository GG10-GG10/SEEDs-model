#!/bin/bash
set -euo pipefail

TOTAL_BATCHES=10
TOTAL_SAMPLES=2000
WORKDIR="/lustre/home/2606194130/Food/Code/bin/new"
PYTHON_SCRIPT="S5_0_1_sensitivity_mc_levels_batches.py"
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
  job_name="mcl${i}"
  script_name="sbatch_S5_0_mclevels_${i}.sh"

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
export MCLEVELS_BATCH_ENABLED=1
export MCLEVELS_BATCH_INDEX=${i}
export MCLEVELS_TOTAL_BATCHES=${TOTAL_BATCHES}
export MCLEVELS_SAMPLES=${TOTAL_SAMPLES}

cd ${WORKDIR}
echo "Running S5_0 batch \${MCLEVELS_BATCH_INDEX}/\${MCLEVELS_TOTAL_BATCHES} on \$(hostname) at \$(date)"
python ${PYTHON_SCRIPT}
echo "Finished batch \${MCLEVELS_BATCH_INDEX} at \$(date)"
EOF

  chmod +x "$script_name"
  echo "[GEN] ${script_name}"
done

for i in $(seq 1 "$TOTAL_BATCHES"); do
  script_name="sbatch_S5_0_mclevels_${i}.sh"
  job_id=""
  echo "[SUBMIT] ${script_name}"
  job_id=$(sbatch --parsable "$script_name")
  echo "[JOB] ${script_name} -> ${job_id}"
done

echo "[DONE] Generated and submitted ${TOTAL_BATCHES} S5_0 batch jobs."
echo "[NOTE] Merge is not submitted by this script."
echo "[NOTE] Run merge manually after all batches finish:"
echo "       python S5_0_2_merge_sensitivity_mc_levels_batches.py"
