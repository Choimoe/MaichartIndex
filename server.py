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

import sys
import socket
import random

def get_random_port(start=50000, end=60000):
    """Find a random available port in range."""
    for _ in range(50):
        port = random.randint(start, end)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue
    return 0 # Fail code


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

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
app.mount("/", StaticFiles(directory=resource_path("static"), html=True), name="static")


if __name__ == "__main__":
    is_frozen = getattr(sys, 'frozen', False)
    # Reload only if NOT frozen (development mode)
    if is_frozen:
        # Pass app object directly in frozen mode to avoid import issues
        port = get_random_port()
        print(f"Starting server at http://0.0.0.0:{port}")
        uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
    else:
        # String import string for reload to work in dev
        uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
