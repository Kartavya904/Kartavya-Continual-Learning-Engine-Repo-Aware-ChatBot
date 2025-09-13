from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_constraints_indexes"
down_revision = "0001_init"
branch_labels = None
depends_on = None

def upgrade():
    # --- Deduplicate BEFORE adding unique constraints ---
    # Keep the lowest id per (owner,name) in repos
    op.execute("""
        DELETE FROM repos r
        USING repos r2
        WHERE r.owner = r2.owner
          AND r.name  = r2.name
          AND r.id    > r2.id
    """)

    # --- Unique constraints ---
    op.create_unique_constraint("uq_repos_owner_name", "repos", ["owner", "name"])
    op.create_unique_constraint("uq_files_repo_path", "files", ["repo_id", "path"])

    # --- Helpful secondary indexes ---
    op.create_index("ix_files_repo_id", "files", ["repo_id"], unique=False)
    op.create_index("ix_chunks_file_id", "chunks", ["file_id"], unique=False)

    # --- pgvector HNSW index for fast KNN (L2 distance) ---
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
        ON chunks USING hnsw (embedding vector_l2_ops)
    """)

def downgrade():
    op.drop_index("ix_chunks_file_id", table_name="chunks")
    op.drop_index("ix_files_repo_id", table_name="files")
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding_hnsw")
    op.drop_constraint("uq_files_repo_path", "files", type_="unique")
    op.drop_constraint("uq_repos_owner_name", "repos", type_="unique")
