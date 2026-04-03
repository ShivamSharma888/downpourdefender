import streamlit as st
import requests
import pandas as pd
import pickle
import time

# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="Downpour Defender",
    page_icon="🌧",
    layout="wide"
)

# -----------------------------
# Custom CSS Styling
# -----------------------------
st.markdown("""
<style>

.main {
    background-color: #0E1117;
}

.title {
    text-align: center;
    font-size: 50px;
    color: #4FC3F7;
    font-weight: bold;
}

.subtitle {
    text-align: center;
    color: #BBBBBB;
}

.metric-card {
    background-color: #1E1E1E;
    padding: 20px;
    border-radius: 10px;
    text-align: center;
    color: white;
    font-size: 20px;
}

.alert {
    font-size: 35px;
    text-align: center;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)

# -----------------------------
# Load ML Model
# -----------------------------
model = pickle.load(open("cloudburst_model.pkl","rb"))

# -----------------------------
# Title Section
# -----------------------------
st.markdown('<p class="title">🌧 Downpour Defender</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">AI Based Cloudburst Prediction System</p>', unsafe_allow_html=True)

st.divider()

# -----------------------------
# Fetch Live Weather Data
# -----------------------------
url = "https://api.open-meteo.com/v1/forecast?latitude=31.55&longitude=77.17&current_weather=true&hourly=precipitation"

data = requests.get(url).json()

temperature = data["current_weather"]["temperature"]
windspeed = data["current_weather"]["windspeed"]
rainfall = data["hourly"]["precipitation"][0]

# -----------------------------
# Metrics Dashboard
# -----------------------------
col1, col2, col3 = st.columns(3)

col1.metric("🌧 Rainfall (mm)", rainfall)
col2.metric("🌡 Temperature (°C)", temperature)
col3.metric("💨 Wind Speed (km/h)", windspeed)

st.divider()

# -----------------------------
# Prediction
# -----------------------------
input_data = pd.DataFrame({
    "rainfall":[rainfall],
    "temperature":[temperature],
    "windspeed":[windspeed]
})

prediction = model.predict(input_data)

# small animation delay
with st.spinner("Analyzing weather patterns..."):
    time.sleep(2)

# -----------------------------
# Alert System
# -----------------------------
if rainfall > 100 or prediction[0] == 1:

    st.error("⚠️ CLOUD BURST ALERT ⚠️")

    st.markdown("""
    <div class="alert" style="color:red;">
    🚨 HIGH RISK OF CLOUDBURST 🚨
    </div>
    """, unsafe_allow_html=True)

else:

    st.success("✅ Weather Conditions Normal")

st.divider()

# -----------------------------
# Weather Chart
# -----------------------------
st.subheader("📊 Weather Parameters")

weather_chart = pd.DataFrame({
    "Parameter":["Rainfall","Temperature","Wind Speed"],
    "Value":[rainfall, temperature, windspeed]
})

st.bar_chart(weather_chart.set_index("Parameter"))

# -----------------------------
# Map of Monitoring Area
# -----------------------------
st.subheader("🗺 Monitoring Location")

map_data = pd.DataFrame({
    "lat":[31.55],
    "lon":[77.17]
})

st.map(map_data)

st.divider()

# -----------------------------
# Footer
# -----------------------------
st.markdown(
"""
<center>
Developed for Disaster Early Warning System<br>
Project: <b>Downpour Defender</b>
</center>
""",
unsafe_allow_html=True
)