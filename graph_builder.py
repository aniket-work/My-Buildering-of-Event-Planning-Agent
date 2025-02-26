from langgraph.graph import StateGraph, START, END

from models import ParentState
from graph_nodes import (
    query_analyzer,
    weather_fetcher,
    event_planning_assistant,
    venues_list_formatter,
    recommendation_analyzer
)
from utils import both_paths_complete


def build_event_planning_graph():
    """Create and compile the event planning state graph"""

    # Initialize the state graph
    parent_builder = StateGraph(ParentState)

    # Add nodes for each step in the process
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