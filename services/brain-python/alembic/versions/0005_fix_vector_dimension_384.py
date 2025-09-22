from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0005_fix_vector_dimension_384"
down_revision = "0004_github_accounts"
branch_labels = None
depends_on = None

def upgrade():
    # Drop the existing chunks table and recreate with correct vector dimension
    op.drop_table("chunks")
    
    # Recreate chunks table with vector(384) instead of vector(1536)
    op.execute("""
    CREATE TABLE chunks (
      id           BIGSERIAL PRIMARY KEY,
      file_id      BIGINT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
      start_line   INTEGER NOT NULL,
      end_line     INTEGER NOT NULL,
      embedding    vector(384),
      created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

def downgrade():
    # Drop and recreate with original vector(1536)
    op.drop_table("chunks")
    op.execute("""
    CREATE TABLE chunks (
      id           BIGSERIAL PRIMARY KEY,
      file_id      BIGINT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
      start_line   INTEGER NOT NULL,
      end_line     INTEGER NOT NULL,
      embedding    vector(1536),
      created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)

