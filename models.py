from typing import TypedDict, Annotated, List
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages

# Define EventVenue model
class EventVenue(BaseModel):
    name: str = Field(..., description="Name of the venue")
    address: str = Field(..., description="Address of the venue")
    details: str = Field(..., description="Details of the venue")
    rating: str = Field("N/A", description="Rating of the venue if available")
    suitability_score: int = Field(0, description="Suitability score from 1-10 based on event type")


# Define ParentState for the graph
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


# Analysis model for extracting query information
class QueryAnalysis(BaseModel):
    location: str = Field(..., description="The city or place name for the event")
    date: str = Field(..., description="The day of the week or date for the event")
    event: str = Field(..., description="The type of event or occasion being planned")


# Venues list for structured LLM output
class VenuesList(BaseModel):
    venues: List[EventVenue]