import os
from typing import TypedDict, List, Dict, Any
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv, find_dotenv
# pyrefly: ignore [missing-import]
from langgraph.graph import StateGraph, START, END
# pyrefly: ignore [missing-import]
# pyrefly: ignore [missing-import]
from langchain_groq import ChatGroq
# pyrefly: ignore [missing-import]
from langchain_core.messages import HumanMessage
# pyrefly: ignore [missing-import]
import arxiv
# pyrefly: ignore [missing-import]
import chromadb

# Load environment variables from .env
load_dotenv(find_dotenv())

# Configuration
GROQ_API_KEY = os.getenv("GROQ_KEY") or os.getenv("GROQ_API_KEY")

# Initialize Groq
llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=GROQ_API_KEY, temperature=0.2)

class ResearchState(TypedDict):
    query: str
    plan: str
    search_queries: List[str]
    raw_content: List[Dict[str, str]]
    analyzed_content: str
    report_draft: str
    final_report: str

def coordinator_node(state: ResearchState) -> dict:
    print("--- COORDINATOR AGENT ---")
    prompt = f"You are a research coordinator planning a literature review. Create a detailed search plan for the following topic: '{state['query']}'. Return a plan identifying key sub-topics and a list of specific search queries to find relevant academic papers."
    response = llm.invoke([HumanMessage(content=prompt)])
    # Create simple search queries for now
    search_queries = [state['query'] + " latest academic papers", state['query'] + " literature review"]
    return {"plan": response.content, "search_queries": search_queries}

def search_node(state: ResearchState) -> dict:
    print("--- WEB SEARCH AGENT ---")
    raw_content = []
    
    try:
        # Use arxiv API for academic papers
        client = arxiv.Client()
        search = arxiv.Search(
            query = state['query'],
            max_results = 3,
            sort_by = arxiv.SortCriterion.Relevance
        )
        for result in client.results(search):
            raw_content.append({"source": result.entry_id, "text": result.summary})
    except Exception as e:
        print(f"arXiv search error: {e}")
        raw_content.append({"source": "Error", "text": "Failed to fetch from arXiv."})
    
    # (In a full production app, integrate Serper API and BeautifulSoup here for general web scraping)
    
    return {"raw_content": raw_content}

def analyzer_node(state: ResearchState) -> dict:
    print("--- CONTENT ANALYZER AGENT ---")
    # Use ChromaDB for source indexing
    client = chromadb.Client()
    try:
        collection = client.create_collection("research_sources")
    except:
        try:
            collection = client.get_collection("research_sources")
        except:
            pass # Fallback if Chroma fails
    
    docs = []
    metas = []
    ids = []
    for i, content in enumerate(state['raw_content']):
        docs.append(content['text'])
        metas.append({"source": content['source']})
        ids.append(f"doc_{i}")
        
    if docs:
        try:
            collection.add(documents=docs, metadatas=metas, ids=ids)
        except Exception as e:
            print(f"ChromaDB indexing error: {e}")
        
    prompt = f"You are a researcher participating in writing a literature review. Analyze the following raw content from research papers related to: '{state['query']}'. \nFor each paper, extract and summarize:\n1. The authors and source\n2. Models or methodology used\n3. Datasets utilized\n4. Each study's conclusion\n5. Each study's limitations\n\nWrite a structured summary for each paper.\nRaw Content:\n{state['raw_content']}"
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"analyzed_content": response.content}

def synthesis_node(state: ResearchState) -> dict:
    print("--- SYNTHESIS AGENT ---")
    prompt = f"You are a researcher writing a literature review. Using these analyzed summaries of papers, write a cohesive and comprehensive literature review draft for the topic '{state['query']}'. \nOrganize the review thematically, comparing and contrasting the studies. Weave them into a continuous narrative that discusses the models, datasets, conclusions, and limitations of the current research landscape.\n\nAnalyzed Summaries:\n{state['analyzed_content']}"
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"report_draft": response.content}

def citation_node(state: ResearchState) -> dict:
    print("--- CITATION MANAGER AGENT ---")
    prompt = f"You are an academic editor reviewing a literature review draft. Fix grammar mistakes, ensure clarity, and format it properly. Ensure proper academic citations are included in the text and append a 'References' section at the end based on the available sources. Output the final literature review in Markdown format.\n\nLiterature Review Draft:\n{state['report_draft']}\n\nSources available:\n{state['raw_content']}"
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"final_report": response.content}

# Build Graph
builder = StateGraph(ResearchState)
builder.add_node("coordinator", coordinator_node)
builder.add_node("searcher", search_node)
builder.add_node("analyzer", analyzer_node)
builder.add_node("synthesizer", synthesis_node)
builder.add_node("citator", citation_node)

builder.add_edge(START, "coordinator")
builder.add_edge("coordinator", "searcher")
builder.add_edge("searcher", "analyzer")
builder.add_edge("analyzer", "synthesizer")
builder.add_edge("synthesizer", "citator")
builder.add_edge("citator", END)

research_graph = builder.compile()
