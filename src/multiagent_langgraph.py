from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, ToolExecutor
from langgraph.prebuilt import tools_from_functions
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

import os
from plugins.search_flights import get_flight_info

"""
*** Sample user queries for testing the flight tool and agent ***
What are the best flights from Toronto, Ontario to Mumbai, India?
I'd like to spend a couple of weeks visiting India, this coming November, 2025
Which are the best flights between Toronto, Ontario and Mumbai, departing on November 11, 2025 and coming back two weeks later?
I need booking details about British Airways flight from Toronto, Ontario and Mumbai, departing on November 11, 2025 and coming back on November 25, 2025
How is the weather in Mumbai in November?
What are the best day trips from Mumbai in November?
How far away is the Taj Mahal from Mumbai?
"""

# Load environment variables for Azure OpenAI configuration
azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
azure_openai_version = os.getenv("AZURE_OPENAI_API_VERSION")

llm = AzureChatOpenAI(
    api_key=azure_api_key,
    azure_endpoint=azure_endpoint,
    deployment_name=azure_deployment_name,
    openai_api_version=azure_openai_version,
    temperature=0.7
)

# --- Tool Functions ---

def weather_tool_func(location: str) -> str:
    prompt = f"What is the current weather in {location}?"
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content

def travel_tool_func(destination: str) -> str:
    prompt = f"Provide travel information, tips, and recommendations for visiting {destination}."
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content

def extract_flight_details_llm(query: str) -> dict:
    system_prompt = (
        "You are a helpful assistant that extracts flight search details from user queries. "
        "Given a user message, extract the following fields if present: "
        "destination, departure_date, return_date, and origin. "
        "Return your answer as a JSON object with these keys. "
        "Make sure to provide only the city name in the 'origin' and 'destination' fields, with additional province or country information if available. "
        "If a field is missing, use null for its value."
    )
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=query)
    ])
    try:
        import json
        details = json.loads(response.content)
        return details
    except Exception:
        return {}

def flight_tool_func(query: str) -> str:
    flight_details = extract_flight_details_llm(query)
    return get_flight_info(
        flight_details.get("origin"),
        flight_details.get("destination"),
        flight_details.get("departure_date"),
        flight_details.get("return_date")
    )

# --- Intent Classifiers ---

def is_weather_intent_llm(user_input: str) -> bool:
    system_prompt = (
        "You are an intent classifier. "
        "If the following message is asking about weather, temperature, climate, or atmospheric conditions, respond ONLY with 'yes'. "
        "Otherwise, respond ONLY with 'no'."
    )
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input)
    ])
    return response.content.strip().lower() == "yes"

def is_travel_intent_llm(user_input: str) -> bool:
    system_prompt = (
        "You are an intent classifier. "
        "If the following message is asking for flight information, schedules, bookings, and destinations, respond ONLY with 'no'. "
        "If the following message is asking for travel information, tips, or recommendations about a destination, respond ONLY with 'yes'. "
        "Otherwise, respond ONLY with 'no'."
    )
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input)
    ])
    return response.content.strip().lower() == "yes"

def is_flight_intent_llm(user_input: str) -> bool:
    system_prompt = (
        "You are an intent classifier. "
        "If the following message is asking for flight information, booking, schedules, or airfare between locations, respond ONLY with 'yes'. "
        "Otherwise, respond ONLY with 'no'."
    )
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input)
    ])
    return response.content.strip().lower() == "yes"

# --- LangGraph Tool Setup ---

tools = tools_from_functions([
    ("WeatherTool", weather_tool_func, "Provides current weather information for a given location using the LLM."),
    ("TravelInfoTool", travel_tool_func, "Offers travel information, tips, and recommendations for a given destination using the LLM."),
    ("FlightInfoTool", flight_tool_func, "Provides flight information between locations. Input should specify destination, and departure and returns dates."),
])

tool_executor = ToolExecutor(tools)

# --- LangGraph State and Nodes ---

def router_node(state):
    user_input = state["user_input"]
    if is_weather_intent_llm(user_input):
        return {"tool": "WeatherTool", "tool_input": user_input}
    elif is_travel_intent_llm(user_input):
        return {"tool": "TravelInfoTool", "tool_input": user_input}
    elif is_flight_intent_llm(user_input):
        return {"tool": "FlightInfoTool", "tool_input": user_input}
    else:
        return {"tool": None, "tool_input": user_input}

def fallback_node(state):
    return {"output": "Agent: I am currently being updated to handle weather, travel, and flight information."}

def output_node(state):
    return {"output": state.get("tool_output")}

# --- Build the LangGraph ---

graph = StateGraph()
graph.add_node("router", router_node)
graph.add_node("tool", ToolNode(tool_executor))
graph.add_node("fallback", fallback_node)
graph.add_node("output", output_node)

graph.add_edge("router", "tool", condition=lambda state: state["tool"] is not None)
graph.add_edge("router", "fallback", condition=lambda state: state["tool"] is None)
graph.add_edge("tool", "output")
graph.add_edge("fallback", "output")
graph.add_edge("output", END)

graph.set_entry_point("router")
langgraph_app = graph.compile()

# --- LLM Greeting ---

def llm_greeting():
    system_prompt = (
        "You are a friendly AI assistant. Greet the user and briefly explain that you can help with weather, travel, and flight information. "
        "Keep your greeting to 2-3 sentences."
    )
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content="Greet the user.")
    ])
    print(f"Agent: {response.content.strip()}")

# --- Main Loop ---
if __name__ == "__main__":
    llm_greeting()
    # print("Start the conversation. Type 'quit' to exit.")
    while True:
        human_input = input("Human: ")
        if human_input.lower() == 'quit':
            break
        state = {"user_input": human_input}
        result = langgraph_app.invoke(state)
        print(result["output"])