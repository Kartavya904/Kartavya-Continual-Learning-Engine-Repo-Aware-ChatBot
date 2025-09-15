import os, random
from typing import List, Annotated

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .db import (
    probe_db, schema_health,
    insert_chunk_with_vec, knn_paths, knn_from_last, EMBED_DIM
)
from .auth import router as auth_router

app = FastAPI()

WEB_ORIGIN = os.getenv("WEB_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[WEB_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz(): return {"ok": True}

@app.get("/db-healthz")
def db_healthz(): return probe_db()

@app.get("/schema-healthz")
def schema_healthz(): return schema_health()

Embedding = Annotated[List[float], Field(min_items=EMBED_DIM, max_items=EMBED_DIM)]

class EmbedVecIn(BaseModel):
    owner: str
    name: str
    path: str
    start_line: int = 1
    end_line: int = 20
    embedding: Embedding

@app.post("/embed-vector")
def embed_vector(body: EmbedVecIn):
    try:
        ids = insert_chunk_with_vec(
            owner=body.owner, name=body.name, path=body.path,
            start_line=body.start_line, end_line=body.end_line, embedding=body.embedding,
        )
        return {"ok": True, **ids}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.post("/dev/embed-random")
def embed_random(owner: str, name: str, path: str, start_line: int = 1, end_line: int = 20):
    if os.getenv("DEV", "1") != "1":
        raise HTTPException(status_code=403, detail="DEV helpers disabled")
    rand_vec = [random.random() for _ in range(EMBED_DIM)]
    ids = insert_chunk_with_vec(owner, name, path, start_line, end_line, rand_vec)
    return {"ok": True, **ids}

class SearchIn(BaseModel):
    query: Embedding
    k: int = 5

@app.post("/search")
def search(body: SearchIn):
    try:
        return {"results": knn_paths(body.query, body.k)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.get("/dev/search-last")
def search_last(k: int = 5):
    return {"results": knn_from_last(k)}

# auth routes
app.include_router(auth_router)
