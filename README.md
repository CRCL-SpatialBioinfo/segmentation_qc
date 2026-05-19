# Segmentation QC Report — Xenium

Quality control report for cell segmentation of 10x Genomics Xenium data,
comparing multiple segmentation methods using [SegTraQ](https://github.com/LazDaria/SegTraQ).

## Methods compared

| Method    | Description                              |
|-----------|------------------------------------------|
| Xenium    | Official 10x multi-modal segmentation   |
| Proseg v3 | Transcript assignment-based segmentation |

## Report structure

| Section | Description |
|---------|-------------|
| Data Loading | Raw data preprocessing and zarr export |
| Baseline | Cell counts, transcript and gene distributions |
| Morphology | Cell shape and size descriptors |
| Clustering | Clustering stability metrics |
| Volume (3D) | Z-distribution, top-bottom consistency, VSI |
| Contamination | Region similarity, border admixture score |
| Supervised | Label transfer metrics *(optional, requires scRNA-seq reference)* |
| Summary | Comparative table and radar chart |

## Requirements

### Environment

The analysis runs inside a [Singularity](https://sylabs.io/singularity/) container
built from a Docker image. The container includes:

- Python 3.11
- [SegTraQ](https://github.com/LazDaria/SegTraQ)
- spatialdata, spatialdata-io, scanpy, ovrlpy, rasterio, geopandas
- [Quarto](https://quarto.org/) 1.6.40

### Build the container

On a machine with Docker installed:

```bash
docker build -t segtraq-env .
docker save segtraq-env | gzip > segtraq-env.tar.gz
```

Transfer to the cluster and build the Singularity image:

```bash
scp segtraq-env.tar.gz user@cluster:/path/to/images/
sudo singularity build segtraq.sif docker-archive://segtraq-env.tar.gz
```

## Configuration

Edit `_params.yml` to set your data paths and parameters:

```yaml
# Raw data
xenium_path: "/path/to/xenium/output"
proseg_path: "/path/to/proseg_v3/output"

# Processed data (written by 00_data_loading.qmd)
processed_xenium_path: "/path/to/processed/xenium_processed.zarr"
processed_proseg_path: "/path/to/processed/proseg3_processed.zarr"

# scRNA-seq reference (optional)
has_reference: false
reference_path: null
cell_type_key: "celltype_major"

# QC parameters
min_qv: 20
min_transcripts: 10
min_genes: 5

# Methods
methods:
  - xenium
  - proseg_v3
```

### Optional: scRNA-seq reference

If a scRNA-seq reference is available, set `has_reference: true` and provide
`reference_path` to enable supervised metrics (label transfer, marker consistency,
cell type stratification).

## Running the report

### Setup cache directories (once)

```bash
mkdir -p ~/singularity-cache/{quarto,deno,quarto-logs,runtime}
```

### Interactive test (single section)

```bash
./render_one.sh 01_baseline.qmd
```

### Full report via SLURM

```bash
sbatch run_qc.sh
```

The HTML report is generated in `_output/`.

### Render locally (after cluster computation)

Once the cluster has computed and cached all results (`_freeze/`),
you can render the final report locally without rerunning the analysis:

```bash
# Sync from cluster
rsync -avz user@cluster:/path/to/segmentation-qc/ ~/segmentation-qc/

# Render locally (no recomputation)
quarto render --no-execute
```

## Project structure

```
segmentation-qc/
├── Dockerfile                  # Docker image definition
├── _quarto.yml                 # Quarto website configuration
├── _params.yml                 # Analysis parameters (edit this)
├── run_qc.sh                   # SLURM job script
├── render_one.sh               # Helper to render a single section
├── index.qmd                   # Overview page
├── 00_data_loading.qmd         # Data loading and preprocessing
├── 01_baseline.qmd             # Baseline metrics
├── 02_morphology.qmd           # Cell morphology
├── 03_clustering.qmd           # Clustering stability
├── 04_volume.qmd               # Volume (3D) metrics
├── 05_contamination.qmd        # Contamination / region similarity
├── 06_supervised.qmd           # Supervised metrics (optional)
├── 07_summary.qmd              # Summary and comparison
└── utils/
    ├── __init__.py
    └── helpers.py              # Shared utility functions
```

## Notes

- The Singularity container includes Quarto, so no local Quarto installation
  is required on the cluster.
- All analysis runs inside the container — no conda environment needed on
  the cluster.
- The `_freeze/` directory caches section outputs. Delete it to force a
  full rerun: `rm -rf _freeze/`.
- Computed metrics are saved to `data/processed/metrics/` as CSV files
  and accumulated across sections.

## References

- [SegTraQ](https://github.com/LazDaria/SegTraQ) — Lazic et al.
- [Proseg](https://github.com/dcjones/proseg) — Jones et al.
- [spatialdata](https://spatialdata.scverse.org/) — scverse
- [ovrlpy](https://github.com/HiDiHlabs/ovrlpy)
- [Quarto](https://quarto.org/)