FROM python:3.13-slim

# Optional build deps if bcrypt wheels ever fail:
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential libffi-dev && \
#     rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps from project metadata
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy app + migrations
COPY app ./app
COPY alembic.ini .
COPY alembic ./alembic

EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--reload"]
