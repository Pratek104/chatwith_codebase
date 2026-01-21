from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import os
import asyncio
from datetime import datetime
from services.repo_service import RepoService

app = FastAPI(title="GitHub Repo Chat API")

# Mount static files
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize service
repo_service = RepoService()


# Background task for periodic cleanup
async def periodic_cleanup():
    """Run cleanup every 30 minutes."""
    while True:
        await asyncio.sleep(1800)  # 30 minutes
        try:
            print(f"[{datetime.now()}] Running periodic database cleanup...")
            repo_service._cleanup_old_databases()
        except Exception as e:
            print(f"Error during cleanup: {e}")


@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup."""
    asyncio.create_task(periodic_cleanup())


class QueryRequest(BaseModel):
    repo_url: HttpUrl
    query: str


class ProcessRequest(BaseModel):
    repo_url: HttpUrl


class ProcessResponse(BaseModel):
    status: str
    message: str
    repo_identifier: str


class SourceDocument(BaseModel):
    source: str
    content: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page."""
    return FileResponse("static/index.html")


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    """Serve the chat interface page."""
    return FileResponse("static/chat.html")


@app.post("/api/process", response_model=ProcessResponse)
async def process_repository(request: ProcessRequest):
    """
    Process and index a GitHub repository.
    This does all the preprocessing: cloning, parsing, chunking, and embedding.
    
    - **repo_url**: URL of the GitHub repository
    """
    try:
        repo_url = str(request.repo_url)
        
        # Process the repository (this will create the vector DB if it doesn't exist)
        success = repo_service.process_repository(repo_url)
        
        if success:
            repo_identifier = repo_service._get_repo_identifier(repo_url)
            return ProcessResponse(
                status="success",
                message="Repository processed and indexed successfully",
                repo_identifier=repo_identifier
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to process repository")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat", response_model=QueryResponse)
async def chat_with_repository(request: QueryRequest):
    """
    Chat with a GitHub repository.
    Repository must be processed first using /api/process endpoint.
    
    - **repo_url**: URL of the GitHub repository
    - **query**: Question to ask about the repository
    """
    try:
        answer, source_docs = repo_service.chat_with_repo(
            str(request.repo_url), 
            request.query
        )
        
        sources = []
        for doc in source_docs[:5]:  # Optimized to 5 sources
            sources.append(SourceDocument(
                source=doc.metadata.get('source', 'Unknown'),
                content=doc.page_content[:600],  # Optimized content length
                start_line=doc.metadata.get('start_line'),
                end_line=doc.metadata.get('end_line')
            ))
        
        return QueryResponse(answer=answer, sources=sources)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/db-status")
async def get_db_status():
    """Get status of all cached repositories."""
    from config import settings
    
    if not os.path.exists(settings.CHROMA_BASE_DIR):
        return {"databases": [], "total": 0}
    
    databases = []
    for item in os.listdir(settings.CHROMA_BASE_DIR):
        item_path = os.path.join(settings.CHROMA_BASE_DIR, item)
        
        if os.path.isdir(item_path):
            age = repo_service._get_db_age(item)
            databases.append({
                "name": item,
                "age_hours": round(age, 2) if age else None,
                "expires_in_hours": round(settings.DB_CLEANUP_HOURS - age, 2) if age else None,
                "size_mb": round(sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, _, filenames in os.walk(item_path)
                    for filename in filenames
                ) / (1024 * 1024), 2)
            })
    
    return {
        "databases": databases,
        "total": len(databases),
        "cleanup_threshold_hours": settings.DB_CLEANUP_HOURS
    }


@app.post("/api/cleanup")
async def manual_cleanup():
    """Manually trigger database cleanup."""
    try:
        repo_service._cleanup_old_databases()
        return {"status": "success", "message": "Cleanup completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/favicon.ico")
async def favicon():
    """Return a simple favicon response to avoid 404 errors."""
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)