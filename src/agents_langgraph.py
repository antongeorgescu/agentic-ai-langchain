from langgraph.graph import StateGraph
from langgraph.graph import START, END
import os
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain.tools import tool
from langchain_core.messages import ToolMessage

from dotenv import load_dotenv
from langgraph.graph import MessagesState
from langgraph.graph import START, END
from langgraph.prebuilt import tools_condition, ToolNode

from duckduckgo_search import DDGS

load_dotenv()

################# Create Open AI model #######################################################
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

################## Specialized agents tools ##################################################
# Define a web search function that uses DuckDuckGo Search
@tool
def web_search(query:str) -> str:
    """
    Search the web using the query provided and return up to 5 results in an aggregated format.
    Skip the results that do not have a title or body, or are not in English language, and continue the search till you hit the limit of 5 results.
    If no results are found, return a message indicating that.
    """
    with DDGS(verify=False) as ddgs:
        results = ddgs.text(query, max_results=5)
        if results:
            output = []
            for res in results:
                output.append(
                    f"Title: {res['title']}\nURL: {res['href']}\nSnippet: {res['body']}\n"
                )
            return "\n---\n".join(output)
        else:
            return "No results found."

################## Create researcher agent #####################################################
researcher_model = model
research_tools = [web_search]
research_model_with_tools = model.bind_tools(research_tools)

def researcher_llm(state):

    msg_content = ("You are a helpful learning assistant. You search on "
        "the internet and provide the answer using different sources. "
        "You also cite those sources.")
    message = [SystemMessage(content=msg_content)] + state['messages']

    return {"messages": research_model_with_tools.invoke(message)}

researcher_graph = StateGraph(MessagesState)
researcher_graph.add_node("researcher", researcher_llm)
researcher_graph.add_node("tools", ToolNode(research_tools))

researcher_graph.add_edge(START, "researcher")
researcher_graph.add_conditional_edges("researcher", tools_condition)

researcher_agent = researcher_graph.compile()

# Uncomment the following lines to test the researcher agent
# This is a test for the researcher agent that searches the internet for the query
# user_input = "What is the most populare agentic framework?"
# resp = researcher_agent.invoke({"messages": [HumanMessage(user_input)]})
# print(resp['messages'][-1].content[:500] + ' ...')

################## Create explainer agent ###################################################
explainer_model = model

def explainer_llm(state):

    msg_content = ("You are a helpful teacher. You explain any topic, "
        "regardless how difficult it is, in a very simple way. Your "
        "students are children and they do not understand many things."
        " To do so, you use examples, stories and allegories as needed."
        "Look on the internet any concept you don't understand.")

    message = [SystemMessage(content=msg_content)] + state['messages']

    return {"messages": explainer_model.invoke(message)}

explainer_graph = StateGraph(MessagesState)
explainer_graph.add_node("explainer", explainer_llm)
explainer_graph.add_node("tools", ToolNode(research_tools))

explainer_graph.add_edge(START, "explainer")
explainer_graph.add_conditional_edges("explainer", tools_condition)

explainer_agent = explainer_graph.compile()

# Uncomment the following lines to test the explainer agent
# This is a test for the explainer agent that uses researcher agent to search for the concept
# user_input = "Explain the concept of entropy in physics."
# resp = explainer_agent.invoke({"messages": [HumanMessage(user_input)]})
# print(resp['messages'][-1].content[:500] + ' ...')

###################### Create generalist agent ##############################################
graph = StateGraph(MessagesState)

@tool
def explainer(concept:str) -> str: 
    """Explains a concept in a simple way using examples, stories and allegories.

    Args:
        concept: concept to explain.

    Returns:
        str: explanation of the concept.
    """
    resp = explainer_agent.invoke({"messages": [HumanMessage(concept)]})
    return resp['messages'][-1]

@tool
def researcher(query:str) -> str:
    """Searches the internet to answer your questions.

    Args:
        query: query to search for.

    Returns:
        str: best answer to the query.
    """
    resp = researcher_agent.invoke({"messages": [HumanMessage(query)]})
    return resp['messages'][-1]

# Bind the agents to the model
supervisor_tools = [researcher, explainer]
supervisor_model = model
supervisor_model_with_tools = model.bind_tools(supervisor_tools)

# Define the supervisor
def supervisor(state):

    msg_content = ("You are a helpful assistant, "
        "you use the tools at your disposal to provide the best answer."
        "You should always search on the internet before answering, by using the researcher tool, "
        "and explain the answer in a very simple way using examples, "
        "stories and allegories, by using the explainer tool."
        "You have to provide the aggregated answers in a single message."
    )

    message = [SystemMessage(content=msg_content)] + state['messages']

    # return {"messages": supervisor_model_with_tools.invoke(message)}
    response = supervisor_model_with_tools.invoke(message)
    # If the model calls a tool
    if hasattr(response, "tool_calls"):
        tool_call = response.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

        if tool_name == "explainer":
            # result_msg = explainer(**tool_args)
            result_msg = explainer(tool_args["concept"])
            result = result_msg.content if hasattr(result_msg, "content") else str(result_msg)
        elif tool_name == "researcher":
            # result_msg = researcher(**tool_args)
            result_msg = researcher(tool_args["query"])
            result = result_msg.content if hasattr(result_msg, "content") else str(result_msg)

        return {
            "messages": [
                response,
                ToolMessage(tool_call_id=tool_id, content=result)
            ]
        }

    return {"messages": [response]}

# Create the graph
graph = StateGraph(MessagesState)
graph.add_node("supervisor", supervisor)
graph.add_node("tools", ToolNode(supervisor_tools))

graph.add_edge(START, "supervisor")
graph.add_edge("tools", "supervisor")
graph.add_conditional_edges("supervisor", tools_condition)

supervisor_agent = graph.compile()

# _ = (
#     supervisor_agent
#     .get_graph()
#     .draw_mermaid_png(output_file_path='imgs/supervisor_graph.png')
# )

###################### Capture the user queries ##############################################
while True:
    user_query = input("Ask a question (type 'quit' to exit): ")
    if user_query.strip().lower() == 'quit':
        print("Exiting conversation.")
        break
    state = {"messages": [HumanMessage(user_query)]}
    resp = supervisor_agent.invoke(state)
    for message in resp['messages']:
        message.pretty_print()

"""
**** Sample queries that will trigger one of the two agents (researcher, explainer) ****
Explain the causes of the decline of the Roman Empire in a simple way, addressing a very young audience.
Which where the causes of the decline of the Roman Empire?

"""
