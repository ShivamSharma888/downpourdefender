import streamlit as st
import pandas as pd
import requests
import pickle
import time
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------
# Page configuration & Styling
# -----------------------------
st.set_page_config(
    page_title="Downpour Defender 🌧",
    page_icon="⛈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .metric-card {background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 15px;}
    </style>
""", unsafe_allow_html=True)

# -----------------------------
# Telegram Configuration
# -----------------------------
# Corrected Token and Chat ID logic
TELEGRAM_TOKEN = "7960388374:AAEThNnB47kmzBQR3Y04sSB67XZRdsRW-tc"
TELEGRAM_CHAT_ID = 8175531261

def send_telegram_msg(text):
    try:
        # Crucial: The URL must have 'bot' before the token
        url = f"https://api.telegram.org/bot7960388374:AAEThNnB47kmzBQR3Y04sSB67XZRdsRW-tc/sendMessage"
        payload = {
            "chat_id": 8175531261, 
            "text": text, 
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=5)
        
        # This will show an error in the sidebar if Telegram rejects the message
        if response.status_code != 200:
            st.sidebar.error(f"Telegram Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        st.sidebar.error(f"Connection Error: {e}")
        return False

# -----------------------------
# Error Handling: Load Model
# -----------------------------
class DummyModel:
    """Fallback model in case cloudburst_model.pkl is missing."""
    def predict(self, df):
        rain = df['rainfall'].iloc[0]
        return [1 if rain > 80 else 0]
    
    def predict_proba(self, df):
        rain = df['rainfall'].iloc[0]
        prob = min(rain / 120.0, 0.99)
        return [[1-prob, prob]]

try:
    model = pickle.load(open("cloudburst_model.pkl","rb"))
    model_status = "✅ ML Model Loaded"
except FileNotFoundError:
    model = DummyModel()
    model_status = "⚠️ Using Fallback Simulation Model"

# -----------------------------
# Session State for HP Districts
# -----------------------------
if "locations" not in st.session_state:
    st.session_state.locations = {
        "Bilaspur": {"lat": 31.33, "lon": 76.75},
        "Chamba": {"lat": 32.55, "lon": 76.13},
        "Hamirpur": {"lat": 31.68, "lon": 76.52},
        "Kangra": {"lat": 32.10, "lon": 76.27},
        "Kinnaur": {"lat": 31.65, "lon": 78.47},
        "Kullu": {"lat": 31.96, "lon": 77.11},
        "Lahaul and Spiti": {"lat": 32.57, "lon": 77.41},
        "Mandi": {"lat": 31.59, "lon": 76.92},
        "Shimla": {"lat": 31.10, "lon": 77.17},
        "Sirmaur": {"lat": 30.59, "lon": 77.30},
        "Solan": {"lat": 30.90, "lon": 77.10},
        "Una": {"lat": 31.47, "lon": 76.27}
    }

# -----------------------------
# Sidebar & Location Tools
# -----------------------------
st.sidebar.title("🌍 Downpour Defender")
st.sidebar.caption(model_status)
st.sidebar.divider()

st.sidebar.header("📍 Location Manager")

if st.sidebar.button("📡 Detect My Location"):
    try:
        loc_data = requests.get("http://ip-api.com/json/", timeout=5).json()
        if loc_data['status'] == 'success':
            city = loc_data['city']
            st.session_state.locations[f"Auto: {city}"] = {"lat": loc_data['lat'], "lon": loc_data['lon']}
            st.sidebar.success(f"Found: {city}")
            st.rerun()
    except Exception:
        st.sidebar.error("Could not detect location.")

new_city = st.sidebar.text_input("🔍 Search City Manually:")
if st.sidebar.button("Add City"):
    if new_city:
        try:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={new_city}&count=1&language=en&format=json"
            geo_data = requests.get(geo_url).json()
            if "results" in geo_data:
                lat = geo_data["results"][0]["latitude"]
                lon = geo_data["results"][0]["longitude"]
                name = geo_data["results"][0]["name"]
                st.session_state.locations[name] = {"lat": lat, "lon": lon}
                st.sidebar.success(f"Added {name}!")
                st.rerun()
        except Exception:
            st.sidebar.error("Geocoding service error.")

selected_locations = st.sidebar.multiselect(
    "Active Dashboards:", 
    list(st.session_state.locations.keys()), 
    default=["Mandi", "Shimla", "Kullu"]
)

# -----------------------------
# Sidebar: Live Monitoring (2-Min Alerts)
# -----------------------------
st.sidebar.divider()
st.sidebar.header("📡 Live Monitoring")
enable_alerts = st.sidebar.toggle("Enable 2-Minute Telegram Alerts")

if enable_alerts:
    if not selected_locations:
        st.sidebar.warning("⚠️ Select a location first!")
    else:
        if "last_alert_time" not in st.session_state:
            st.session_state.last_alert_time = 0

        current_ts = time.time()
        
        # Check if 120 seconds have passed
        if current_ts - st.session_state.last_alert_time > 120:
            monitor_loc = selected_locations[0]
            m_lat, m_lon = st.session_state.locations[monitor_loc]["lat"], st.session_state.locations[monitor_loc]["lon"]
            
            try:
                # Fetch live data for the alert
                r_url = f"https://api.open-meteo.com/v1/forecast?latitude={m_lat}&longitude={m_lon}&current_weather=true&hourly=precipitation"
                res = requests.get(r_url).json()
                curr_r = res["hourly"]["precipitation"][0]
                curr_t = res["current_weather"]["temperature"]
                
                risk_txt = "🚨 HIGH RISK" if curr_r > 80 else "✅ STABLE"
                
                msg = (
                    f"🛰 *Downpour Defender Update*\n"
                    f"📍 *Location:* {monitor_loc}\n"
                    f"📊 *Condition:* {risk_txt}\n"
                    f"🌧 *Rainfall:* {curr_r:.1f} mm/hr\n"
                    f"🌡 *Temp:* {curr_t}°C"
                )
                
                if send_telegram_msg(msg):
                    st.session_state.last_alert_time = current_ts
                    st.sidebar.success(f"Alert sent for {monitor_loc}!")
            except:
                st.sidebar.error("Data fetch failed for alert.")

        # Countdown Display
        time_left = int(120 - (time.time() - st.session_state.last_alert_time))
        st.sidebar.caption(f"Next update in approx: {max(0, time_left)}s")
        if st.sidebar.button("🔄 Refresh & Check Now"):
            st.rerun()

# -----------------------------
# Core Functions
# -----------------------------
def fetch_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=precipitation"
    response = requests.get(url).json()
    temp = response["current_weather"]["temperature"]
    wind = response["current_weather"]["windspeed"]
    rain = response["hourly"]["precipitation"][0]
    return rain, temp, wind

def predict_cloudburst(rain, temp, wind):
    df = pd.DataFrame({"rainfall":[rain], "temperature":[temp], "windspeed":[wind]})
    pred = model.predict(df)[0]
    probabilities = model.predict_proba(df)[0]
    prob = probabilities[1] if len(probabilities) > 1 else (1.0 if pred == 1 else 0.0)
    return pred, prob

# -----------------------------
# Main Dashboard
# -----------------------------
st.title("🌧 Downpour Defender Dashboard")

if not selected_locations:
    st.info("👈 Please select or add a location from the sidebar to view the dashboard.")
else:
    tabs = st.tabs(selected_locations)

    for i, loc in enumerate(selected_locations):
        with tabs[i]:
            lat, lon = st.session_state.locations[loc]["lat"], st.session_state.locations[loc]["lon"]
            
            with st.spinner(f"Fetching live data for {loc}..."):
                try:
                    rain, temp, wind = fetch_weather(lat, lon)
                    pred, prob = predict_cloudburst(rain, temp, wind)

                    if pred == 1 or rain > 80:
                        risk, color = "High Risk", "red"
                    elif prob > 0.4:
                        risk, color = "Moderate Risk", "orange"
                    else:
                        risk, color = "Low Risk", "green"

                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("🌧 Rainfall (mm/hr)", f"{rain:.1f}")
                    col2.metric("🌡 Temp (°C)", f"{temp:.1f}")
                    col3.metric("💨 Wind (km/h)", f"{wind:.1f}")
                    col4.metric("⚠️ Alert Status", risk)

                    st.markdown("---")
                    st.subheader("📊 Live Weather & Risk Analysis")
                    g_col1, g_col2 = st.columns((1, 2))

                    with g_col1:
                        fig_gauge = go.Figure(go.Indicator(
                            mode = "gauge+number",
                            value = prob * 100,
                            title = {'text': "Cloudburst Probability (%)"},
                            gauge = {
                                'axis': {'range': [None, 100]},
                                'bar': {'color': color},
                                'steps': [
                                    {'range': [0, 40], 'color': "lightgreen"},
                                    {'range': [40, 80], 'color': "lightyellow"},
                                    {'range': [80, 100], 'color': "salmon"}
                                ]
                            }
                        ))
                        fig_gauge.update_layout(height=300, margin=dict(l=10, r=10, t=40, b=10))
                        st.plotly_chart(fig_gauge, use_container_width=True)

                    with g_col2:
                        days = [(datetime.now() - timedelta(days=x)).strftime("%b %d") for x in range(6,-1,-1)]
                        trend = pd.DataFrame({
                            "Date": days,
                            "Rainfall (mm)": [rain*0.9, rain*1.1, rain*0.8, rain*1, rain*0.7, rain*1.2, rain*0.95],
                            "Temp (°C)": [temp+0.5, temp-0.2, temp+0.3, temp, temp-0.4, temp+0.1, temp+0.2]
                        })
                        fig_line = px.area(trend, x="Date", y=["Rainfall (mm)", "Temp (°C)"], 
                                           title="Simulated 7-Day Microclimate Trend",
                                           color_discrete_map={"Rainfall (mm)": "#1f77b4", "Temp (°C)": "#ff7f0e"})
                        fig_line.update_layout(height=300, margin=dict(l=10, r=10, t=40, b=10))
                        st.plotly_chart(fig_line, use_container_width=True)

                    with st.expander("🗺️ View Location on Map"):
                        st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=10)
                except Exception:
                    st.error(f"Error loading weather data for {loc}.")

st.divider()

# -----------------------------
# Internal Chatbot Section
# -----------------------------
st.header("🌍 Environmental Assistant")
st.markdown("Ask about cloudbursts, weather safety, or disaster management.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask me about extreme weather..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        q = prompt.lower()
        if "cloudburst" in q:
            response = "**Cloudbursts:** Extreme localized rainfall events. Climate change increases their frequency."
        elif "warming" in q or "climate" in q:
            response = "**Global Warming:** Rising temperatures disrupt monsoon patterns in Himachal."
        elif "safe" in q or "prepare" in q:
            response = "**Safety Tips:** 1. Move to higher ground. 2. Avoid floodwaters. 3. Tune to alerts."
        else:
            response = "I am the Downpour Defender assistant specializing in Cloudbursts and Safety."
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# -----------------------------
# Updated Footer
# -----------------------------
st.markdown("""
<br><br>
<center>
<p style='color: #787;'>Developed for Disaster Early Warning Systems</p>
<p><b>Developed by: Ansh Thakur, Piyush Sharma </b></p>
<p><b> Lecturer Hemant Kumar</b> </p>
<small><b>Downpour Defender</b> | Project 2026</small>
</center>
""", unsafe_allow_html=True)
