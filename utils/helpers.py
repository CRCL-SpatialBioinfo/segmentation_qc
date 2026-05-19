import yaml
import gzip
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import spatialdata as sd
import segtraq

from pathlib import Path
from spatialdata.transformations import get_transformation, set_transformation


def load_params(path="_params.yml"):
    """Load parameters from YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


# ── Data preparation helpers ──────────────────────────────────────────────────

def read_geojson_gz(path):
    """Read a gzipped GeoJSON file into a GeoDataFrame."""
    with gzip.open(path, "rt") as f:
        data = json.load(f)
    return gpd.GeoDataFrame.from_features(data["features"])


def add_proseg_zlayers(sdata, proseg_output_path):
    """Add per-z-layer cell boundaries from Proseg output."""
    polygons_layers_gz_path = Path(proseg_output_path) / "cell-polygons-layers.geojson.gz"
    polygons_layers_gdf = read_geojson_gz(polygons_layers_gz_path)

    for z, gdf in polygons_layers_gdf.groupby("layer", sort=True):
        sdata.shapes[f"cell_boundaries_z{int(z)}"] = sd.models.ShapesModel.parse(
            gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
        )
        sdata.shapes[f"cell_boundaries_z{int(z)}"].set_index("cell", drop=True, inplace=True)

    return sdata


def align_to_xenium(sdata_target, sdata_xenium, has_zlayers=False):
    """
    Copy image and nucleus boundaries from Xenium SpatialData
    and align transformations.
    """
    xenium_transformation = get_transformation(sdata_xenium.shapes["cell_boundaries"])

    sdata_target.images["morphology_focus"] = sdata_xenium.images["morphology_focus"]
    sdata_target.shapes["nucleus_boundaries"] = sdata_xenium.shapes["nucleus_boundaries"]

    set_transformation(sdata_target.shapes["cell_boundaries"], xenium_transformation)
    set_transformation(sdata_target.points["transcripts"], xenium_transformation)

    if has_zlayers:
        for k in sdata_target.shapes:
            if k.startswith("cell_boundaries_z"):
                set_transformation(sdata_target.shapes[k], xenium_transformation)

    return sdata_target


# ── SegTraQ initialization ────────────────────────────────────────────────────

def init_segtraq_objects(sdata_xenium, sdata_proseg3):
    """Initialize SegTraQ objects with method-specific parameters."""

    # Xenium: create cell_id column from index if not present
    if "cell_id" not in sdata_xenium.shapes["cell_boundaries"].columns:
        sdata_xenium.shapes["cell_boundaries"]["cell_id"] = (
            sdata_xenium.shapes["cell_boundaries"].index
        )

    st_xenium = segtraq.SegTraQ(
        sdata_xenium,
        tables_centroid_x_key=None,
        tables_centroid_y_key=None,
        points_background_id="UNASSIGNED",  # "UNASSIGNED" in Xenium Prime
    )

    # Proseg v3: re-link table to shapes if spatialdata_attrs missing
    if "spatialdata_attrs" not in sdata_proseg3.tables["table"].uns:
        sdata_proseg3.tables["table"].obs["region"] = "cell_boundaries"
        sdata_proseg3.tables["table"].obs["region"] = (
            sdata_proseg3.tables["table"].obs["region"].astype("category")
        )
        sdata_proseg3.set_table_annotates_spatialelement(
            "table", region="cell_boundaries", region_key="region", instance_key="cell"
        )

    st_proseg3 = segtraq.SegTraQ(
        sdata_proseg3,
        points_cell_id_key="assignment",
        points_background_id=None,
        points_gene_key="gene",
        tables_area_key=None,
        tables_cell_id_key="cell",
        shapes_cell_id_key="cell",
        tables_centroid_x_key="centroid_x",
        tables_centroid_y_key="centroid_y",
    )

    return {"xenium": st_xenium, "proseg_v3": st_proseg3}


def load_processed_data(params):
    """
    Load preprocessed SpatialData objects from zarr and initialize SegTraQ.
    Expects processed zarr files written by 00_data_loading.qmd.
    """
    sdata_xenium = sd.read_zarr(params["processed_xenium_path"])
    sdata_proseg3 = sd.read_zarr(params["processed_proseg_path"])

    return init_segtraq_objects(sdata_xenium, sdata_proseg3)


def filter_transcripts(st_dict, params):
    """
    Filter control probes and low quality transcripts.
    Proseg v3 already filters internally, so min_qv is set to None for it.
    """
    for method, st in st_dict.items():
        # Proseg already filters low quality transcripts internally
        min_qv = None if "proseg" in method else params["min_qv"]
        st.filter_control_and_low_quality_transcripts(min_qv=min_qv)
        if min_qv is None:
            print(f"{method}: control probes filtered (qv filtering skipped — already applied by Proseg)")
        else:
            print(f"{method}: transcripts filtered (min_qv={min_qv})")
    return st_dict


def save_metrics(st_dict, output_dir="_output/metrics"):
    """
    Save obs dataframe with computed metrics to CSV for each method.
    Merges with existing CSV if present, to accumulate metrics across sections.
    """
    from pathlib import Path
    import pandas as pd
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    for method, st in st_dict.items():
        obs_new = st.sdata.tables["table"].obs.copy()
        path = f"{output_dir}/{method}_obs.csv"
        
        # Merge with existing CSV if present
        if Path(path).exists():
            obs_existing = pd.read_csv(path, index_col=0)
            # Add new columns only — don't overwrite existing ones
            new_cols = [c for c in obs_new.columns if c not in obs_existing.columns]
            if new_cols:
                obs_merged = obs_existing.join(obs_new[new_cols], how="left")
            else:
                obs_merged = obs_existing
        else:
            obs_merged = obs_new
        
        obs_merged.to_csv(path)
        print(f"{method}: metrics saved to {path}")


def load_metrics(methods, output_dir="_output/metrics"):
    """Load precomputed obs metrics from CSV."""
    obs_dict = {}
    for method in methods:
        path = f"{output_dir}/{method}_obs.csv"
        obs_dict[method] = pd.read_csv(path, index_col=0)
        print(f"{method}: metrics loaded from {path}")
    return obs_dict