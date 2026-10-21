"""gantt + finance: board_budgets, activities, finance_increments"""
import sqlalchemy as sa
from alembic import op

revision = "0003_gantt_finance"
down_revision = "0002_rbac"
branch_labels = None
depends_on = None


def upgrade():
    # create_all in main.py may already have built these tables, so every step is guarded.
    insp = sa.inspect(op.get_bind())

    if not insp.has_table("board_budgets"):
        op.create_table(
            "board_budgets",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("board_id", sa.Integer, sa.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("base_budget", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if not insp.has_table("activities"):
        op.create_table(
            "activities",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("board_id", sa.Integer, sa.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False),
            sa.Column("task_id", sa.Integer, sa.ForeignKey("tasks.id", ondelete="SET NULL")),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("phase", sa.String(100)),
            sa.Column("start_date", sa.Date, nullable=False),
            sa.Column("end_date", sa.Date, nullable=False),
            sa.Column("planned_hours", sa.Numeric(8, 2), nullable=False, server_default="0"),
            sa.Column("actual_hours", sa.Numeric(8, 2), nullable=False, server_default="0"),
            sa.Column("progress_pct", sa.Integer, nullable=False, server_default="0"),
            sa.Column("estimated_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("actual_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("depends_on", sa.JSON, nullable=False, server_default="[]"),
            sa.Column("position", sa.Integer, nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.CheckConstraint("end_date >= start_date", name="ck_activity_dates"),
            sa.CheckConstraint("progress_pct BETWEEN 0 AND 100", name="ck_activity_progress"),
        )
        op.create_index("ix_activities_board_id", "activities", ["board_id"])

    if not insp.has_table("finance_increments"):
        op.create_table(
            "finance_increments",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("board_id", sa.Integer, sa.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False),
            sa.Column("activity_id", sa.Integer, sa.ForeignKey("activities.id", ondelete="SET NULL")),
            sa.Column("phase", sa.String(100)),
            sa.Column("amount", sa.Numeric(14, 2), nullable=False),
            sa.Column("effective_date", sa.Date, nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="planned"),
            sa.Column("note", sa.String(300)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_finance_increments_board_id", "finance_increments", ["board_id"])


def downgrade():
    op.drop_table("finance_increments")
    op.drop_table("activities")
    op.drop_table("board_budgets")
