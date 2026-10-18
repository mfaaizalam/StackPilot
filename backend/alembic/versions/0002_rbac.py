"""rbac: board_members, board_invitations, board_activity (+ backfill owners as admin)"""
import sqlalchemy as sa
from alembic import op

revision = "0002_rbac"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade():
    insp = sa.inspect(op.get_bind())

    # `create_all` in main.py may already have created these tables on app start,
    # so every step is guarded: running this twice, or after create_all, is safe.
    if not insp.has_table("board_members"):
        op.create_table(
            "board_members",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("board_id", sa.Integer, sa.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("invited_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("board_id", "user_id", name="uq_board_user"),
        )
        op.create_index("ix_board_members_board_id", "board_members", ["board_id"])
        op.create_index("ix_board_members_user_id", "board_members", ["user_id"])

    if not insp.has_table("board_invitations"):
        op.create_table(
            "board_invitations",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("board_id", sa.Integer, sa.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("token", sa.String(64), nullable=False, unique=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("invited_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_board_invitations_board_id", "board_invitations", ["board_id"])
        op.create_index("ix_board_invitations_email", "board_invitations", ["email"])

    if not insp.has_table("board_activity"):
        op.create_table(
            "board_activity",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("board_id", sa.Integer, sa.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("action", sa.String(50), nullable=False),
            sa.Column("entity_type", sa.String(30)),
            sa.Column("entity_id", sa.Integer),
            sa.Column("summary", sa.Text, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_board_activity_board_id", "board_activity", ["board_id"])
        op.create_index("ix_board_activity_created_at", "board_activity", ["created_at"])

    # Backfill: every existing board's owner becomes its admin (your column is boards.owner_id).
    op.execute("""
        INSERT INTO board_members (board_id, user_id, role)
        SELECT b.id, b.owner_id, 'admin' FROM boards b
        WHERE b.owner_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM board_members m
                          WHERE m.board_id = b.id AND m.user_id = b.owner_id)
    """)


def downgrade():
    op.drop_table("board_activity")
    op.drop_table("board_invitations")
    op.drop_table("board_members")