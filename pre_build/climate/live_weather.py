import os
import requests

def fetch_live_air_quality(lat: float, lon: float, anomaly_type: str = None, city: str = "Dallas") -> dict:
    """
    Fetches real-time Air Quality data (AQI and Pollutants) from Google Maps Air Quality API.
    """
    if anomaly_type:
        if city == "New Delhi":
            if anomaly_type == "respiratory":
                return {"aqi": 340, "dominant": "PM2.5", "category": "Hazardous", "custom_alert": "Severe Stubble Burning Smog"}
            elif anomaly_type == "cardiovascular":
                return {"aqi": 180, "dominant": "Ozone", "category": "Unhealthy", "custom_alert": "Extreme Pre-Monsoon Heatwave (45°C) & High Ozone"}
            elif anomaly_type == "metabolic":
                return {"aqi": 90, "dominant": "PM10", "category": "Moderate", "custom_alert": "Severe Monsoon Flooding (Waterlogging & Infection Risk)"}
        else: # Dallas
            if anomaly_type == "respiratory":
                return {"aqi": 165, "dominant": "PM2.5", "category": "Unhealthy", "custom_alert": "Wildfire Plume from Panhandle"}
            elif anomaly_type == "cardiovascular":
                return {"aqi": 110, "dominant": "Ozone", "category": "Unhealthy for Sensitive Groups", "custom_alert": "Extreme Heat Dome (108°F)"}
            elif anomaly_type == "metabolic":
                return {"aqi": 80, "dominant": "None", "category": "Moderate", "custom_alert": "ERCOT Power Grid Alert (Rolling Blackouts Risk)"}

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        print("[Live Climate] Warning: No GOOGLE_MAPS_API_KEY found. Using fallback data.")
        return {"aqi": 85, "dominant": "PM2.5", "category": "Moderate"}

    url = f"https://airquality.googleapis.com/v1/currentConditions:lookup?key={api_key}"
    
    payload = {
        "location": {
            "latitude": lat,
            "longitude": lon
        },
        "extraComputations": [
            "POLLUTANT_ADDITIONAL_INFO"
        ]
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        indexes = data.get("indexes", [])
        if not indexes:
            return {"aqi": 50, "dominant": "None", "category": "Good"}
            
        primary_index = indexes[0]
        aqi_value = primary_index.get("aqi", 50)
        category = primary_index.get("category", "Good")
        dominant = primary_index.get("dominantPollutant", "PM2.5")
        
        return {
            "aqi": aqi_value,
            "dominant": dominant,
            "category": category
        }
    except Exception as e:
        print(f"[Live Climate] API Error: {e}. Falling back to default.")
        return {"aqi": 85, "dominant": "PM2.5", "category": "Moderate"}

def generate_climate_anomaly_string(aqi_data: dict) -> str:
    """
    Converts live AQI data into a human-readable anomaly string for Gemini.
    """
    if "custom_alert" in aqi_data:
        return f"CRITICAL ENVIRONMENTAL ALERT: {aqi_data['custom_alert']} (AQI: {aqi_data['aqi']} - {aqi_data['category']})"
    if aqi_data["aqi"] > 100:
        return f"live Air Quality Index of {aqi_data['aqi']} ({aqi_data['category']}) with high {aqi_data['dominant']}"
    else:
        return f"moderate Air Quality Index of {aqi_data['aqi']} with {aqi_data['dominant']}"
