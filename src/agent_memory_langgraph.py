# from langchain_community.tools.ddg_search import DuckDuckGoSearchRun
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph

from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.graph import MessagesState
from langgraph.graph import START, END
import os

from langgraph.checkpoint.sqlite import sqlite3, SqliteSaver
from plugins.synth_data_gen import weather_by_city_search, event_by_city_search, supported_cities_search

# Create or connect to a SQLite database for checkpointing
conn = sqlite3.connect('memory.db', check_same_thread=False)
memory = SqliteSaver(conn)

config = {"configurable": {"thread_id": "2"}}

load_dotenv()

azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
azure_openai_version= os.getenv("AZURE_OPENAI_API_VERSION")

model = AzureChatOpenAI(
    api_key=azure_api_key,
    azure_endpoint=azure_endpoint,
    deployment_name=azure_deployment_name,
    openai_api_version=azure_openai_version, # Using a recent API version
    temperature=0.7 # Example temperature
)

# Set of tools for the agent
tools = [weather_by_city_search, event_by_city_search, supported_cities_search]
model_with_tools = model.bind_tools(tools)

def travel_llm(state):

    msg_content = (
        "You are a helpful assistant that can answer questions about the weather, cultural events and sport information in various cities around the world. " 
        "For weather and cultural events, you have to use only the tools provided. "
        "Your answers have to refer strictly to the topic of the question asked. "
    )
    message = [SystemMessage(content=msg_content)] + state['messages']

    return {"messages": model_with_tools.invoke(message)}


graph = StateGraph(MessagesState)
graph.add_node("travel_llm", travel_llm)
graph.add_node("tools", ToolNode(tools))

graph.add_edge(START, "travel_llm")
graph.add_edge("tools", "travel_llm")
graph.add_conditional_edges("travel_llm", tools_condition)

agent = graph.compile(checkpointer=memory)
# _ = (
#     agent
#     .get_graph()
#     .draw_mermaid_png(output_file_path='imgs/weather_tool_agent.png')
# )

while True:
    user_input = input("Ask a question (type 'quit' to exit): ")
    if user_input.strip().lower() == 'quit':
        print("Exiting conversation.")
        break
    response = agent.invoke(
        {"messages": [HumanMessage(user_input)]},
        config=config
    )
    result = f"\n.....{response['messages'][-1].content}"
    print(result)

    if "error" in response['messages'][-1].content:
        break

