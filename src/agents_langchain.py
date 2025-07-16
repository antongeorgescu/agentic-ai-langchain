from langchain.agents import AgentType, initialize_agent, create_react_agent, AgentExecutor
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_openai import AzureChatOpenAI

import os

from plugins.search_flights import get_flight_info

""""
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
azure_openai_version= os.getenv("AZURE_OPENAI_API_VERSION")

llm = AzureChatOpenAI(
    api_key=azure_api_key,
    azure_endpoint=azure_endpoint,
    deployment_name=azure_deployment_name,
    openai_api_version=azure_openai_version, # Using a recent API version
    temperature=0.7 # Example temperature
)

# Define a simple weather tool that queries the LLM for weather info
def weather_tool_func(location: str) -> str:
    prompt = f"What is the current weather in {location}?"
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content

# Define a simple travel tool that queries the LLM for travel information
def travel_tool_func(destination: str) -> str:
    prompt = f"Provide travel information, tips, and recommendations for visiting {destination}."
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content

def is_travel_intent_llm(user_input: str) -> bool:
    """
    Uses the LLM to classify if the user input is about travel information.
    """
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

def extract_flight_details_llm(query: str, llm) -> dict:
    """
    Uses the LLM to extract destination, departure date, return date, and optionally origin from the user's query.
    Returns a dictionary with keys: destination, departure_date, return_date, origin (optional).
    """
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
        # Try to parse the LLM's response as JSON
        import json
        details = json.loads(response.content)
        return details
    except Exception:
        return {}

# Define a flight tool using the imported get_flight_info function
def flight_tool_func(query: str) -> str:
    """
    Uses get_flight_info to provide flight information based on the user's query.
    Confirm with the user departure location. If departure_date or return_date is missing, invite the user to provide them.
    """
    # Extract flight details using the LLM
    flight_details = extract_flight_details_llm(query, llm)

    return get_flight_info(flight_details["origin"],flight_details["destination"], flight_details["departure_date"], flight_details["return_date"])     

def is_flight_intent_llm(user_input: str) -> bool:
    """
    Uses the LLM to classify if the user input is about flight information.
    """
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

def human_conversation(agent_response):
    print(f"Human: {agent_response}")
    return input("Your response: ")

def is_weather_intent_keywords(user_input: str) -> bool:
    """
    Returns True if the user input is likely asking about the weather.
    """
    weather_keywords = [
        "temperature", "rain", "sunny", "cloudy", "forecast", "wind", "humidity",
        "snow", "storm", "hot", "cold", "climate", "how is it outside", "is it raining",
        "is it sunny", "is it snowing", "is it hot", "is it cold", "weather"
    ]
    user_input_lower = user_input.lower()
    return any(keyword in user_input_lower for keyword in weather_keywords)

def is_weather_intent_llm(user_input: str) -> bool:
    """
    Uses the LLM to classify if the user input is about weather.
    """
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

# Add an LLM-powered greeting before collecting user query
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

def init_agents():
    """
    Initializes the agents and their tools.
    This function is called at the start of the script to set up the agents.
    """
    global flights_agent, travel_agent, weather_agent

    # Create a flight tool using the flight tool function
    flight_tool = Tool(
        name="FlightInfoTool",
        description="Provides flight information between locations. Input should specify destination, and departure and returns dates.",
        func=flight_tool_func
    )
    
    # Create a flight agent using the flight tool
    flights_agent = initialize_agent(
        [flight_tool],
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )

    travel_tool = Tool(
        name="TravelInfoTool",
        description="Offers travel information, tips, and recommendations for a given destination using the LLM.",
        func=travel_tool_func
    )

    # Create a travel agent using the travel tool
    travel_agent = initialize_agent(
        [travel_tool],
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )

    weather_tool = Tool(
        name="WeatherTool",
        description="Provides current weather information for a given location using the LLM.",
        func=weather_tool_func
    )

    # Create a weather agent using the weather tool
    weather_agent = initialize_agent(
        [weather_tool],
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )

if __name__ == "__main__":
    # Create the agents and their tools
    init_agents()
    
    # Greet the user using the LLM
    llm_greeting()

    # Start the main conversation loop
    while True:
        human_input = input("Human: ")
        if human_input.lower() == 'quit':
            break

        # Use the weather agent to answer weather-related questions
        if is_weather_intent_llm(human_input):
            result = weather_agent.run(human_input)
            print(f"[Weather Agent]: {result}")
        # Use the travel agent to answer travel-related questions
        elif is_travel_intent_llm(human_input):
            result = travel_agent.run(human_input)
            print(f"[Travel Agent]: {result}")
        # Use the flights agent to answer flight-related questions
        elif is_flight_intent_llm(human_input):
            result = flights_agent.run(human_input)
            print(f"[Flight Agent]: {result}")
        else:
            print("Agent: I am currently being updated to handle weather, travel, and flight information.")