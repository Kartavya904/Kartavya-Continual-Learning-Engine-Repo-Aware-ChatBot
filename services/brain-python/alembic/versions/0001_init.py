from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("email", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # repos
    op.create_table(
        "repos",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("owner", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("default_branch", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # files
    op.create_table(
        "files",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("repo_id", sa.BigInteger, sa.ForeignKey("repos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("commit", sa.Text, nullable=True),
        sa.Column("content_hash", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # chunks (embedding = vector(1536); adjust later if you pick a different dim)
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

def downgrade():
    op.drop_table("chunks")
    op.drop_table("files")
    op.drop_table("repos")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
