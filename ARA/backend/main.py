# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException
# pyrefly: ignore [missing-import]
from pydantic import BaseModel
# pyrefly: ignore [missing-import]
import uvicorn
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine, Column, Integer, String, Text
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import declarative_base
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker
# pyrefly: ignore [missing-import]
from agents import research_graph

DATABASE_URL = "sqlite:///./research_history.db" 
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ResearchHistory(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True, index=True)
    query = Column(String, index=True)
    report = Column(Text)

Base.metadata.create_all(bind=engine)

# FastAPI App
app = FastAPI(title="Autonomous AI Research Assistant Team API")

class ResearchRequest(BaseModel):
    query: str

class ResearchResponse(BaseModel):
    final_report: str

@app.post("/research", response_model=ResearchResponse)
async def conduct_research(request: ResearchRequest):
    try:
        initial_state = {
            "topic": request.query,
            "plan": "",
            "abstract": "",
            "introduction": "",
            "related_work": "",
            "datasets": "",
            "methodology": "",
            "models_used": "",
            "draft": "",
            "editor": "",
            "final": "",
        }
        
        # Invoke LangGraph Multi-Agent Workflow
        final_state = research_graph.invoke(initial_state)
        report = final_state.get("final", "No report generated.")
        
        # Save to Database
        db = SessionLocal()
        new_history = ResearchHistory(query=request.query, report=report)
        db.add(new_history)
        db.commit()
        db.close()

        return ResearchResponse(final_report=report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
