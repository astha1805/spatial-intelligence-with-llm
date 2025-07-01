from langgraph.graph import StateGraph
from langchain_groq.chat_models import ChatGroq
from tools.raster_tool import raster_tool_fn
from tools.vector_tool import vector_tool_fn
from tools.disaster_tool import disaster_safe_tool_fn
from tools.ranking_tool import ranking_tool_fn
from tools.suitability_tool import suitability_tool_fn

import osmnx as ox
import os
import ee
import geemap
import geopandas as gpd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize LLM and Earth Engine
llm = ChatGroq(model="llama3-8b-8192")
ee.Authenticate()
ee.Initialize()

# Helper: download OSM boundary
def fetch_boundary(region):
    path = f"data/{region}_boundary.geojson"
    if not os.path.exists(path):
        gdf = ox.geocode_to_gdf(region)
        gdf.to_file(path, driver="GeoJSON")
    return path

# Helper: fetch DEM from GEE
def fetch_dem(region):
    region_path = fetch_boundary(region)
    dem_path = f"data/srtm_{region}.tif"
    if os.path.exists(dem_path):
        return dem_path

    gdf = gpd.read_file(region_path)
    bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
    dem = ee.Image("USGS/SRTMGL1_003").clip(ee.Geometry.BBox(*bounds))
    geemap.download_ee_image(dem, filename=dem_path, scale=30, crs='EPSG:4326')
    return dem_path

# Reasoning node with CoT logging
def reasoning_node(state):
    import re
    query = state.get("query", "").lower()
    state["cot_log"].append(f"Received query: '{query}'")

    # Extract region (e.g., 'in Gujarat', 'around Shimla')
    match = re.search(r'(?:in|around|near|buffer)\s+([a-zA-Z ,]+)', query)
    region = match.group(1).strip() if match else "India"
    state["region"] = region.replace(" ", "_")
    state["cot_log"].append(f"Extracted region: '{region}'")

    # Optional: Extract 'top_n' for ranking
    match_n = re.search(r'(top|best)\s+(\d+)', query)
    if match_n:
        state["top_n"] = int(match_n.group(1))
        state["cot_log"].append(f"Extracted top_n: {state['top_n']}")

    # Fetch boundary and DEM paths
    region_path = fetch_boundary(region)
    state["cot_log"].append(f"Fetched boundary: {region_path}")
    dem_path = fetch_dem(region)
    state["cot_log"].append(f"Fetched DEM: {dem_path}")

    # Route to ranking
    if "rank" in query or "top" in query:
        state["cot_log"].append("Routing to ranking_analysis")
        return {
            **state,
            "suitability_output": f"data/{state['region']}_suitability.tif",  # assumed input
            "step": "ranking_analysis"
        }

    # Route to suitability analysis
    elif "suitable" in query or "suitability" in query:
        state["cot_log"].append("Routing to suitability_analysis")
        return {
            **state,
            "region_path": region_path,
            "dem_path": dem_path,
            "step": "suitability_analysis"
        }

    # Route to raster or vector analysis
    elif "elevation" in query or "height" in query:
        state["cot_log"].append("Routing to raster_analysis")
        return {
            **state,
            "region_path": region_path,
            "dem_path": dem_path,
            "threshold": 50,
            "step": "raster_analysis"
        }
    else:
        state["cot_log"].append("Routing to vector_analysis")
        return {
            **state,
            "vector_path": region_path,
            "buffer_distance": 1000,
            "step": "vector_analysis"
        }

# Observation node: finalize
def observation_node(state):
    state["cot_log"].append("Workflow complete")
    return {**state, "step": "complete"}

# Build and run LangGraph
workflow = StateGraph(state_schema=dict)
workflow.add_node("reasoning", reasoning_node)
workflow.add_node("raster_analysis", raster_tool_fn)
workflow.add_node("vector_analysis", vector_tool_fn)
workflow.add_node("observe", observation_node)
workflow.set_entry_point("reasoning")
workflow.add_conditional_edges("reasoning", lambda s: s["step"])
workflow.add_edge("raster_analysis", "observe")
workflow.add_edge("vector_analysis", "observe")
workflow.add_node("suitability_analysis", suitability_tool_fn)
workflow.add_node("ranking", ranking_tool_fn)
workflow.add_node("disaster_safe", disaster_safe_tool_fn)
workflow.add_conditional_edges("observe", lambda s: s["step"])

app = workflow.compile()

if __name__ == "__main__":
    query = input("Ask your spatial query: ")
    state = {"query": query, "cot_log": []}
    final = app.invoke(state)

    print("Chain of Thought:")
    for step in final.get("cot_log", []):
        print(" -", step)

    print("Final Output:", {k: v for k, v in final.items() if k not in ['cot_log']})
