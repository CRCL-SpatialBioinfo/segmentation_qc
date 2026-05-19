#!/bin/bash
#SBATCH --job-name=segtraq-qc
#SBATCH --cpus-per-task=30
#SBATCH --mem=200G
#SBATCH --time=48:00:00
#SBATCH --output=logs/qc_%j.out
#SBATCH --error=logs/qc_%j.err

mkdir -p logs
singularity exec \
    --bind ~/dev/segmentation_qc:/workspace \
    --bind /data:/data \
    --bind ~/singularity-cache/runtime:/run/user/$(id -u) \
    --bind ~/singularity-cache/quarto:/home/tonon/.cache/quarto \
    --bind ~/singularity-cache/deno:/home/tonon/.cache/deno \
    --bind ~/singularity-cache/quarto-logs:/home/tonon/.local/share/quarto \
    --env JUPYTER_PATH=/opt/conda/envs/segtraq/share/jupyter \
    --env JUPYTER_DATA_DIR=/opt/conda/envs/segtraq/share/jupyter \
    /home/tonon/softs/sifs/segtraq.sif \
    bash -c "cd /workspace && quarto render"