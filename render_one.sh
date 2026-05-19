#!/bin/bash
# Usage: ./render_one.sh 01_baseline.qmd
QMD=${1:-00_data_loading.qmd}

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
    bash -c "cd /workspace && quarto render $QMD --to html"