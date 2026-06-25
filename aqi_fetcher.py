import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAQ_API_KEY")
HEADERS = {"X-API-Key": api_key}


def get_coordinates(city):
    res = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": city, "format": "json", "limit": 1},
        headers={"User-Agent": "urban-health-assistant"},
        timeout=5
    ).json()
    if not res:
        return None, None
    return float(res[0]["lat"]), float(res[0]["lon"])


def get_locations(lat, lon, radius=25000):
    res = requests.get(
        "https://api.openaq.org/v3/locations",
        headers=HEADERS,
        params={"coordinates": f"{lat},{lon}", "radius": radius, "limit": 20},
        timeout=10
    )
    if res.status_code != 200:
        return []
    return res.json().get("results", [])


def get_latest_measurement(sensor_id):
    res = requests.get(
        f"https://api.openaq.org/v3/sensors/{sensor_id}/measurements",
        headers=HEADERS,
        params={"limit": 1, "order_by": "datetime", "sort_order": "desc"},
        timeout=10
    )
    if res.status_code != 200:
        return None
    results = res.json().get("results", [])
    return results[0].get("value") if results else None


def health_advice(param, value):
    if param == "pm25":
        if value <= 12:
            return "Good", "green"
        elif value <= 35:
            return "Moderate", "orange"
        elif value <= 55:
            return "Unhealthy for Sensitive Groups", "orange"
        else:
            return "Unhealthy", "red"
    elif param == "pm10":
        if value <= 54:
            return "Good", "green"
        elif value <= 154:
            return "Moderate", "orange"
        else:
            return "Unhealthy", "red"
    return None, None


# Each disease carries a multiplier that raises the effective risk score,
# plus a warning shown to the user when that condition is selected.
DISEASE_RISK = {
    "Asthma": {
        "factor": 1.8,
        "warning": "Asthma greatly increases PM2.5 sensitivity. "
                   "Carry your inhaler at all times and avoid outdoor "
                   "exposure when AQI exceeds 100.",
    },
    "COPD": {
        "factor": 1.9,
        "warning": "COPD makes you highly vulnerable. Even moderate AQI can "
                   "trigger exacerbations. Stay indoors and use air purifiers "
                   "when AQI exceeds 50.",
    },
    "Heart disease": {
        "factor": 1.7,
        "warning": "Air pollution increases cardiac event risk. Avoid exertion "
                   "outdoors above AQI 100. Monitor for chest tightness.",
    },
    "Hypertension": {
        "factor": 1.4,
        "warning": "Pollution can spike blood pressure. Monitor readings closely "
                   "on high AQI days and reduce physical strain.",
    },
    "Diabetes": {
        "factor": 1.3,
        "warning": "Diabetics face increased systemic inflammation from particulates. "
                   "Maintain medication adherence and watch for unusual fatigue.",
    },
    "Allergies": {
        "factor": 1.5,
        "warning": "Airborne particulates worsen allergic reactions. Take "
                   "antihistamines preventively and limit outdoor time during "
                   "peak pollution hours.",
    },
    "Sinusitis": {
        "factor": 1.4,
        "warning": "Pollution directly irritates sinuses. Use saline nasal rinse "
                   "after outdoor exposure and consider an N95 mask.",
    },
    "Pregnancy": {
        "factor": 2.0,
        "warning": "Foetal exposure to pollution is linked to low birth weight and "
                   "preterm birth. Minimise outdoor time when AQI exceeds 75 and "
                   "ensure good indoor air quality.",
    },
}


def personalised_risk(pm25, age, activity_level, diseases):
    """
    Returns (risk_label, color_string).
    pm25: float or None
    age: int
    activity_level: 0=Low, 1=Moderate, 2=High
    diseases: list of selected disease strings
    """
    if pm25 is None:
        return "Unknown (no data)", "orange"

    score = pm25

    if age < 12 or age >= 65:
        score *= 1.3

    if activity_level == 2:
        score *= 1.2
    elif activity_level == 0:
        score *= 0.85

    for d in diseases:
        if d in DISEASE_RISK:
            score *= DISEASE_RISK[d]["factor"]

    if score < 30:
        return "Low", "green"
    elif score < 80:
        return "Moderate", "orange"
    elif score < 160:
        return "High", "red"
    else:
        return "Very High - take immediate precautions", "red"


def disease_warnings(diseases, pm25):
    """Returns warning strings for the selected diseases."""
    warnings = []
    for d in diseases:
        if d in DISEASE_RISK:
            warnings.append(DISEASE_RISK[d]["warning"])
    return warnings


def general_tips(pm25, age, activity_level):
    """Returns a list of plain-text tip strings."""
    tips = []
    if pm25 is None:
        tips.append("Could not retrieve pollution data. Check back later.")
        return tips

    if pm25 > 55:
        tips.append("Wear an N95 or FFP2 mask outdoors - PM2.5 is at harmful levels.")
    if pm25 > 35:
        tips.append(
            "Limit outdoor activity, especially between 12pm and 6pm "
            "when pollution typically peaks."
        )
    if pm25 <= 12:
        tips.append("Air quality is good - outdoor activities are safe for all groups.")

    if age >= 65 or age < 12:
        tips.append(
            "You are in a sensitive age group. Take extra precautions "
            "on any day with AQI above 50."
        )

    if activity_level == 2 and pm25 > 25:
        tips.append(
            "High activity level significantly increases your inhaled pollutant dose. "
            "Consider moving exercise indoors."
        )

    tips.append(
        "Stay well hydrated - drink 2-3 litres of water to support "
        "respiratory mucus clearance."
    )

    if pm25 > 35:
        tips.append("Keep windows closed and run an indoor HEPA air purifier if available.")

    return tips