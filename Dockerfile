# Stage 1 — build de l'environnement
FROM condaforge/mambaforge:latest AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    gcc g++ libgdal-dev && \
    rm -rf /var/lib/apt/lists/*

RUN mamba create -n segtraq -c conda-forge \
    python=3.11 \
    numpy h5py rasterio gdal shapely geopandas \
    igraph \
    python-igraph leidenalg \
    && mamba clean -afy \
    && find /opt/conda/envs/segtraq -name "*.pyc" -delete \
    && find /opt/conda/envs/segtraq -name "__pycache__" -type d -exec rm -rf {} + \
    && rm -rf /opt/conda/pkgs/*

RUN /opt/conda/envs/segtraq/bin/pip install --no-cache-dir segtraq ipykernel nbformat nbclient spatialdata-io

# Stage 2 — image finale minimale
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Paris

# uniquement les libs système nécessaires à l'exécution
RUN apt-get update && apt-get install -y \
    libgdal32 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installe Quarto dans le conteneur (Debian bookworm = glibc récente)
RUN curl -LO https://github.com/quarto-dev/quarto-cli/releases/download/v1.6.40/quarto-1.6.40-linux-amd64.tar.gz && \
    tar -xzf quarto-1.6.40-linux-amd64.tar.gz -C /opt/ && \
    rm quarto-1.6.40-linux-amd64.tar.gz

# on copie uniquement l'environnement conda, pas mambaforge entier
COPY --from=builder /opt/conda/envs/segtraq /opt/conda/envs/segtraq

# Pre-compile numba/cython caches while /opt/conda is still writable
RUN /opt/conda/envs/segtraq/bin/python -c "import datashader; import xrspatial; import numba; import squidpy; import scanpy; import skimage; import rasterio; print('All caches compiled OK')"

ENV PATH="/opt/quarto-1.6.40/bin:/opt/conda/envs/segtraq/bin:$PATH"

WORKDIR /workspace