from __future__ import annotations
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name, disable_existing_loggers=False)
    except Exception:
        # logging config is optional; don't crash migrations over it
        pass

# We'll manage metadata later; migrations will be explicit for now
target_metadata = None

def get_url() -> str:
    # Prefer a single DATABASE_URL if provided
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    # Else, assemble from POSTGRES_* (all come from your .env via compose)
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")

    if user and password and db:
        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"

    # No secrets in code; fail fast so you don’t accidentally connect with dev/devpass
    raise RuntimeError(
        "DATABASE_URL is not set and could not compose from POSTGRES_* envs."
    )

def run_migrations_offline():
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        {"sqlalchemy.url": get_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
