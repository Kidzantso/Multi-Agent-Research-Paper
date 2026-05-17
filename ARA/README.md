# Autonomous AI Research Assistant Team

This project contains a multi-agent system built with **FastAPI** (Backend), **Streamlit** (Frontend), and **LangGraph**. It automates the process of researching, analyzing, synthesizing, and formatting reports with citations on given topics.

## Project Structure
- `backend/`
  - `agents.py`: Contains the LangGraph implementation of the Research Coordinator, Web Search, Content Analyzer, Synthesis, and Citation agents using Gemini.
  - `main.py`: The FastAPI application that exposes the `/research` endpoint and stores research history using SQLite (easily swappable to PostgreSQL).
  - `requirements.txt`: Python dependencies for the backend.
- `frontend/`
  - `app.py`: The Streamlit interface to submit queries and view/download the generated Markdown reports.
  - `requirements.txt`: Python dependencies for the frontend.

## How to Run

### 1. Backend
Open a terminal and navigate to the backend directory:
```bash
cd backend
pip install -r requirements.txt
python main.py
```
This will start the FastAPI server on `http://0.0.0.0:8002`.

### 2. Frontend
Open a new terminal and navigate to the frontend directory:
```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```
This will open the Streamlit UI in your browser where you can submit your research topics.

## Notes
- The system uses **Groq API** for synthesis and analysis via the provided API key.
- **ChromaDB** is used to locally index raw content.
- **arXiv API** is integrated for fetching academic papers. For general web search, you can expand `agents.py` with `Serper` and web scraping tools (e.g., BeautifulSoup) as needed.
