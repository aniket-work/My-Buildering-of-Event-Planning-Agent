# Weather condition codes mapping
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Light rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with light hail",
    99: "Thunderstorm with heavy hail"
}

# CSS styles for the application
CSS_STYLES = """
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2563EB;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #EFF6FF;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .weather-card {
        background-color: #F0F9FF;
        border-left: 4px solid #0EA5E9;
        padding: 15px;
        margin-bottom: 15px;
    }
    .venue-card {
        background-color: #F8FAFC;
        border-left: 4px solid #8B5CF6;
        padding: 15px;
        margin-bottom: 10px;
    }
    .recommendation-box {
        background-color: #ECFDF5;
        border-radius: 8px;
        border: 1px solid #10B981;
        padding: 20px;
        margin-top: 20px;
    }
</style>
"""

# Help text for the sidebar
SIDEBAR_HELP = {
    "usage": [
        "1. Enter your OpenAI API key",
        "2. Fill out the event details form",
        "3. Click \"Plan My Event\" to get recommendations",
        "4. Review weather, venues, and AI recommendations"
    ],
    "examples": [
        "- \"Plan a wedding in Paris for next Saturday\"",
        "- \"I need a venue for a corporate meeting in New York this Friday\"",
        "- \"Find places for a birthday party in London next weekend\""
    ]
}

# About page content
ABOUT_CONTENT = """
## About EventPro AI Planner

EventPro AI Planner is an intelligent assistant that helps you plan your events with ease. The app uses artificial intelligence to:

- Analyze weather conditions for your event date
- Find suitable venues based on your event type and location
- Provide personalized recommendations and planning advice
- Consider special requirements and constraints

### How It Works

1. Our AI engine extracts key information from your event query
2. It checks real-time weather forecasts for your location and date
3. It searches for and analyzes potential venues
4. Based on all gathered information, it generates a comprehensive recommendation

### Data Sources

- Weather data: Open-Meteo API
- Venue information: Web search results

### Privacy

Your event details are used only for processing your request and are not stored permanently.
"""