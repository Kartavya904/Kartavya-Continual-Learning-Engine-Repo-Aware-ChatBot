from __future__ import annotations

import os
from typing import Dict, List

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base, Mapped, mapped_column
import sqlalchemy as sa

# --- Config ---------------------------------------------------------------

def _resolve_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    if user and password and db:
        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
    raise RuntimeError("Missing DB env: set DATABASE_URL or POSTGRES_* vars")

EMBED_DIM = int(os.environ["EMBED_DIM"])

engine: Engine = create_engine(_resolve_db_url(), pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ORM (User for auth) --------------------------------------------------

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    created_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)
    email: Mapped[str | None] = mapped_column(sa.String(255))
    first_name: Mapped[str | None] = mapped_column(sa.String(120))
    last_name: Mapped[str | None] = mapped_column(sa.String(120))
    password_hash: Mapped[str | None] = mapped_column(sa.String(255))
    phone: Mapped[str | None] = mapped_column(sa.String(40))
    address: Mapped[str | None] = mapped_column(sa.Text)

# --- Health ---------------------------------------------------------------

def probe_db() -> Dict[str, str]:
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar_one()
    return {"ok": "true", "db_version": version}

def schema_health() -> dict:
    with engine.connect() as conn:
        ext = conn.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='vector')")).scalar_one()
        tables = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public'
                  AND table_name IN ('users','repos','files','chunks','alembic_version')
                ORDER BY table_name
            """)
        ).scalars().all()
    ok = bool(ext and all(t in tables for t in ("users", "repos", "files", "chunks")))
    return {"ok": ok, "vector_ext": bool(ext), "tables": tables}

# --- Vector helpers -------------------------------------------------------

def _vec_literal(vec: List[float], dim: int = EMBED_DIM) -> str:
    if len(vec) != dim:
        raise ValueError(f"vector must be length {dim}, got {len(vec)}")
    return "[" + ",".join(f"{x:.10g}" for x in vec) + "]"

# --- Writes ---------------------------------------------------------------

def insert_stub_chunk(owner: str, name: str, path: str, start_line: int, end_line: int) -> dict:
    with engine.begin() as conn:
        repo_id = conn.execute(
            text("""
                INSERT INTO repos(owner, name, default_branch)
                VALUES (:owner, :name, 'main')
                ON CONFLICT (owner, name) DO UPDATE
                SET default_branch = COALESCE(EXCLUDED.default_branch, repos.default_branch)
                RETURNING id
            """),
            {"owner": owner, "name": name},
        ).scalar_one()

        file_id = conn.execute(
            text("""
                INSERT INTO files(repo_id, path, commit, content_hash)
                VALUES (:repo_id, :path, NULL, NULL)
                ON CONFLICT (repo_id, path) DO UPDATE
                SET commit = COALESCE(EXCLUDED.commit, files.commit),
                    content_hash = COALESCE(EXCLUDED.content_hash, files.content_hash)
                RETURNING id
            """),
            {"repo_id": repo_id, "path": path},
        ).scalar_one()

        chunk_id = conn.execute(
            text("""
                INSERT INTO chunks(file_id, start_line, end_line, embedding)
                VALUES (:file_id, :start, :end, NULL)
                RETURNING id
            """),
            {"file_id": file_id, "start": start_line, "end": end_line},
        ).scalar_one()

    return {"repo_id": repo_id, "file_id": file_id, "chunk_id": chunk_id}

def insert_chunk_with_vec(owner: str, name: str, path: str, start_line: int, end_line: int, embedding: List[float]) -> dict:
    vec = _vec_literal(embedding, EMBED_DIM)
    with engine.begin() as conn:
        repo_id = conn.execute(
            text("""
                INSERT INTO repos(owner, name, default_branch)
                VALUES (:owner, :name, 'main')
                ON CONFLICT (owner, name) DO UPDATE
                SET default_branch = COALESCE(EXCLUDED.default_branch, repos.default_branch)
                RETURNING id
            """),
            {"owner": owner, "name": name},
        ).scalar_one()

        file_id = conn.execute(
            text("""
                INSERT INTO files(repo_id, path, commit, content_hash)
                VALUES (:repo_id, :path, NULL, NULL)
                ON CONFLICT (repo_id, path) DO UPDATE
                SET commit = COALESCE(EXCLUDED.commit, files.commit),
                    content_hash = COALESCE(EXCLUDED.content_hash, files.content_hash)
                RETURNING id
            """),
            {"repo_id": repo_id, "path": path},
        ).scalar_one()

        chunk_id = conn.execute(
            text(f"""
                INSERT INTO chunks(file_id, start_line, end_line, embedding)
                VALUES (:file_id, :start, :end, (:embedding)::vector({EMBED_DIM}))
                RETURNING id
            """),
            {"file_id": file_id, "start": start_line, "end": end_line, "embedding": vec},
        ).scalar_one()

    return {"repo_id": repo_id, "file_id": file_id, "chunk_id": chunk_id}

# --- KNN Retrieval --------------------------------------------------------

def knn_paths(query_vec: List[float], k: int = 5) -> List[dict]:
    q = _vec_literal(query_vec, EMBED_DIM)
    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT
                    f.path,
                    c.start_line,
                    c.end_line,
                    (c.embedding <-> (:q)::vector({EMBED_DIM})) AS dist,
                    c.id AS chunk_id
                FROM chunks c
                JOIN files f ON f.id = c.file_id
                WHERE c.embedding IS NOT NULL
                ORDER BY c.embedding <-> (:q)::vector({EMBED_DIM})
                LIMIT :k
            """),
            {"q": q, "k": k},
        ).mappings().all()
    return [dict(r) for r in rows]

def knn_from_last(k: int = 5) -> List[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                WITH q AS (
                    SELECT embedding
                    FROM chunks
                    WHERE embedding IS NOT NULL
                    ORDER BY id DESC
                    LIMIT 1
                )
                SELECT
                    f.path,
                    c.start_line,
                    c.end_line,
                    (c.embedding <-> q.embedding) AS dist,
                    c.id AS chunk_id
                FROM chunks c
                CROSS JOIN q
                JOIN files f ON f.id = c.file_id
                WHERE c.embedding IS NOT NULL
                ORDER BY c.embedding <-> q.embedding
                LIMIT :k
            """),
            {"k": k},
        ).mappings().all()
    return [dict(r) for r in rows]
