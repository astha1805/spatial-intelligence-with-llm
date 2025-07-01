def disaster_safe_tool_fn(state):
    try:
        mask_path = state["hazard_mask_path"]  # binary mask (1 = unsafe, 0 = safe)
        region_path = state["region_path"]
        output_path = f"data/{state['region']}_safe_zones.geojson"

        import rasterio
        import geopandas as gpd
        import numpy as np
        from shapely.geometry import shape

        with rasterio.open(mask_path) as src:
            mask_data = src.read(1)
            transform = src.transform

        # Get polygons where mask == 0 (safe)
        from rasterio.features import shapes
        shapes_gen = shapes(mask_data == 0, transform=transform)
        safe_shapes = [shape(geom) for geom, val in shapes_gen if val]

        safe_gdf = gpd.GeoDataFrame(geometry=safe_shapes, crs="EPSG:4326")
        safe_gdf.to_file(output_path, driver="GeoJSON")

        state["cot_log"].append(f"Disaster-safe zones saved to {output_path}")
        return {
            **state,
            "safe_zones_output": output_path,
            "step": "complete"
        }
    except Exception as e:
        state["cot_log"].append(f"Error in disaster_safe_tool_fn: {str(e)}")
        return {
            **state,
            "safe_zones_output": None,
            "step": "complete",
            "error": str(e)
        }
