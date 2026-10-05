# This script requires the Streamlit package.
# If you're seeing "ModuleNotFoundError: No module named 'streamlit'",
# install it by running: pip install streamlit

try:
    import streamlit as st
except ModuleNotFoundError:
    raise ImportError("Streamlit is not installed. Please install it using 'pip install streamlit'.")

import pandas as pd
import requests
from io import StringIO
import csv

# --- Google Sheets CSV URLs ---
locations_url = "https://docs.google.com/spreadsheets/d/1gJGJ_IGqybrN2C0O01uafzmJ43byKjGbAyi894hz2Lo/gviz/tq?tqx=out:csv&sheet=Locations"
connections_url = "https://docs.google.com/spreadsheets/d/1gJGJ_IGqybrN2C0O01uafzmJ43byKjGbAyi894hz2Lo/gviz/tq?tqx=out:csv&sheet=Connections"

# --- Initial Clean Master List ---
top_priority = ["Los Angeles Metro, CA", "San Diego Metro, CA", "San Jose Metro, CA", "San Francisco Bay, CA", "Greater Houston, TX", "San Antonio, TX Metro", "Dallas-Fort Worth Metroplex, TX", "Austin, TX Metro", "Miami-Fort Lauderdale Area, FL", "Greater Tampa Bay Area, FL", "Greater Orlando, FL", "Metro Jacksonville, FL", "Florida (excl. Miami, Fort Lauderdale, Tampa Bay, Orlando, Jacksonville)", "New York", "Pennsylvania", "Illinois", "Ohio", "Georgia", "North Carolina", "Washington", "Massachusetts", "New South Wales", "North Rhine-Westphalia", "Bavaria", "Baden-Württemberg", "Hesse", "Berlin", "Île-de-France", "South Holland", "North Holland", "North Brabant", "Belgium", "Sweden", "Austria", "Switzerland", "Denmark", "Finland", "Norway", "Ireland"]

middle_priority = ["Texas (excl Houston, San Antonio, Dallas-Fort Worth, Austin)", "California (excl. LA, SD, SJ, SF)", "London", "Bristol", "Manchester", "Cambridge", "Birmingham", "New Jersey", "Virginia", "Michigan", "Arizona", "Tennessee", "Indiana", "Missouri", "Maryland", "Wisconsin", "Colorado", "Minnesota", "South Carolina", "Alabama", "Louisiana", "Kentucky", "Oregon", "Oklahoma", "Connecticut", "Utah", "Iowa", "Nevada", "Arkansas", "Mississippi", "Washington DC", "Queensland", "Victoria", "Lower Saxony / Rhineland-Palatinate / Saxony", "Schleswig-Holstein / Brandenburg / Saxony-Anhalt", "Thuringia / Hamburg / Mecklenburg-Vorpommern / Saarland / Bremen", "Auvergne-Rhône-Alpes", "Hauts-de-France", "Utrecht", "Overijssel", "Limburg", "Luxembourg", "Oxford / Reading / Surrey / Hampshire", "Edinburgh / Glasgow / Leeds / Belfast", "British Columbia", "Ontario", "Alberta"]

low_priority = ["Montreal", "Nouvelle-Aquitaine", "Grand Est", "Provence-Alpes-Côte d'Azur", "Gelderland", "Friesland", "Groningen / Drenthe / Flevoland / Zeeland", "Western Australia", "South Australia", "Tasmania", "Singapore", "United Arab Emirates", "New Zealand", "Kansas", "New Mexico", "Nebraska", "West Virginia", "Idaho", "Hawaii", "New Hampshire", "Maine", "Rhode Island", "Montana", "Delaware", "Alaska", "North Dakota", "South Dakota", "Vermont", "Wyoming", "Iceland", "Occitanie", "Pays de la Loire / Brittany", "Jersey / Guernsey / Isle of Man / Gibraltar / Liechtenstein"]

# --- Load Google Sheet Data ---
@st.cache_data(ttl=60, show_spinner=False)
def load_sheet(url):
    res = requests.get(url)
    return pd.read_csv(StringIO(res.text))

@st.cache_data(ttl=60, show_spinner=False)
def load_sheet_locations(url):
    # The Locations tab is a grid: a warning row, a priority row, a country
    # header row, then location names under each country column.
    res = requests.get(url)
    res.raise_for_status()
    rows = list(csv.reader(StringIO(res.text)))[3:]
    names = [cell.strip() for row in rows for cell in row if cell.strip()]
    return list(dict.fromkeys(names))

# The sheet is the source of truth for WHICH locations exist; the lists above
# only assign priorities. A name added to the sheet but not to a list above
# shows up as "Unassigned" until it is given a priority here.
priority_of = {}
for loc in top_priority:
    priority_of[loc] = "Top"
for loc in middle_priority:
    priority_of[loc] = "Middle"
for loc in low_priority:
    priority_of[loc] = "Low"

try:
    sheet_locations = load_sheet_locations(locations_url)
except Exception as e:
    sheet_locations = []
    st.warning(f"Could not read the Locations sheet ({e}); using the built-in list.")
if not sheet_locations:
    sheet_locations = list(priority_of)

# Always reload the master list on every rerun
all_locations = [(loc, priority_of.get(loc, "Unassigned")) for loc in sheet_locations]
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



