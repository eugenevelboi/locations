# This script requires the Streamlit package.
# If you're seeing "ModuleNotFoundError: No module named 'streamlit'",
# install it by running: pip install streamlit

try:
    import streamlit as st
except ModuleNotFoundError:
    raise ImportError("Streamlit is not installed. Please install it using 'pip install streamlit'.")

import pandas as pd
import requests
from io import StringIO, BytesIO
import openpyxl

# --- Google Sheets CSV URLs ---
locations_xlsx_url = "https://docs.google.com/spreadsheets/d/1gJGJ_IGqybrN2C0O01uafzmJ43byKjGbAyi894hz2Lo/export?format=xlsx"
connections_url = "https://docs.google.com/spreadsheets/d/1gJGJ_IGqybrN2C0O01uafzmJ43byKjGbAyi894hz2Lo/gviz/tq?tqx=out:csv&sheet=Connections"

# --- Load Google Sheet Data ---
@st.cache_data(ttl=60, show_spinner=False)
def load_sheet(url):
    res = requests.get(url)
    return pd.read_csv(StringIO(res.text))

@st.cache_data(ttl=60, show_spinner=False)
def load_sheet_locations(url):
    # Priority lives in the cell colour, which the CSV export drops, so read
    # the xlsx export instead. Row 2 of the Locations tab is the colour key
    # ("Top Priority" / "Middle Priority" / "Low Priority"); every location
    # below the country header row takes the priority of its fill colour.
    res = requests.get(url)
    res.raise_for_status()
    ws = openpyxl.load_workbook(BytesIO(res.content))["Locations"]
    legend = {}
    for cell in ws[2]:
        label = str(cell.value or "").strip()
        if label.endswith(" Priority"):
            legend[cell.fill.fgColor.rgb] = label[:-len(" Priority")]
    found = {}
    for row in ws.iter_rows(min_row=4):
        for cell in row:
            name = str(cell.value or "").strip()
            if name and name not in found:
                found[name] = legend.get(cell.fill.fgColor.rgb, "Unassigned")
    return list(found.items())

try:
    all_locations = load_sheet_locations(locations_xlsx_url)
except Exception as e:
    st.error(f"Could not read the Locations sheet: {e}")
    st.stop()

# Always reload the master list on every rerun
st.session_state.location_master = pd.DataFrame(all_locations, columns=["Location", "Priority"])

# --- UI: Edit Location Master List ---
st.sidebar.header("📋 Manage Master Location List")
with st.sidebar.form("add_location"):
    new_location = st.text_input("Add New Location")
    new_priority = st.selectbox("Priority", ["Top", "Middle", "Low"])
    submitted = st.form_submit_button("Add Location")
    if submitted and new_location:
        st.session_state.location_master = pd.concat([
            st.session_state.location_master,
            pd.DataFrame([[new_location.strip(), new_priority]], columns=["Location", "Priority"])
        ]).drop_duplicates()

# Delete locations with confirmation
with st.sidebar.expander("❌ Remove Location"):
    selected_to_remove = st.selectbox("Pick location to remove", ["-"] + st.session_state.location_master["Location"].tolist())
    if selected_to_remove != "-":
        confirm_removal = st.checkbox("Are you sure you want to remove this location from the master list?")
        if confirm_removal:
            if st.button("Remove Location"):
                st.session_state.location_master = st.session_state.location_master[st.session_state.location_master["Location"] != selected_to_remove]
                st.rerun()

# --- Manual Refresh Button ---
if st.button("🔄 Refresh Sheets Now"):
    st.cache_data.clear()
    st.rerun()

connections_df = load_sheet(connections_url)

# --- Collect only used (current + Pr. Location 1) ---
used = pd.concat([
    connections_df['Current location'],
    connections_df['Pr. Location 1']
], ignore_index=True).dropna().str.strip().unique()

# --- Filter valid and available locations ---
master_df = st.session_state.location_master
valid_locations = master_df[~master_df["Location"].isin(used)]

# --- Group and display ---
st.title("📍 Available Locations (Filtered)")
st.markdown("Filtered from team usage (Current + Pr. Location 1 only) and grouped by priority.")

for priority in ["Top", "Middle", "Low", "Unassigned"]:
    subset = valid_locations[valid_locations["Priority"] == priority].sort_values("Location")
    if priority == "Unassigned" and subset.empty:
        continue
    with st.expander(f"{priority} Priority ({len(subset)})"):
        st.dataframe(subset.reset_index(drop=True))



