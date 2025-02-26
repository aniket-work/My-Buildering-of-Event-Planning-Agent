import os
import json
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import HumanMessage

from models import QueryAnalysis, VenuesList, EventVenue
from utils import fetch_weather, load_constants, load_config

# Get configuration
config = load_config()
constants = load_constants()
weather_codes = constants.get("WEATHER_CODES", {})


def query_analyzer(state):
    """Extract location, date, and event type from user query"""
    messages = state['messages']
    user_query = messages[-1].content

    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY", "")

    try:
        # Initialize LLM with API key
        llm = ChatOpenAI(model=config["api"]["default_model"], api_key=api_key)

        prompt = f"""
Extract the following information from the user query:
- location: the city or place name
- date: the day of the week, including any modifiers like 'next' or 'this' (e.g., 'next Sunday', 'this Friday', 'this weekend', 'next weekend', or just 'Sunday')
- event: the type of event or occasion

Handle special date formats like 'weekend', 'this weekend', 'next weekend' appropriately.

User query: {user_query}
"""
        try:
            structured_llm = llm.with_structured_output(QueryAnalysis)
            analysis = structured_llm.invoke(prompt)
            return {"location": analysis.location, "date": analysis.date, "event": analysis.event}
        except Exception as e:
            # Fallback to manual extraction if structured format fails
            try:
                # Default emergency values
                event = config["default_values"]["event"]
                location = config["default_values"]["location"]
                date = config["default_values"]["date"]

                # Try to extract from the query
                if "in" in user_query and "for" in user_query:
                    parts = user_query.split("in")
                    if len(parts) > 1:
                        event_part = parts[0].strip().lower()
                        if "plan" in event_part:
                            event = event_part.split("plan")[-1].strip()
                        elif "an" in event_part:
                            event = event_part.split("an")[-1].strip()
                        elif "a" in event_part:
                            event = event_part.split("a")[-1].strip()

                        location_date_part = parts[1].strip()
                        if "for" in location_date_part:
                            loc_parts = location_date_part.split("for")
                            location = loc_parts[0].strip()
                            date = loc_parts[1].strip()

                return {"location": location, "date": date, "event": event}
            except:
                # Ultimate fallback
                return {
                    "location": config["default_values"]["location"],
                    "date": config["default_values"]["date"],
                    "event": config["default_values"]["event"]
                }
    except Exception as e:
        return {
            "location": config["default_values"]["location"],
            "date": config["default_values"]["date"],
            "event": config["default_values"]["event"]
        }


def weather_fetcher(state):
    """Fetch weather information for the event location and date"""
    location = state['location']
    date_str = state['date']

    weather_report, weather_ready = fetch_weather(location, date_str, weather_codes)
    return {"weather_report": weather_report, "weather_ready": weather_ready}


def event_planning_assistant(state):
    """Search for venues based on event type and location"""
    location = state['location']
    event = state['event']
    query = f"best venues for {event} in {location} with reviews and ratings"

    try:
        search_tool = DuckDuckGoSearchRun()
        search_result = search_tool.run(query)
        return {"search_result": search_result}
    except Exception as e:
        return {"search_result": f"Error searching for venues: {str(e)}"}


def venues_list_formatter(state):
    """Format venue search results into structured data"""
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY", "")

    # Initialize LLM with API key
    llm = ChatOpenAI(model=config["api"]["default_model"], api_key=api_key)

    search_result = state['search_result']
    event_type = state['event']

    prompt = f"""
Extract a list of venues from the following search result for a {event_type} event. 
For each venue, provide:
1. Name
2. Address
3. Details (including prices, capacity, or special features if available)
4. Rating (if available, otherwise "N/A")
5. Suitability score (from 1-10) based on how well it matches a {event_type} event

Search result: {search_result}

Limit to the {config.get('limits', {}).get('max_venues', 5)} most relevant venues.
"""
    try:
        structured_llm = llm.with_structured_output(VenuesList)
        result = structured_llm.invoke(prompt)
        return {"venues": result.venues, "venues_ready": True}
    except Exception as e:
        # Fallback in case of error
        dummy_venue = EventVenue(
            name="Sample Venue",
            address="123 Main St, City",
            details="No venue details available due to processing error",
            rating="N/A",
            suitability_score=5
        )
        return {"venues": [dummy_venue], "venues_ready": True}


def recommendation_analyzer(state):
    """Generate comprehensive event recommendations"""
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY", "")

    # Initialize LLM with API key
    llm = ChatOpenAI(model=config["api"]["default_model"], api_key=api_key)

    weather_data = state['weather_report']
    venues = state['venues']
    event_type = state['event']
    location = state['location']
    date_str = state['date']

    try:
        weather_report = json.loads(weather_data)
        weather_description = f"""
Weather for {weather_report['day_name']} ({weather_report['date']}) in {weather_report['location']}:
- Conditions: {weather_report['description']}
- Temperature: {weather_report['min_temp']}°C to {weather_report['max_temp']}°C
- Precipitation probability: {weather_report['precipitation_probability']}%
"""
    except:
        weather_description = weather_data

    prompt = f"""
You are an expert event planner. Based on:
1. Weather: {weather_description}
2. Event Type: {event_type}
3. Location: {location} 
4. Date: {date_str}
5. Available Venues: {venues}

Provide a comprehensive recommendation including:
1. Whether the event should be indoors or outdoors given the weather
2. The top 2 venue recommendations with brief justification
3. Suggested timing for the event (morning, afternoon, evening)
4. Any special preparations needed based on weather or venue
5. Alternative plan in case of unexpected issues

Format your response in a professional, elegant way suitable for an event planning service.
"""
    try:
        result = llm.invoke(prompt)
        return {"recommendation": result.content}
    except Exception as e:
        # Fallback recommendation in case of error
        return {
            "recommendation": f"""
# Event Planning Recommendation

Due to a technical issue, we could not generate a detailed recommendation.

## Basic Recommendation
- Consider indoor venues if the weather forecast shows rain or extreme temperatures
- Choose a venue that specializes in {event_type} events
- Have a backup plan in case of unexpected issues

Please try again later for more detailed recommendations.
"""
        }