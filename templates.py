"""
Template strings for the UI components of the EventPro AI application
"""
import json


def get_about_content():
    """Return HTML content for the About tab"""
    return """
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


def get_sidebar_content():
    """Return HTML content for the sidebar"""
    return {
        "help_text": """
        ### How to use EventPro AI
        1. Enter your OpenAI API key
        2. Fill out the event details form
        3. Click "Plan My Event" to get recommendations
        4. Review weather, venues, and AI recommendations
        """,

        "examples": """
        ### Examples
        - "Plan a wedding in Paris for next Saturday"
        - "I need a venue for a corporate meeting in New York this Friday"
        - "Find places for a birthday party in London next weekend"
        """
    }


def get_event_details_card(event_type, location, date_str):
    """Return HTML for the event details card"""
    return f"""
    <div class="info-box">
    <p><strong>🎪 Event Type:</strong> {event_type}</p>
    <p><strong>📍 Location:</strong> {location}</p>
    <p><strong>📅 Date:</strong> {date_str}</p>
    </div>
    """


def get_weather_card(weather_data):
    """Return HTML for the weather card"""
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


def get_venue_card(venue):
    """Return HTML for the venue card"""
    return f"""
    <div class="venue-card">
    <h3>{venue.name}</h3>
    <p><strong>Address:</strong> {venue.address}</p>
    <p><strong>Rating:</strong> {venue.rating}</p>
    <p><strong>Suitability Score:</strong> {venue.suitability_score}/10</p>
    <p><em>{venue.details}</em></p>
    </div>
    """


def get_recommendation_box(recommendation):
    """Return HTML for the recommendation box"""
    return f"""
    <div class="recommendation-box">
    {recommendation}
    </div>
    """