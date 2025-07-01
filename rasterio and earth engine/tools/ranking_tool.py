def ranking_tool_fn(state):
    try:
        suitability_path = state["suitability_output"]
        num_top_locations = state.get("top_n", 5)
        output_path = f"data/{state['region']}_top_{num_top_locations}_locations.geojson"

        import rasterio
        import geopandas as gpd
        from shapely.geometry import Point
        import numpy as np

        with rasterio.open(suitability_path) as src:
            data = src.read(1)
            transform = src.transform

        flat_indices = np.argpartition(data.ravel(), -num_top_locations)[-num_top_locations:]
        coords = [~transform * (idx % data.shape[1], idx // data.shape[1]) for idx in flat_indices]

        gdf = gpd.GeoDataFrame(geometry=[Point(xy) for xy in coords], crs="EPSG:4326")
        gdf.to_file(output_path, driver="GeoJSON")

        state["cot_log"].append(f"Top {num_top_locations} ranked locations saved at {output_path}")
        return {
            **state,
            "ranking_output": output_path,
            "step": "complete"
        }
    except Exception as e:
        state["cot_log"].append(f"Error in ranking_tool_fn: {str(e)}")
        return {
            **state,
            "ranking_output": None,
            "step": "complete",
            "error": str(e)
        }
