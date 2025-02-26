import os
import datetime
import streamlit as st
from typing import TypedDict, Annotated, List
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
import requests
from langchain_core.messages import HumanMessage
import json

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Set page config
st.set_page_config(
    page_title="EventPro AI Planner",
    page_icon="🎪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
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
""", unsafe_allow_html=True)

# Sidebar for API key input
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("OpenAI API Key",
                            value=os.getenv("OPENAI_API_KEY", ""),
                            type="password",
                            help="Enter your OpenAI API key to use the app")


    if os.getenv("OPENAI_API_KEY", ""):
        st.success("API key is set")
    else:
        st.info("API key will be loaded from .env file if available")

    st.markdown("---")
    st.markdown("### How to use EventPro AI")
    st.markdown("""
    1. Enter your OpenAI API key
    2. Fill out the event details form
    3. Click "Plan My Event" to get recommendations
    4. Review weather, venues, and AI recommendations
    """)

    st.markdown("---")
    st.markdown("### Examples")
    st.markdown("""
    - "Plan a wedding in Paris for next Saturday"
    - "I need a venue for a corporate meeting in New York this Friday"
    - "Find places for a birthday party in London next weekend"
    """)

# Weather codes dictionary
weather_codes = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Light rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Light snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Rain showers",
    81: "Moderate rain showers", 82: "Violent rain showers", 95: "Thunderstorm",
    96: "Thunderstorm with light hail", 99: "Thunderstorm with heavy hail",
}


# Define EventVenue model
class EventVenue(BaseModel):
    name: str = Field(..., description="Name of the venue")
    address: str = Field(..., description="Address of the venue")
    details: str = Field(..., description="Details of the venue")
    rating: str = Field("N/A", description="Rating of the venue if available")
    suitability_score: int = Field(0, description="Suitability score from 1-10 based on event type")


# Define ParentState
class ParentState(TypedDict):
    messages: Annotated[list, add_messages]
    location: str
    date: str
    event: str
    weather_report: str
    search_result: str
    venues: List[EventVenue]
    recommendation: str
    # Add flags to track completion of parallel paths
    weather_ready: bool
    venues_ready: bool


# Helper function to get the next date
def get_next_date(date_str):
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


# Node Functions
class QueryAnalysis(BaseModel):
    location: str = Field(..., description="The city or place name for the event")
    date: str = Field(..., description="The day of the week or date for the event")
    event: str = Field(..., description="The type of event or occasion being planned")


def query_analyzer(state: ParentState):
    messages = state['messages']
    user_query = messages[-1].content

    # Get API key from session state
    api_key = os.getenv("OPENAI_API_KEY", "")

    try:
        # Initialize LLM with API key
        llm = ChatOpenAI(model="gpt-3.5-turbo", api_key=api_key)

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
                event = "event"
                location = "location"
                date = "this weekend"

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
                return {"location": "New York", "date": "this weekend", "event": "event"}
    except Exception as e:
        st.error(f"Error in query analyzer: {str(e)}")
        return {"location": "New York", "date": "this weekend", "event": "event"}


def weather_fetcher(state: ParentState):
    location = state['location']
    date_str = state['date']
    target_date = get_next_date(date_str)

    try:
        # Geocoding request
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json"
        response = requests.get(geocode_url)
        if response.status_code != 200 or not response.json().get('results'):
            return {"weather_report": f"📍 **{location}**: Weather data not available (location not found)",
                    "weather_ready": True}

        result = response.json()['results'][0]
        latitude, longitude = result['latitude'], result['longitude']

        # Weather request
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto"
        response = requests.get(weather_url)

        if response.status_code != 200:
            return {"weather_report": f"📍 **{location}**: Weather data not available (API error)",
                    "weather_ready": True}

        data = response.json()['daily']
        target_date_str = target_date.strftime("%Y-%m-%d")

        # If the exact date isn't available, use the closest available date
        if target_date_str not in data['time'] and len(data['time']) > 0:
            # Find the closest date available in the API response
            closest_date_str = data['time'][0]  # Default to first available date
            min_days_diff = float('inf')

            for api_date in data['time']:
                api_date_obj = datetime.datetime.strptime(api_date, "%Y-%m-%d").date()
                days_diff = abs((api_date_obj - target_date).days)

                if days_diff < min_days_diff:
                    min_days_diff = days_diff
                    closest_date_str = api_date

            # Use the closest date instead
            target_date_str = closest_date_str
            target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()

            # Add a note about using an alternative date
            date_note = f" (using forecast for {target_date.strftime('%A, %B %d')} as requested date unavailable)"
        else:
            date_note = ""

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
                "weather_code": weather_code,
                "date_note": date_note
            }

            return {"weather_report": json.dumps(weather_report), "weather_ready": True}

        return {"weather_report": f"📍 **{location}**: Weather forecast not available for {target_date_str}",
                "weather_ready": True}

    except Exception as e:
        return {"weather_report": f"📍 **{location}**: Error fetching weather data: {str(e)}", "weather_ready": True}


def event_planning_assistant(state: ParentState):
    location = state['location']
    event = state['event']
    query = f"best venues for {event} in {location} with reviews and ratings"

    try:
        search_tool = DuckDuckGoSearchRun()
        search_result = search_tool.run(query)
        return {"search_result": search_result}
    except Exception as e:
        return {"search_result": f"Error searching for venues: {str(e)}"}


class VenuesList(BaseModel):
    venues: List[EventVenue]


def venues_list_formatter(state: ParentState):
    # Get API key from session state
    api_key = os.getenv("OPENAI_API_KEY", "")

    # Initialize LLM with API key
    llm = ChatOpenAI(model="gpt-3.5-turbo", api_key=api_key)

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

Limit to the 5 most relevant venues.
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


def recommendation_analyzer(state: ParentState):
    # Get API key from session state
    api_key = os.getenv("OPENAI_API_KEY", "")

    # Initialize LLM with API key
    llm = ChatOpenAI(model="gpt-3.5-turbo", api_key=api_key)

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


# Check if both paths are complete
def both_paths_complete(state):
    return state.get("weather_ready") and state.get("venues_ready")


# Build the Graph
def build_event_planning_graph():
    parent_builder = StateGraph(ParentState)
    parent_builder.add_node("query_analyzer", query_analyzer)
    parent_builder.add_node("weather_fetcher", weather_fetcher)
    parent_builder.add_node("event_planning_assistant", event_planning_assistant)
    parent_builder.add_node("venues_list_formatter", venues_list_formatter)
    parent_builder.add_node("recommendation_analyzer", recommendation_analyzer)

    # Connect the nodes
    parent_builder.add_edge(START, "query_analyzer")
    parent_builder.add_edge("query_analyzer", "weather_fetcher")
    parent_builder.add_edge("query_analyzer", "event_planning_assistant")
    parent_builder.add_edge("event_planning_assistant", "venues_list_formatter")

    # Use conditional routing to ensure both paths complete
    parent_builder.add_conditional_edges(
        "weather_fetcher",
        lambda state: "recommendation_analyzer" if both_paths_complete(state) else "__wait__"
    )

    parent_builder.add_conditional_edges(
        "venues_list_formatter",
        lambda state: "recommendation_analyzer" if both_paths_complete(state) else "__wait__"
    )

    # Add a special "wait" node that routes back to itself until both conditions are met
    parent_builder.add_node("__wait__", lambda state: state)
    parent_builder.add_conditional_edges(
        "__wait__",
        lambda state: "recommendation_analyzer" if both_paths_complete(state) else "__wait__"
    )

    parent_builder.add_edge("recommendation_analyzer", END)

    return parent_builder.compile()


# Streamlit UI
st.markdown('<h1 class="main-header">EventPro AI Planner</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; font-size: 1.2rem;">Your professional event planning assistant</p>',
            unsafe_allow_html=True)

# Create tabs
tab1, tab2 = st.tabs(["✨ Plan Your Event", "ℹ️ About"])

with tab1:
    # Event planning form
    with st.form("event_planning_form"):
        col1, col2 = st.columns(2)

        with col1:
            event_type = st.text_input("Event Type", placeholder="Wedding, Conference, Birthday Party...")
            location = st.text_input("Location", placeholder="City or Place")

        with col2:
            date_options = ["Today", "Tomorrow", "This Weekend", "Next Weekend",
                            "This Monday", "This Tuesday", "This Wednesday", "This Thursday",
                            "This Friday", "This Saturday", "This Sunday",
                            "Next Monday", "Next Tuesday", "Next Wednesday", "Next Thursday",
                            "Next Friday", "Next Saturday", "Next Sunday", "Custom Date"]

            date_selection = st.selectbox("When is your event?", date_options)

            if date_selection == "Custom Date":
                date_input = st.date_input("Select a Date", datetime.date.today())
                date_str = date_input.strftime("%Y-%m-%d")
            else:
                date_str = date_selection.lower()

        # Query field (optional)
        additional_requirements = st.text_area("Additional Requirements (Optional)",
                                               placeholder="e.g., needs catering, accessible facilities, outdoor space...")

        # Create full query for the AI
        query = f"Plan a {event_type} in {location} for {date_str}"
        if additional_requirements:
            query += f". Requirements: {additional_requirements}"

        # Submit button
        submit_button = st.form_submit_button("Plan My Event")

    if submit_button:
        # Check if API key is available
        api_key = os.getenv("OPENAI_API_KEY", "")

        if not api_key:
            st.error("⚠️ No OpenAI API key found. Please add it to your .env file or enter it in the sidebar")
        elif not event_type or not location or not date_str:
            st.error("⚠️ Please fill out all required fields")
        else:
            with st.spinner("Planning your event... This may take a moment"):
                try:
                    # Initialize the graph
                    parent_graph = build_event_planning_graph()

                    # Run the graph
                    result = parent_graph.invoke({
                        "messages": [HumanMessage(content=query)]
                    })

                    # Display Results in a structured format
                    st.success("✅ Event planned successfully!")

                    # Create three columns
                    col1, col2 = st.columns([1, 1])

                    with col1:
                        st.markdown('<h2 class="sub-header">Event Details</h2>', unsafe_allow_html=True)
                        st.markdown(f"""
                        <div class="info-box">
                        <p><strong>🎪 Event Type:</strong> {event_type}</p>
                        <p><strong>📍 Location:</strong> {location}</p>
                        <p><strong>📅 Date:</strong> {date_str}</p>
                        </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        # Venues information
                        st.markdown('<h2 class="sub-header">Recommended Venues</h2>', unsafe_allow_html=True)
                        for venue in result['venues'][:3]:  # Show top 3 venues
                            st.markdown(f"""
                            <div class="venue-card">
                            <h3>{venue.name}</h3>
                            <p><strong>Address:</strong> {venue.address}</p>
                            <p><strong>Rating:</strong> {venue.rating}</p>
                            <p><strong>Suitability Score:</strong> {venue.suitability_score}/10</p>
                            <p><em>{venue.details}</em></p>
                            </div>
                            """, unsafe_allow_html=True)

                    # AI Recommendation
                    st.markdown('<h2 class="sub-header">AI Recommendation</h2>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="recommendation-box">
                    {result['recommendation']}
                    </div>
                    """, unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Error processing your request: {str(e)}")
                    if "API key" in str(e):
                        st.warning("Please check your OpenAI API key in the sidebar")

with tab2:
    st.markdown("""
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
    """)

