import datetime
import json
import os
import requests
import yaml
import streamlit as st


def load_config():
    """Load configuration from config.json file"""
    with open('config.json', 'r') as f:
        return json.load(f)


def load_settings():
    """Load settings from settings.yaml file"""
    with open('settings.yaml', 'r') as f:
        return yaml.safe_load(f)


def load_constants():
    """Import constants from JavaScript file using PyExecJS"""
    try:
        # This is a simplified version - in a real app, you'd use PyExecJS or similar
        # to properly import from the JS file
        import execjs
        with open('constants.js', 'r') as f:
            js_code = f.read()
        ctx = execjs.compile(js_code)
        return ctx.eval('module.exports')
    except ImportError:
        # Fallback if execjs isn't available
        return {
            "WEATHER_CODES": {
                0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
                55: "Dense drizzle", 61: "Light rain", 63: "Moderate rain", 65: "Heavy rain",
                71: "Light snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Rain showers",
                81: "Moderate rain showers", 82: "Violent rain showers", 95: "Thunderstorm",
                96: "Thunderstorm with light hail", 99: "Thunderstorm with heavy hail",
            }
        }


def get_next_date(date_str):
    """Convert a date string to an actual date object"""
    date_str = date_str.lower().strip()
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    today = datetime.date.today()
    today_index = today.weekday()

    # Handle weekend cases
    if "weekend" in date_str:
        # Find the next Saturday
        days_to_saturday = (5 - today_index) % 7
        if "next" in date_str:
            # If it's already weekend, go to next weekend
            if today_index >= 5:  # If today is Saturday or Sunday
                days_to_saturday += 7
            # If explicitly asking for next weekend
            elif "next" in date_str:
                days_to_saturday += 7
        elif "this" in date_str:
            # Use the upcoming weekend
            pass

        return today + datetime.timedelta(days=days_to_saturday)

    # Handle other specific cases
    if date_str.startswith("next "):
        day_name = date_str[5:].strip()
        try:
            day_index = days.index(day_name)
            days_ahead = (day_index - today_index) % 7 or 7
            return today + datetime.timedelta(days=days_ahead)
        except ValueError:
            # If day name not found, return today as fallback
            return today
    elif date_str.startswith("this "):
        day_name = date_str[5:].strip()
        try:
            day_index = days.index(day_name)
            days_ahead = (day_index - today_index) % 7
            return today + datetime.timedelta(days=days_ahead)
        except ValueError:
            # If day name not found, return today as fallback
            return today
    elif date_str.startswith("today"):
        return today
    elif date_str.startswith("tomorrow"):
        return today + datetime.timedelta(days=1)
    else:
        try:
            day_name = date_str
            day_index = days.index(day_name)
            days_ahead = (day_index - today_index) % 7 or 7
            return today + datetime.timedelta(days=days_ahead)
        except ValueError:
            # Try to parse as YYYY-MM-DD
            try:
                return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                # Return today as fallback
                return today


def fetch_weather(location, date_str, weather_codes):
    """Fetch weather data for location and date"""
    config = load_config()
    target_date = get_next_date(date_str)

    try:
        # Geocoding request
        geocode_url = f"{config['api']['weather']['geocoding_url']}?name={location}&count=1&language=en&format=json"
        response = requests.get(geocode_url)
        if response.status_code != 200 or not response.json().get('results'):
            return f"📍 **{location}**: Weather data not available (location not found)", True

        result = response.json()['results'][0]
        latitude, longitude = result['latitude'], result['longitude']

        # Weather request
        weather_url = f"{config['api']['weather']['forecast_url']}?latitude={latitude}&longitude={longitude}&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto"
        response = requests.get(weather_url)

        if response.status_code != 200:
            return f"📍 **{location}**: Weather data not available (API error)", True

        data = response.json()['daily']
        target_date_str = target_date.strftime("%Y-%m-%d")

        if target_date_str in data['time']:
            index = data['time'].index(target_date_str)
            weather_code = data['weathercode'][index]
            max_temp = data['temperature_2m_max'][index]
            min_temp = data['temperature_2m_min'][index]
            precip_prob = data.get('precipitation_probability_max', [0] * len(data['time']))[index]

            description = weather_codes.get(weather_code, "Unknown")

            # Format a more detailed weather report
            weather_report = {
                "location": location,
                "date": target_date_str,
                "day_name": target_date.strftime("%A"),
                "description": description,
                "max_temp": max_temp,
                "min_temp": min_temp,
                "precipitation_probability": precip_prob,
                "weather_code": weather_code
            }

            return json.dumps(weather_report), True

        return f"📍 **{location}**: Weather forecast not available for {target_date_str}", True

    except Exception as e:
        return f"📍 **{location}**: Error fetching weather data: {str(e)}", True


def render_weather_card(weather_data):
    """Render a weather card in HTML format"""
    try:
        weather = json.loads(weather_data)
        return f"""
        <div class="weather-card">
        <h3>{weather['day_name']}, {weather['date']}</h3>
        <p><strong>Conditions:</strong> {weather['description']}</p>
        <p><strong>Temperature:</strong> {weather['min_temp']}°C to {weather['max_temp']}°C</p>
        <p><strong>Precipitation:</strong> {weather['precipitation_probability']}% chance</p>
        </div>
        """
    except:
        return f"""
        <div class="weather-card">
        {weather_data}
        </div>
        """


def render_venue_card(venue):
    """Render a venue card in HTML format"""
    return f"""
    <div class="venue-card">
    <h3>{venue.name}</h3>
    <p><strong>Address:</strong> {venue.address}</p>
    <p><strong>Rating:</strong> {venue.rating}</p>
    <p><strong>Suitability Score:</strong> {venue.suitability_score}/10</p>
    <p><em>{venue.details}</em></p>
    </div>
    """


def both_paths_complete(state):
    """Check if both parallel paths (weather and venues) are complete"""
    return state.get("weather_ready") and state.get("venues_ready")