import streamlit as st
import json
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from main import app  # LangGraph workflow
import os

st.set_page_config(page_title="🧠 Spatial LLM Map", layout="wide")
st.title("🗺️ Spatial Query Assistant")

# Initialize session state
if "final" not in st.session_state:
    st.session_state.final = None

query = st.text_input("🔍 Ask your spatial query:", placeholder="e.g., Give me areas below 50m in Gujarat")

# Run the query
if st.button("Run Query") and query.strip():
    with st.spinner("🧠 Processing your query..."):
        state = {"query": query, "cot_log": []}
        st.session_state.final = app.invoke(state)

# Retrieve result
final = st.session_state.final

if final:
    st.subheader("🧩 Chain of Thought")
    for step in final.get("cot_log", []):
        st.markdown(f"- {step}")

    st.subheader("🧬 Final Output State")
    st.json({k: v for k, v in final.items() if k != "cot_log"})

    # Determine best map path to display
    map_path = None
    if final.get("raster_result", {}).get("vectorized_output") and os.path.exists(final["raster_result"]["vectorized_output"]):
        map_path = final["raster_result"]["vectorized_output"]
        map_title = "🌄 Thresholded Elevation Areas"
    elif final.get("vector_result", {}).get("vector_output") and os.path.exists(final["vector_result"]["vector_output"]):
        map_path = final["vector_result"]["vector_output"]
        map_title = "🟢 Buffered Area"
    elif final.get("vector_path") and os.path.exists(final["vector_path"]):
        map_path = final["vector_path"]
        map_title = "🗺️ Input Region"

    # Show map
    if map_path:
        try:
            gdf = gpd.read_file(map_path)
            if not gdf.empty:
                bounds = gdf.total_bounds
                m = folium.Map(
                    location=[(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2],
                    zoom_start=7
                )
                folium.GeoJson(gdf, name="Geo Output").add_to(m)
                st.subheader(map_title)
                st_folium(m, width=800, height=500)
            else:
                st.warning("⚠️ GeoDataFrame is empty.")
        except Exception as e:
            st.error(f"❌ Error displaying map: {e}")
    else:
        st.warning("⚠️ No map output available.")

    # Download buttons
    if "dem_path" in final and final["dem_path"] and os.path.exists(final["dem_path"]):
        st.download_button("📥 Download DEM", open(final["dem_path"], "rb"), file_name=os.path.basename(final["dem_path"]))

    if "suitability_output" in final and final["suitability_output"] and os.path.exists(final["suitability_output"]):
        st.download_button("📥 Download Suitability Raster", open(final["suitability_output"], "rb"), file_name=os.path.basename(final["suitability_output"]))

    if final.get("raster_result", {}).get("raster_output") and os.path.exists(final["raster_result"]["raster_output"]):
        st.download_button("📥 Download Masked Raster", open(final["raster_result"]["raster_output"], "rb"),
                           file_name=os.path.basename(final["raster_result"]["raster_output"]))
