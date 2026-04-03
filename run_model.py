import pickle
import pandas as pd

# load model
model = pickle.load(open("cloudburst_model.pkl","rb"))

print("Cloudburst Prediction Test")

rainfall = float(input("Rainfall (mm): "))
temperature = float(input("Temperature (°C): "))
windspeed = float(input("Wind Speed (km/h): "))

input_data = pd.DataFrame({
    "rainfall":[rainfall],
    "temperature":[temperature],
    "windspeed":[windspeed]
})

prediction = model.predict(input_data)

if rainfall > 100 or prediction[0] == 1:
    print("⚠️ CLOUD BURST ALERT")
else:
    print("✅ Weather Normal")