import streamlit as st
import pandas as pd
import requests
import pickle
import time
import plotly.graph_objects as go
import pydeck as pdk

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Downpour Defender 🌧", layout="wide")

# -----------------------------
# UI STYLE
# -----------------------------
st.markdown("""
<style>

.card {
    background: white;
    color: black;   /* ✅ ADD THIS */
    padding: 15px;
    border-radius: 15px;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
}


""", unsafe_allow_html=True)

# -----------------------------
# TELEGRAM
# -----------------------------
import requests

TOKEN = "YOUR_NEW_TOKEN"
CHAT_ID = "-1003814185899"

def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot8754743480:AAFUdPETX7l431QNuWxZqMIoQGDR82ScxhQ/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg},
            timeout=5
        )
    except:
        pass

# -----------------------------
# MODEL
# -----------------------------
class DummyModel:
    def predict(self, df):
        return [1 if df['rainfall'].iloc[0] > 80 else 0]
    def predict_proba(self, df):
        r = df['rainfall'].iloc[0]
        p = min(r/120, 0.99)
        return [[1-p, p]]

try:
    model = pickle.load(open("cloudburst_model.pkl","rb"))
except:
    model = DummyModel()

# -----------------------------
# LOCATIONS
# -----------------------------
if "locs" not in st.session_state:
    st.session_state.locs = {
        "Mandi": (31.59,76.92),
        "Shimla": (31.10,77.17),
        "Kullu": (31.96,77.11)
    }

# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.title("🌍 Control Panel")

selected = st.sidebar.multiselect(
    "Select Locations",
    list(st.session_state.locs.keys()),
    default=["Mandi","Shimla"]
)

city = st.sidebar.text_input("Add City")

if st.sidebar.button("Add City"):
    if city:
        try:
            geo = requests.get(
                f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1",
                timeout=5
            ).json()

            if "results" in geo:
                lat = geo["results"][0]["latitude"]
                lon = geo["results"][0]["longitude"]
                st.session_state.locs[city] = (lat, lon)
                st.sidebar.success("Added")
            else:
                st.sidebar.error("City not found")

        except:
            st.sidebar.error("API Error")

# -----------------------------
# WEATHER
# -----------------------------
def get_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=precipitation"

        d = requests.get(url, timeout=5).json()

        temp = d.get("current_weather", {}).get("temperature", 25)
        wind = d.get("current_weather", {}).get("windspeed", 5)

        rain = 0
        if "hourly" in d and "precipitation" in d["hourly"]:
            rain = max(d["hourly"]["precipitation"])

        return rain, temp, wind

    except Exception:
        return 0, 25, 5
        temp = d["current_weather"]["temperature"]
        wind = d["current_weather"]["windspeed"]

        return rain, temp, wind

    except:
        return 0, 25, 5

# -----------------------------
# PREDICTION SAFE
# -----------------------------
def predict(df):
    pred = model.predict(df)[0]

    try:
        p = model.predict_proba(df)[0]
        prob = p[1] if len(p) > 1 else p[0]
    except:
        prob = 1.0 if pred else 0.0

    return pred, prob

# -----------------------------
# HEADER
# -----------------------------
st.title("🌧 Downpour Defender PRO MAX")

# -----------------------------
# DASHBOARD
# -----------------------------
for loc in selected:

    lat, lon = st.session_state.locs[loc]

    rain, temp, wind = get_weather(lat, lon)

    df = pd.DataFrame({
        "rainfall":[rain],
        "temperature":[temp],
        "windspeed":[wind]
    })

    pred, prob = predict(df)

    st.subheader(f"📍 {loc}")

    c1,c2,c3,c4 = st.columns(4)

    c1.markdown(f'<div class="card">🌧 Rain<br><b>{rain:.1f}</b></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="card">🌡 Temp<br><b>{temp:.1f}</b></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="card">💨 Wind<br><b>{wind:.1f}</b></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="card">⚠ Risk<br><b>{"HIGH" if pred else "LOW"}</b></div>', unsafe_allow_html=True)

    # GAUGE
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=prob*100,
        title={'text':"Cloudburst %"},
        gauge={'axis':{'range':[0,100]}}
    ))

    st.plotly_chart(fig, key=f"chart_{loc}")

    # LANDSLIDE
    if rain > 80:
        st.error("🚨 HIGH LANDSLIDE RISK")
    elif rain > 40:
        st.warning("⚠ Moderate Risk")
    else:
        st.success("✅ Safe Travel")

    # MAP (FIXED PYDECK)
    map_df = pd.DataFrame({
        "lat":[lat],
        "lon":[lon]
    })

    st.pydeck_chart(pdk.Deck(
        initial_view_state=pdk.ViewState(
            latitude=lat,
            longitude=lon,
            zoom=8
        ),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=map_df,
                get_position="[lon, lat]",
                get_fill_color=[255,0,0],
                get_radius=5000
            )
        ]
    ))
       # TELEGRAM TIMER
    if "last_sent" not in st.session_state:
        st.session_state.last_sent = 0

    # Check cooldown (30 minutes = 1800 seconds)
    if time.time() - st.session_state.last_sent > 1800:

        # Define risk
        if rain > 80:
            risk = "HIGH"
        elif rain > 40:
            risk = "MODERATE"
        else:
            risk = "LOW"

        # Send only risk
        send_telegram(f"⚠ {loc} Cloudburst Risk: {risk}")

        # Update last sent time
        st.session_state.last_sent = time.time()
# -----------------------------
# CHATBOT
# -----------------------------
st.header("🤖 Local AI Assistant")

qa = {
    "cloudburst":"Heavy sudden rainfall.",
    "landslide":"Occurs due to heavy rain.",
    "safe":"Avoid travel in heavy rainfall.",
    
    "what is cloudburst": "A cloudburst is sudden, heavy rainfall in a short time causing floods.",
    "what causes cloudburst": "Cloudbursts are caused by intense upward air currents and moisture accumulation.",
    "where do cloudbursts occur": "They mostly occur in mountainous regions like Himachal Pradesh.",
    "what is landslide": "A landslide is the movement of rock, soil, or debris down a slope.",
    "what causes landslides": "Heavy rainfall, earthquakes, and slope instability cause landslides.",
    "is rain dangerous": "Heavy rain can cause floods, landslides, and road accidents.",
    "what is safe rainfall level": "Rainfall below 40 mm/hr is generally considered safe.",
    "what is high rainfall": "Rainfall above 80 mm/hr is considered dangerous.",
    "what is moderate rainfall": "Rainfall between 40–80 mm/hr is moderate risk.",
    "how to stay safe in rain": "Avoid travel, stay indoors, and monitor alerts.",
    "what to do during landslide": "Move to higher ground and avoid slopes immediately.",
    "can cloudburst be predicted": "Cloudbursts are difficult to predict but weather data helps estimate risk.",
    "what is wind speed": "Wind speed measures how fast air is moving.",
    "does wind affect rain": "Yes, strong winds can intensify storms.",
    "what is temperature role": "Temperature affects moisture and storm formation.",
    "is himachal prone to landslides": "Yes, due to hilly terrain and heavy monsoon rains.",
    "what is safe travel condition": "Low rainfall and stable weather are safe for travel.",
    "when should i avoid travel": "Avoid travel during heavy rain or landslide warnings.",
    "what is disaster management": "It involves planning and response to natural disasters.",
    "what is flood": "Flood is overflow of water covering land areas.",
    "how to prevent landslides": "Plant trees, improve drainage, and avoid slope cutting.",
    "what is weather forecast": "It predicts future atmospheric conditions.",
    "what is rainfall measurement": "Rainfall is measured in millimeters (mm).",
    "what is humidity": "Humidity is the amount of moisture in air.",
    "how to prepare for rain": "Carry essentials, avoid risky areas, and stay informed.",
    "what is emergency alert": "A warning message for dangerous situations.",
    "why roads become unsafe": "Water weakens soil causing landslides and road damage.",
    "what is safe zone": "An area with low disaster risk.",
    "what is red zone": "An area with high disaster risk.",
 "what is weather forecast": "It predicts future atmospheric conditions.",
"what is rainfall": "It is the amount of precipitation falling as rain.",
"what is cloudburst": "It is sudden heavy rainfall in a short time.",
"what is humidity": "It is the amount of water vapor in the air.",
"what is temperature": "It measures how hot or cold the air is.",
"what is wind speed": "It is the rate at which air is moving.",
"what is atmospheric pressure": "It is the force exerted by air on the earth.",
"what is precipitation": "It includes rain, snow, sleet, or hail.",
"what is a storm": "It is a violent weather condition with wind and rain.",
"what is a flood": "It is overflow of water covering land.",
"what is drought": "It is a long period of low rainfall.",
"what is thunderstorm": "It is a storm with thunder and lightning.",
"what is lightning": "It is a sudden electrical discharge in the atmosphere.",
"what is climate": "It is the long-term weather pattern of a region.",
"what is weather": "It is the day-to-day condition of the atmosphere.",
"what is fog": "It is a thick cloud near the ground.",
"what is dew": "It is water droplets formed from condensation.",
"what is evaporation": "It is the process of liquid turning into vapor.",
"what is condensation": "It is vapor turning into liquid.",
"what is water cycle": "It is the continuous movement of water on earth.",
"what is cyclone": "It is a large rotating storm system.",
"what is hurricane": "It is a strong tropical storm with high winds.",
"what is tornado": "It is a violently rotating column of air.",
"what is monsoon": "It is seasonal wind bringing heavy rain.",
"what is heatwave": "It is a prolonged period of high temperature.",
"what is cold wave": "It is a period of extremely low temperature.",
"what is barometer": "It measures atmospheric pressure.",
"what is hygrometer": "It measures humidity.",
"what is thermometer": "It measures temperature.",
"what is anemometer": "It measures wind speed.",
"what is rain gauge": "It measures rainfall amount.",
"what is satellite weather": "It uses satellites to observe weather.",
"what is radar weather": "It detects precipitation using radio waves.",
"what is cloud formation": "It is formation of clouds from condensation.",
"what is cumulonimbus cloud": "It is a cloud associated with storms.",
"what is cirrus cloud": "It is a thin high-altitude cloud.",
"what is stratus cloud": "It is a low, gray cloud layer.",
"what is fog formation": "It occurs when air cools to dew point.",
"what is dew point": "It is temperature at which condensation occurs.",
"what is solar radiation": "It is energy from the sun.",
"what is greenhouse effect": "It traps heat in earth’s atmosphere.",
"what is global warming": "It is increase in earth’s temperature.",
"what is climate change": "It is long-term change in climate patterns.",
"what is flash flood": "It is sudden flooding due to heavy rain.",
"what is cloud seeding": "It is artificial rain enhancement method.",
"what is jet stream": "It is fast-flowing air current in atmosphere.",
"what is weather station": "It is a place to record weather data.",
"what is meteorology": "It is the study of weather.",
"what is forecast model": "It predicts weather using data.",
"what is cloudburst": "It is a sudden and very heavy rainfall over a small area in a short time.",
"what causes cloudburst": "It is caused by intense upward air movement and moisture condensation in clouds.",
"what is rainfall intensity": "It is the amount of rain that falls in a specific time period.",
"what is humidity": "It is the amount of water vapor present in the air.",
"what is atmospheric pressure": "It is the force exerted by air on the Earth's surface.",
"what is temperature in weather": "It is the measure of how hot or cold the atmosphere is.",
"what is thunderstorm": "It is a storm with lightning, thunder, heavy rain, and strong winds.",
"what is lightning": "It is a sudden electric discharge in the atmosphere.",
"what is thunder": "It is the sound caused by lightning heating the air rapidly.",
"what is monsoon": "It is a seasonal wind system that brings heavy rainfall.",
"what is rainfall": "It is the precipitation of water from clouds to Earth.",
"what is precipitation": "It is any form of water falling from clouds like rain, snow, or hail.",
"what is cloud formation": "It is the process where water vapor condenses into clouds.",
"what is condensation": "It is the process where water vapor changes into liquid water droplets.",
"what is water cycle": "It is the continuous movement of water between Earth and atmosphere.",
"what is evaporation": "It is the process where water changes into vapor due to heat.",
"what is convection": "It is the upward movement of warm air that helps cloud formation.",
"what is wind": "It is the movement of air from high pressure to low pressure.",
"what is wind speed": "It is the rate at which air moves in the atmosphere.",
"what is wind direction": "It is the direction from which wind is coming.",
"what is weather forecasting": "It is the prediction of future weather conditions.",
"what is radar in weather": "It is a system used to detect rain and storm movement.",
"what is satellite in weather": "It is used to observe clouds and weather patterns from space.",
"what is flood": "It is an overflow of water onto normally dry land.",
"what is landslide": "It is the movement of soil and rocks down a slope.",
"what is soil saturation": "It is the condition when soil is fully filled with water.",
"what is runoff": "It is water flowing over land after heavy rainfall.",
"what is drainage system": "It is a system that removes excess water from land.",
"what is weather warning": "It is an alert issued for dangerous weather conditions.",
"what is disaster management": "It is planning and response to reduce damage from disasters.",
"what is humidity level": "It is the percentage of moisture in the air.",
"what is cloud cover": "It is the fraction of sky covered by clouds.",
"what is cumulonimbus cloud": "It is a tall cloud that produces heavy rain and storms.",
"what is atmospheric instability": "It is a condition that supports rapid cloud growth and storms.",
"what is orographic rainfall": "It is rainfall caused when air rises over mountains.",
"what is convectional rainfall": "It is rainfall caused by heating of the Earth's surface.",
"what is frontal rainfall": "It is rainfall caused when two air masses meet.",
"what is air mass": "It is a large body of air with uniform temperature and humidity.",
"what is climate": "It is the long-term pattern of weather in a region.",
"what is weather": "It is the day-to-day condition of the atmosphere.",
"what is extreme rainfall": "It is unusually heavy rainfall in a short time.",
"what is flash flood": "It is sudden flooding caused by heavy rainfall in a short time.",
"what is rainfall measurement": "It is the process of measuring rain using a rain gauge.",
"what is rain gauge": "It is an instrument used to measure rainfall.",
"what is humidity sensor": "It is a device used to measure moisture in air.",
"what is pressure drop": "It is a sudden decrease in atmospheric pressure often linked to storms.",
"what is storm": "It is a disturbed weather condition with strong winds and rain.",
"what is cloudburst prediction": "It is the forecasting of sudden heavy rainfall events.",
"what is weather station": "It is a system that collects weather data like temperature and rain.",
"what is data logging in weather": "It is recording weather data over time for analysis.",
"what is sensor in weather system": "It is a device that measures environmental conditions.",
"what is Arduino weather project": "It is a project using Arduino to monitor weather parameters.",
"what is IoT weather monitoring": "It is using internet-connected devices to track weather conditions.",
"what is alert system in disaster": "It is a system that warns people about upcoming hazards.",
"what is SMS alert system": "It is a system that sends warnings through mobile messages.",
"what is WhatsApp alert system": "It is a system that sends alerts through WhatsApp messages.",
"what is cloudburst": "It is a sudden and very heavy rainfall over a small area in a short time.",
"define rainfall intensity": "It is the amount of rain that falls in a specific time period.",
"explain humidity": "It is the amount of water vapor present in the air.",
"why is temperature important in cloudburst prediction": "It is the measure of how hot or cold the atmosphere is.",
"how does wind speed affect weather": "It is the rate at which air moves in the atmosphere.",
"what is atmospheric pressure": "It is the force exerted by air on the Earth's surface.",
"define thunderstorm": "It is a storm with lightning, thunder, heavy rain, and strong winds.",
"explain flood": "It is an overflow of water onto normally dry land.",
"why is flash flood important in cloudburst prediction": "It is sudden flooding caused by heavy rainfall in a short time.",
"how does cloud formation affect weather": "It is the process where water vapor condenses into clouds.",
"what is rain gauge": "It is an instrument used to measure rainfall.",
"define weather forecasting": "It is the prediction of future weather conditions.",
"explain IoT weather monitoring": "It is using internet-connected devices to track weather conditions.",
"why is Arduino weather project important in cloudburst prediction": "It is a project using Arduino to monitor weather parameters.",
"how does alert system affect weather": "It is a system that warns people about dangerous weather conditions.",
"what is soil moisture": "It is the amount of water present in soil.",
"define runoff": "It is water flowing over land after heavy rainfall.",
"explain drainage system": "It is a system that removes excess water from land.",
"why is satellite monitoring important in cloudburst prediction": "It is observing weather conditions using satellites.",
"how does radar monitoring affect weather": "It is detecting rain and storm movement using radar systems.",
"what is orographic lift": "It is the process of air being forced upward by rising terrain like mountains.",
"define cumulonimbus": "It is a dense, towering vertical cloud associated with thunderstorms.",
"explain dew point": "It is the temperature at which air becomes saturated with water vapor.",
"what is an ultrasonic sensor": "It is a device used to measure water levels using sound waves.",
"define an anemometer": "It is a tool used to measure the speed and direction of wind.",
"explain hygrometer": "It is an instrument used to measure the humidity of the air.",
"what is moisture advection": "It is the horizontal transport of moisture by the wind.",
"define atmospheric instability": "It is a condition where air continues to rise after being nudged upward.",
"explain microburst": "It is an intense localized downdraft within a thunderstorm.",
"what is vertical wind shear": "It is the change in wind speed or direction at different altitudes.",
"define precipitation": "It is any product of the condensation of atmospheric water vapor that falls under gravity.",
"explain convective rainfall": "It is precipitation caused by the rising of warm, moist air.",
"what is a barometer": "It is an instrument that detects changes in atmospheric pressure.",
"define saturation point": "It is the stage where air cannot hold any more water vapor.",
"explain catchment area": "It is the land area where rainfall collects and drains into a river.",
"what is a landslide sensor": "It is a device that detects movement or shifts in soil and rock.",
"define peak discharge": "It is the maximum flow rate of water during a flood event.",
"explain storm surge": "It is a rising of the sea as a result of atmospheric pressure changes.",
"what is an ESP8266 module": "It is a low-cost Wi-Fi chip used for IoT weather stations.",
"define seismic vibration": "It is a shaking of the ground caused by sudden energy release.",
"explain water level monitoring": "It is the continuous tracking of water height in reservoirs.",
"what is a DHT11 sensor": "It is a basic sensor used to measure temperature and humidity.",
"define debris flow": "It is a fast-moving mixture of water, soil, and rock fragments.",
"explain cloud electrification": "It is the process by which clouds gain an electrical charge.",
"what is a tipping bucket": "It is a mechanism in rain gauges that tips when full to measure rain.",
"define topsoil saturation": "It is the state when soil pores are completely filled with water.",
"explain real-time data": "It is information that is delivered immediately after collection.",
"what is a threshold value": "It is the specific limit that triggers an automated alert system.",
"define cloudburst duration": "It is the length of time an intense rainfall event lasts.",
"explain weather telemetry": "It is the wireless transmission of data from weather sensors.",
"what is a heat island": "It is an urban area that is significantly warmer than surrounding rural areas.",
"define an ADXL345 sensor": "It is an accelerometer used for motion and vibration detection.",
"explain data logging": "It is the process of recording sensor measurements over time.",
"what is a cloudburst cell": "It is the specific core of a storm where the heaviest rain occurs.",
"define an automated floodgate": "It is a barrier that opens or closes based on water level sensors.",
"explain cloud seeding": "It is the practice of adding substances to clouds to encourage rain.",
"what is a buzzer alert": "It is an audible signal used to warn people of immediate danger.",
"define vapor pressure": "It is the pressure exerted by water vapor in the atmosphere.",
"explain updraft intensity": "It is the strength of rising air currents in a storm.",
"what is a GSM module": "It is a hardware component used to send SMS alerts.",
"define a rain shadow": "It is a region having little rainfall because it is sheltered by hills.",
"explain condensation nuclei": "It is small particles on which water vapor condenses to form clouds.",
"what is an IoT gateway": "It is a bridge that connects local sensors to the internet.",
"define latent heat": "It is energy released or absorbed during a phase change of water.",
"explain precipitable water": "It is the total atmospheric water vapor in a vertical column.",
"what is an isobar": "It is a line on a map connecting points of equal barometric pressure.",
"define a drainage basin": "It is an area of land where all flowing water converges to a single point.",
"explain a stepper motor": "It is a motor used to control the movement of physical models.",
"what is water turbidity": "It is the cloudiness of a fluid caused by individual particles.",
"define a pH sensor": "It is a device used to measure the acidity or alkalinity of water.",
"explain Blynk platform": "It is an IoT tool used to visualize and control hardware data.",
"what is cloudbase": "It is the lowest altitude of the visible portion of a cloud.",
"define a gust front": "It is the leading edge of cool air rushing down from a thunderstorm.",
"explain hydrograph": "It is a graph showing the rate of flow versus time at a specific point.",
"what is an anemograph": "It is an instrument that records a continuous log of wind speed.",
"define a weather vane": "It is a revolving pointer that shows the direction of the wind.",
"explain flash flood warning": "It is an official notice that a flash flood is imminent.",
"what is a squall line": "It is a narrow band of high winds and storms.",
"define a supercell": "It is a system producing severe thunderstorms and rotating updrafts.",
"explain pluviograph": "It is a rain gauge that provides a continuous record of rainfall.",
"what is an automated weather station": "It is a version of a weather station that saves manual labor.",
"define a moisture tongue": "It is an extension of moist air into a region of dry air.",
"explain a cold front": "It is the boundary of an advancing mass of cold air.",
"what is a warm front": "It is the boundary of an advancing mass of warm air.",
"define a storm cell": "It is an air mass that contains up and down drafts in a loop.",
"explain rain-bearing clouds": "It is clouds such as nimbostratus that carry significant moisture.",
"what is a microclimate": "It is the weather conditions of a specific small area.",
"define an altimeter": "It is an instrument used to measure the altitude of an object.",
"explain a psychrometer": "It is a type of hygrometer used to measure relative humidity.",
"what is a lightning rod": "It is a metal rod that protects structures from lightning strikes.",
"define an evapo-transpiration": "It is the process by which water is transferred from land to the atmosphere.",
"explain a cloudburst alert": "It is a notification triggered by extreme rainfall data.",
"what is a solenoid valve": "It is an electrically controlled valve used to manage water flow.",
"define a pressure sensor": "It is a device that senses pressure and converts it into a signal.",
"explain an LCD display": "It is a flat-panel display used to output sensor readings.",
"what is a breadboard": "It is a construction base for prototyping electronic circuits.",
"what is precipitation rate": "It is speed of rainfall occurrence.",   "who should monitor weather": "Everyone, especially travelers and residents in risky areas."
}


def answer(q):
    q = q.lower()
    for k in qa:
        if k in q:
            return qa[k]
    return "I don't know yet."

if "chat" not in st.session_state:
    st.session_state.chat = []

for role, msg in st.session_state.chat:
    with st.chat_message(role):
        st.write(msg)
if prompt := st.chat_input("Ask anything..."):
    st.session_state.chat.append(("user", prompt))
    reply = answer(prompt)
    st.session_state.chat.append(("assistant", reply))

    with st.chat_message("assistant"):
        st.write(reply)

# -----------------------------
# FOOTER
# -----------------------------
st.markdown("---")
st.write("DEVELOPED BY ANSH THAKUR ,PIYUSH SHARMA and HEMANT KUMAR")
