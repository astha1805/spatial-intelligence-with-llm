def suitability_tool_fn(state):
    try:
        criteria_paths = state["criteria_paths"]  # list of raster paths
        weights = state["weights"]                # list of weights
        output_path = f"data/{state['region']}_suitability.tif"

        import rasterio
        import numpy as np

        weighted_sum = None
        for path, weight in zip(criteria_paths, weights):
            with rasterio.open(path) as src:
                data = src.read(1).astype(np.float32)
                if weighted_sum is None:
                    weighted_sum = weight * data
                    meta = src.meta.copy()
                else:
                    weighted_sum += weight * data

        # Normalize
        weighted_sum = (weighted_sum - weighted_sum.min()) / (weighted_sum.max() - weighted_sum.min())

        meta.update(dtype='float32')
        with rasterio.open(output_path, 'w', **meta) as dst:
            dst.write(weighted_sum, 1)

        state["cot_log"].append(f"Generated suitability map at {output_path}")
        return {
            **state,
            "suitability_output": output_path,
            "step": "complete"
        }
    except Exception as e:
        state["cot_log"].append(f"Error in suitability_tool_fn: {str(e)}")
        return {
            **state,
            "step": "complete",
            "suitability_output": None,
            "error": str(e)
        }
