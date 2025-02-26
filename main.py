import os
import datetime
import streamlit as st
import json
from langchain_core.messages import HumanMessage

# Import local modules
from constants import CSS_STYLES, SIDEBAR_HELP
from utils import load_config
from graph_builder import build_event_planning_graph
from templates import (
    get_about_content,
    get_event_details_card,
    get_weather_card,
    get_venue_card,
    get_recommendation_box
)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Load configuration
config = load_config()

# Set page config
st.set_page_config(
    page_title=config["app"]["title"],
    page_icon=config["app"]["icon"],
    layout=config["app"]["layout"],
    initial_sidebar_state=config["app"]["sidebar_state"]
)

# Apply custom CSS
st.markdown(CSS_STYLES, unsafe_allow_html=True)

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
    st.markdown("\n".join(SIDEBAR_HELP["usage"]))

    st.markdown("---")
    st.markdown("### Examples")
    st.markdown("\n".join(SIDEBAR_HELP["examples"]))

# Streamlit UI
st.markdown(f'<h1 class="main-header">{config["app"]["title"]}</h1>', unsafe_allow_html=True)
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
            date_options = config["date_options"]
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

                    # Create columns
                    col1, col2 = st.columns([1, 1])

                    with col1:
                        st.markdown('<h2 class="sub-header">Event Details</h2>', unsafe_allow_html=True)
                        st.markdown(get_event_details_card(event_type, location, date_str), unsafe_allow_html=True)

                        # Weather information
                        st.markdown('<h2 class="sub-header">Weather Forecast</h2>', unsafe_allow_html=True)
                        st.markdown(get_weather_card(result['weather_report']), unsafe_allow_html=True)

                    with col2:
                        # Venues information
                        st.markdown('<h2 class="sub-header">Recommended Venues</h2>', unsafe_allow_html=True)
                        for venue in result['venues'][:3]:  # Show top 3 venues
                            st.markdown(get_venue_card(venue), unsafe_allow_html=True)

                    # AI Recommendation
                    st.markdown('<h2 class="sub-header">AI Recommendation</h2>', unsafe_allow_html=True)
                    st.markdown(get_recommendation_box(result['recommendation']), unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Error processing your request: {str(e)}")
                    if "API key" in str(e):
                        st.warning("Please check your OpenAI API key in the sidebar")

with tab2:
    st.markdown(get_about_content())

if __name__ == "__main__":
    # The app is already running at this point through Streamlit
    pass