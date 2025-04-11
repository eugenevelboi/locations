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

# --- Google Sheets CSV URLs ---
locations_url = "https://docs.google.com/spreadsheets/d/1gJGJ_IGqybrN2C0O01uafzmJ43byKjGbAyi894hz2Lo/gviz/tq?tqx=out:csv&sheet=Locations"
connections_url = "https://docs.google.com/spreadsheets/d/1gJGJ_IGqybrN2C0O01uafzmJ43byKjGbAyi894hz2Lo/gviz/tq?tqx=out:csv&sheet=Connections"

# --- Initial Clean Master List ---
top_priority = ["Los Angeles Metro, CA", "San Diego Metro, CA", "San Jose Metro, CA", "San Francisco Bay, CA", "California (excl. LA, SD, SJ, SF)", "Greater Houston, TX", "San Antonio, TX Metro", "Dallas-Fort Worth Metroplex, TX", "Austin, TX Metro", "Texas (excl Houston, San Antonio, Dallas-Fort Worth, Austin)", "Miami-Fort Lauderdale Area, FL", "Greater Tampa Bay Area, FL", "Greater Orlando, FL", "Metro Jacksonville, FL", "Florida (excl. Miami, Fort Lauderdale, Tampa Bay, Orlando, Jacksonville)", "New York", "Pennsylvania", "Illinois", "Ohio", "Georgia", "North Carolina", "Washington", "Massachusetts", "New South Wales", "North Rhine-Westphalia", "Hesse", "Berlin", "Île-de-France", "South Holland", "North Holland", "North Brabant", "Belgium", "Sweden", "Austria", "Switzerland", "Denmark", "Finland", "Norway", "Ireland"]

middle_priority = ["London", "Bristol", "Manchester", "Cambridge", "Birmingham", "Nottingham / Leeds / Newcastle", "Scotland", "Wales", "Northern Ireland", "New Jersey", "Virginia", "Michigan", "Arizona", "Tennessee", "Indiana", "Missouri", "Maryland", "Wisconsin", "Colorado", "Minnesota", "South Carolina", "Alabama", "Louisiana", "Kentucky", "Oregon", "Oklahoma", "Connecticut", "Utah", "Iowa", "Nevada", "Arkansas", "Mississippi", "Washington DC", "Queensland", "Victoria", "Bavaria", "Baden-Württemberg", "Lower Saxony / Rhineland-Palatinate / Saarland", "Schleswig-Holstein / Brandenburg / Saxony-Anhalt", "Thuringia / Hamburg / Mecklenburg-Vorpommern / Saarland", "Auvergne-Rhône-Alpes", "Hauts-de-France", "Utrecht", "Overijssel", "Limburg", "Luxembourg", "Greater Vancouver", "Greater Toronto", "Greater Ottawa"]

low_priority = ["Montreal", "Waterloo", "Nouvelle-Aquitaine", "Grand Est", "Provence-Alpes-Côte d'Azur", "Gelderland", "Friesland", "Groningen / Drenthe / Flevoland / Zeeland", "Spain", "Western Australia", "South Australia", "Tasmania", "Singapore", "United Arab Emirates", "New Zealand", "Cape Town", "Japan", "Israel", "South Korea", "Hong Kong", "Taiwan", "Kansas", "New Mexico", "Nebraska", "West Virginia", "Idaho", "Hawaii", "New Hampshire", "Maine", "Rhode Island", "Montana", "Delaware", "Alaska", "North Dakota", "South Dakota", "Vermont", "Wyoming", "Iceland"]

# Always reload the master list on every rerun
all_locations = (
    [(loc, "Top") for loc in top_priority] +
    [(loc, "Middle") for loc in middle_priority] +
    [(loc, "Low") for loc in low_priority]
)
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

# Delete locations
remove_loc = st.sidebar.selectbox("Remove Location", ["-"] + st.session_state.location_master["Location"].tolist())
if remove_loc != "-":
    st.session_state.location_master = st.session_state.location_master[st.session_state.location_master["Location"] != remove_loc]
    st.experimental_rerun()

# --- Manual Refresh Button ---
if st.button("🔄 Refresh Sheets Now"):
    st.cache_data.clear()
    st.experimental_rerun()

# --- Load Google Sheet Data ---
@st.cache_data(ttl=60, show_spinner=False)
def load_sheet(url):
    res = requests.get(url)
    return pd.read_csv(StringIO(res.text))

locations_df = load_sheet(locations_url)
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

for priority in ["Top", "Middle", "Low"]:
    subset = valid_locations[valid_locations["Priority"] == priority].sort_values("Location")
    with st.expander(f"{priority} Priority ({len(subset)})"):
        st.dataframe(subset.reset_index(drop=True))
