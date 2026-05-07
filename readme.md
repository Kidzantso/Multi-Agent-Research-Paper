# Multi-Agent System for Research Paper Generation

This project provides a Jupyter Notebook (`Multi_agent_system_for_reasearch.ipynb`) that implements a multi-agent system to automatically generate an IEEE-format research paper draft on a given topic. It utilizes **LangGraph** to coordinate a team of AI agents and a **Telegram Bot** to provide an accessible user interface.

## Overview

The notebook sets up a sophisticated pipeline where different specialized AI agents work collaboratively to construct a research paper. The final output is formatted as a PDF document and delivered directly to the user via a Telegram bot. 

The system runs locally using **Ollama** to serve the LLM (`Eomer/gpt-3.5-turbo` used as an example, but adaptable to others).

## Architecture & Workflow

The core of the system is a `StateGraph` built with `langgraph`, defining a sequential flow of tasks handled by specific agents. The `AgentState` passes information from one node to the next.

The workflow consists of the following agents/nodes:
1. **Planner (`planner_node`)**: Creates a detailed outline for the research paper based on the user's topic, including sections for related work and datasets.
2. **Abstract Writer (`abstract_node`)**: Generates a concise abstract summarizing the paper's intent and models used.
3. **Literature Reviewer (`related_work_node`)**: Writes summaries of related research papers specified in the outline.
4. **Dataset Describer (`datasets_node`)**: Details the datasets (features, records, targets) mentioned in the plan.
5. **Methodologist (`methodology_node`)**: Drafts the methodology section, including data preprocessing steps and evaluation metrics.
6. **Model Describer (`models_used_node`)**: Explains the specific models chosen in the methodology section.
7. **Draft Writer (`draft_node`)**: Assembles all previously generated sections into a cohesive IEEE format draft.
8. **Editor (`editor_node`)**: Reviews the draft, correcting grammar and suggesting improvements for clarity and adherence to the IEEE format.
9. **Finalizer (`finalize_node`)**: Refines and rewrites the final research paper based on the editor's feedback.

## Features

- **Local LLM Execution:** Uses Ollama to run models locally, ensuring privacy and reducing API costs.
- **Agentic Workflow:** LangGraph orchestrates multiple LLM calls with specific system prompts to break down the complex task of paper writing.
- **Telegram Bot Integration:** Users interact with the system simply by sending a topic as a message to a Telegram bot.
- **Automated PDF Generation:** The `fpdf` library converts the final generated text into a formatted PDF document.

## Requirements

The notebook installs the following key dependencies:
- `langchain_openai`: For interacting with the Ollama API using Langchain's OpenAI-compatible interface.
- `langgraph`: For building the multi-agent state graph.
- `python-telegram-bot`: For creating the Telegram bot interface.
- `fpdf`: For generating the final PDF file.
- `ollama`: System-level installation required for serving the local LLM.

## Setup and Usage

1. **Install Ollama**: The notebook includes cells to install Ollama and pull the required model (e.g., `!ollama pull Eomer/gpt-3.5-turbo`). Ensure the Ollama server is running.
2. **Configure Telegram Bot**: 
   - Create a bot using BotFather on Telegram.
   - Obtain the Bot Token.
   - Paste the token into the `TOKEN = ''` variable in the notebook.
3. **Run the Notebook**: Execute all cells in the notebook. The final cell will start the Telegram bot polling.
4. **Interact**: Open your bot on Telegram, send `/start`, and then type a research topic (e.g., "Predictive Modeling of Bitcoin Prices"). The bot will process the request through the LangGraph and return a PDF.
