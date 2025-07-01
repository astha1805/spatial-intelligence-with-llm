from rasterio.mask import mask
import rasterio
import geopandas as gpd
from shapely.geometry import mapping
import numpy as np
from numpy import ma

def raster_tool_fn(state):
    try:
        region_path = state["region_path"]
        dem_path = state["dem_path"]
        threshold = state["threshold"]

        region = gpd.read_file(region_path).to_crs("EPSG:4326")
        with rasterio.open(dem_path) as src:
            geom = [mapping(region.unary_union)]
            clipped, transform = mask(src, geom, crop=True)
            meta = src.meta.copy()

            nodata = src.nodata if src.nodata is not None else -32768
            elevation_data = clipped[0].astype(np.float32)
            elevation_data[elevation_data == nodata] = np.nan  # Mask out nodata

            mask_arr = (elevation_data < threshold).astype(np.uint8)

            meta.update({
                "height": mask_arr.shape[0],
                "width": mask_arr.shape[1],
                "transform": transform,
                "dtype": "uint8",
                "count": 1,
                "nodata": 0  # Set a valid nodata for uint8
            })

            out_path = f"data/{state['region']}_low_elevation_mask.tif"
            with rasterio.open(out_path, "w", **meta) as dst:
                dst.write(mask_arr, 1)

        # Log CoT
        state["cot_log"].append(f"Performed elevation masking below {threshold}m and saved to {out_path}")

        # Update state
        return {
            **state,
            "raster_result": {"status": "success", "raster_output": out_path},
            "step": "complete"
        }
    except Exception as e:
        state["cot_log"].append(f"Error in raster_tool_fn: {str(e)}")
        return {
            **state,
            "raster_result": {"status": "error", "error_msg": str(e)},
            "step": "complete"
        }