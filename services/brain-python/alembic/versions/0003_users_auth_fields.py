from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_users_auth_fields"
down_revision = "0002_constraints_indexes"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # If the table doesn't exist (unlikely here), bail early.
    if not insp.has_table("users"):
        # Optional: create from scratch, or just return and let the "create" migration handle it.
        # Keeping it simple: just return to avoid surprises.
        return

    cols = {c["name"] for c in insp.get_columns("users")}
    idxs = {i["name"] for i in insp.get_indexes("users")}

    def add_col(name: str, type_, nullable=True):
        if name not in cols:
            op.add_column("users", sa.Column(name, type_, nullable=nullable))

    # Add fields if missing. If your table already has rows, adding NOT NULL
    # without defaults can fail — so we add as nullable=True for safety in dev.
    add_col("first_name", sa.String(length=120), nullable=True)   # tighten later with data present
    add_col("last_name", sa.String(length=120), nullable=True)
    add_col("email", sa.String(length=255), nullable=True)
    add_col("password_hash", sa.String(length=255), nullable=True)
    add_col("phone", sa.String(length=40), nullable=True)
    add_col("address", sa.Text(), nullable=True)

    # Ensure a unique index/constraint on email exists (name may vary)
    if "uq_users_email" not in idxs and "ix_users_email_unique" not in idxs:
        op.create_index("uq_users_email", "users", ["email"], unique=True)

def downgrade():
    # Be conservative on downgrade: drop the unique index if we created it.
    try:
        op.drop_index("uq_users_email", table_name="users")
    except Exception:
        pass
    for c in ["address", "phone", "password_hash", "email", "last_name", "first_name"]:
        try:
            op.drop_column("users", c)
        except Exception:
            pass
