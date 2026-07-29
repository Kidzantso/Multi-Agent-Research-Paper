import os
from typing import TypedDict

from dotenv import find_dotenv, load_dotenv
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph

load_dotenv(find_dotenv())

GROQ_API_KEY = os.getenv("GROQ_KEY") or os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    groq_api_key=GROQ_API_KEY,
    temperature=0.1,
)
search = DuckDuckGoSearchRun(name="Search")


class AgentState(TypedDict):
    topic: str
    plan: str
    abstract: str
    introduction: str
    related_work: str
    datasets: str
    methodology: str
    models_used: str
    draft: str
    editor: str
    final: str


def invoke_text(prompt: str) -> str:
    return llm.invoke(prompt).content


def search_context(query: str) -> str:
    try:
        return search.run(query)
    except Exception as exc:
        return f"Search failed: {exc}"


def with_search(prompt: str, query: str) -> str:
    return f"{prompt}\n\nDuckDuckGo search results:\n{search_context(query)}"


def planner_node(state: AgentState) -> dict:
    prompt = f"You are a researcher who is participating in writing an IEEE research paper. Your role is to Create a detailed outline for the research paper article about: {state['topic']} including: related papers that worked on the same topic, their citations, 2-3 datasets used in this topic, models used in this papers to research this topic, methodology used to adress it. You should use the search tool to find relevant papers and datasets. Make sure to include proper citations for any information found through searching."
    return {"plan": invoke_text(with_search(prompt, f"{state['topic']} related papers datasets"))}


def abstract_node(state: AgentState) -> dict:
    prompt = f"You are a researcher who is participating in writing an IEEE research paper. Your role is to Write ONLY the abstract part for a new research paper upon this topic:\n\n{state['topic']}, here is the outline that we will be following:{state['plan']}, look at your part and summarize it to be an abstract that is talking about what the research paper will do and the models will be used in this paper and write keywords. Use the search tool to find any missing information about models or concepts."
    return {"abstract": invoke_text(with_search(prompt, f"{state['topic']} models concepts"))}


def related_work_node(state: AgentState) -> dict:
    prompt = f"You are a researcher who is participating in writing an IEEE research paper. Your role is to Write ONLY the summarization part (Literature review) for these research papers mentioned here in the plan :\n\n{state['plan']} \n\n, Include the: 1. The authors for each paper \n 2. Models with the highest results \n 3. Each study's conclusion \n 4. Each study's Limitation \n \n Write One paragraph for each paper mentioned. Use the search tool to find details about the mentioned papers, including authors, models, conclusions, and limitations and then rewrite everything in the plan using your results in searching and your own words, ONLY the releated work section."
    return {"related_work": invoke_text(with_search(prompt, f"{state['topic']} research papers authors models limitations"))}


def datasets_node(state: AgentState) -> dict:
    prompt = f"You are a researcher who is participating in writing an IEEE research paper. Your role is to write ONLY about the datasets mentioned in this outline:\n\n{state['plan']} , search for each and describe in details by showing: 1. Number of features \n 2. Number of records \n 3. Target feature \n 4. Each feature's description. Write one paragraph for each dataset. Use the search tool to gather detailed information about each dataset and use the plan and search results to rewrite in your own words ONLY the dataset section."
    return {"datasets": invoke_text(with_search(prompt, f"{state['topic']} datasets features records target"))}


def methodology_node(state: AgentState) -> dict:
    prompt = f"You are a researcher who is participating in writing an IEEE research paper. Your role is to Write ONLY the 'Methodology' part using this outline: \n{state['plan']} \n\n You must include: 1. (3-5) Models that will be used \n 2. Steps for data preprocessing \n 3. Performance metrics that will measure the accuracy of the models. Use the search tool to research appropriate models, data preprocessing steps, and performance metrics relevant to the topic, rewrite in your own words the methodology section ONLY using your results in searching."
    return {"methodology": invoke_text(with_search(prompt, f"{state['topic']} models preprocessing evaluation metrics"))}


def models_used_node(state: AgentState) -> dict:
    prompt = f"You are a researcher who is participating in writing an IEEE research paper. Your role is to Write ONLY the description of the models that will be used. \n Use the models listed here inside the methodolgy planned :{state['methodology']}, search and explain each model separately in one paragraph. Use the search tool to find detailed explanations and characteristics of each model then rewrite the models used section ONLY."
    return {"models_used": invoke_text(with_search(prompt, f"{state['topic']} model explanations characteristics"))}


def draft_node(state: AgentState) -> dict:
    prompt = f"You are a researcher who is writing a research paper following the IEEE format, Using these inputs given from other partners, put the whole research paper with this order given : Abstract , Introduction, Related work, datasets used, methodolgy, models used. \n \n Don't add or edit anything, Just use the format and append each part using the IEEE format, here are the parts in order: Abstract :{state['abstract']} \n \n Related work:  {state['related_work']}\n \n Datasets: {state['datasets']}\n \n Methodolgy: {state['methodology']}\n \n Models Used: {state['models_used']}"
    return {"draft": invoke_text(prompt)}


def editor_node(state: AgentState) -> dict:
    prompt = f"You are an IEEE researcher who is reviewing a research paper, editing and refining it. Fix grammar mistakes and clarity while following the IEEE research paper format, here is the draft :\n\n{state['draft']},Explain what to edit in the draft (if needed) to finalize it to be published and send the review"
    return {"editor": invoke_text(prompt)}


def finalize_node(state: AgentState) -> dict:
    prompt = f"You are an IEEE researcher whose role is to re-write a draft using a reviewer's report ,follow the reviewer's refinement and instructions and rewrite the whole research paper correctly with the same draft. Here is the draft: {state['draft']} \n \n and here is the reviewr's report for editing :{state['editor']}, Rewrite the research paper correctly, don't add any notes or words as this text will be exported as a PDF"
    return {"final": invoke_text(prompt)}


builder = StateGraph(AgentState)
builder.add_node("planner", planner_node)
builder.add_node("abstract", abstract_node)
builder.add_node("related_work", related_work_node)
builder.add_node("datasets", datasets_node)
builder.add_node("methodology", methodology_node)
builder.add_node("models_used", models_used_node)
builder.add_node("writer", draft_node)
builder.add_node("editor", editor_node)
builder.add_node("final", finalize_node)

builder.add_edge(START, "planner")
builder.add_edge("planner", "abstract")
builder.add_edge("abstract", "related_work")
builder.add_edge("related_work", "datasets")
builder.add_edge("datasets", "methodology")
builder.add_edge("methodology", "models_used")
builder.add_edge("models_used", "writer")
builder.add_edge("writer", "editor")
builder.add_edge("editor", "final")
builder.add_edge("final", END)

research_graph = builder.compile()
