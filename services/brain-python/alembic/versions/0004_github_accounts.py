from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_github_accounts"
down_revision = "0003_users_auth_fields"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "github_accounts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("gh_user_id", sa.BigInteger, unique=True, nullable=False),
        sa.Column("login", sa.Text, unique=True, nullable=False),
        sa.Column("name", sa.Text),
        sa.Column("avatar_url", sa.Text),
        sa.Column("access_token_enc", sa.LargeBinary, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

def downgrade():
    op.drop_table("github_accounts")