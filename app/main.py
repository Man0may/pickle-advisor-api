import requests
from datetime import datetime, timezone
from flask import Flask, jsonify, request

app = Flask(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def calculate_playability(temperature_f, wind_mph, precip_probability, dewpoint_f):
    """Calculate pickleball playability score (1-10) based on weather conditions."""
    # Temperature score (2x weight): peak at 72-76F, penalty outside
    if 72 <= temperature_f <= 76:
        temp_score = 10
    elif 60 <= temperature_f <= 90:
        temp_score = 10 - (min(abs(temperature_f - 74), 16) / 16) * 6
    elif 40 <= temperature_f < 60:
        temp_score = 4 - ((60 - temperature_f) / 20) * 3
    elif temperature_f > 90:
        temp_score = 4 - ((temperature_f - 90) / 23) * 3
    else:
        temp_score = 1

    # Wind score (2x weight): 10 up to 8 mph, ramp down to 1 at 25 mph
    if wind_mph <= 8:
        wind_score = 10
    elif wind_mph >= 25:
        wind_score = 1
    else:
        wind_score = 10 - ((wind_mph - 8) / 17) * 9

    # Precipitation score (2x weight): penalty starts at 15%, severe above 50%
    if precip_probability <= 15:
        precip_score = 10
    elif precip_probability >= 80:
        precip_score = 1
    else:
        precip_score = 10 - ((precip_probability - 15) / 65) * 9

    # Dewpoint/humidity score (1x weight): lower dewpoint is better
    if dewpoint_f <= 55:
        humidity_score = 10
    elif dewpoint_f >= 75:
        humidity_score = 1
    else:
        humidity_score = 10 - ((dewpoint_f - 55) / 20) * 9

    # Weighted average: temp(2x) + wind(2x) + precip(2x) + humidity(1x)
    total = (temp_score * 2 + wind_score * 2 + precip_score * 2 + humidity_score * 1) / 7
    return round(max(1, min(10, total)), 1)


def get_recommendation(score):
    """Return a Phineas-and-Ferb-style recommendation based on score."""
    if score >= 8:
        return "Ferb, I know what we're gonna do today! Perfect pickleball weather!"
    elif score >= 6:
        return "Hey Ferb, grab the paddles! Decent conditions out there."
    elif score >= 4:
        return "Ferb, maybe we should build something indoors first..."
    else:
        return "Aren't you a little young to be playing in this weather? Stay inside!"

@app.route("/score")
def score():
    latitude = request.args.get("latitude")
    longitude = request.args.get("longitude")

    if not latitude or not longitude:
        return jsonify({"error": "latitude and longitude query parameters are required"}), 400

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except ValueError:
        return jsonify({"error": "latitude and longitude must be numeric"}), 400

    # Fetch current weather from Open-Meteo
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,wind_speed_10m,precipitation_probability,dew_point_2m",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
    }

    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return jsonify({"error": f"Weather API request failed: {str(e)}"}), 502

    weather_data = response.json()
    current = weather_data.get("current", {})

    temperature_f = current.get("temperature_2m", 70)
    wind_mph = current.get("wind_speed_10m", 0)
    precip_probability = current.get("precipitation_probability", 0)
    dewpoint_f = current.get("dew_point_2m", 50)

    playability = calculate_playability(temperature_f, wind_mph, precip_probability, dewpoint_f)
    recommendation = get_recommendation(playability)

    return jsonify({
        "playability_score": playability,
        "recommendation": recommendation,
        "weather": {
            "temperature_f": temperature_f,
            "wind_mph": wind_mph,
            "precipitation_probability_pct": precip_probability,
            "dewpoint_f": dewpoint_f,
        },
        "location": {
            "latitude": latitude,
            "longitude": longitude,
        },
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/")
def index():
    return jsonify({
        "service": "Pickleball Playability Advisor",
        "usage": "GET /score?latitude=38.89&longitude=-77.03",
        "health": "GET /health",
    })