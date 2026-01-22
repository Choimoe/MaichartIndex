from fastapi import FastAPI, UploadFile, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from contextlib import asynccontextmanager
import uvicorn
import os
import shutil
import json

from simai_search.search import RhythmSearcher

# Searcher
DB_PATH = "maichart.db"  # Hardcoded as in main.py
searcher = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global searcher
    if os.path.exists(DB_PATH):
        try:
            searcher = RhythmSearcher(DB_PATH)
            print("Searcher initialized.")
        except Exception as e:
            print(f"Failed to initialize searcher: {e}")
            searcher = None
    else:
        print("Database not found. Please run 'python main.py build' first.")
    yield
    # Clean up if needed

app = FastAPI(title="Maichart Index Search", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/api/search")
def search(
    query: str,
    level_min: Optional[float] = None,
    level_max: Optional[float] = None,
    diff: Optional[str] = None, # Comma separated
    designer: Optional[str] = None,
    bpm_min: Optional[float] = None,
    bpm_max: Optional[float] = None
):
    if not searcher:
        return {"error": "Searcher not initialized. DB might be missing or rebuilding."}
    
    difficulties = []
    if diff:
        diff_map = {"easy": 1, "basic": 2, "advanced": 3, "expert": 4, "master": 5, "remaster": 6}
        for d in diff.split(','):
             d_lower = d.lower().strip()
             if d_lower in diff_map:
                 difficulties.append(diff_map[d_lower])
    
    results = searcher.search(
        query,
        level_min=level_min,
        level_max=level_max,
        difficulties=difficulties,
        designer=designer,
        bpm_min=bpm_min,
        bpm_max=bpm_max
    )
    
    # Format results
    json_results = []
    for title, diff_name, level, chart_id, snippet, degree in results:
        json_results.append({
            "title": title,
            "difficulty": diff_name,
            "level": level,
            "id": chart_id,
            "snippet": snippet,
            "match_degree": degree
        })
        
    return {"count": len(results), "results": json_results}

# Mount static files
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
