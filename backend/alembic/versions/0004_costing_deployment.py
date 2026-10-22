"""costing + deployment document: expenses, deployment_plans, deployment_docs"""
import sqlalchemy as sa
from alembic import op

revision = "0004_costing_deployment"
down_revision = "0003_gantt_finance"
branch_labels = None
depends_on = None


def upgrade():
    # create_all in main.py may already have built these tables, so every step is guarded.
    insp = sa.inspect(op.get_bind())

    if not insp.has_table("expenses"):
        op.create_table(
            "expenses",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("board_id", sa.Integer, sa.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False),
            sa.Column("activity_id", sa.Integer, sa.ForeignKey("activities.id", ondelete="SET NULL")),
            sa.Column("category", sa.String(30), nullable=False),
            sa.Column("description", sa.String(300), nullable=False),
            sa.Column("estimated_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("actual_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("incurred_on", sa.Date),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_expenses_board_id", "expenses", ["board_id"])

    if not insp.has_table("deployment_plans"):
        op.create_table(
            "deployment_plans",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("board_id", sa.Integer, sa.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version", sa.Integer, nullable=False),
            sa.Column("stack", sa.JSON, nullable=False),
            sa.Column("selected", sa.JSON, nullable=False),
            sa.Column("options", sa.JSON, nullable=False),
            sa.Column("totals", sa.JSON, nullable=False),
            sa.Column("document_md", sa.Text, nullable=False),
            sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_deployment_plans_board_id", "deployment_plans", ["board_id"])

    if not insp.has_table("deployment_docs"):
        op.create_table(
            "deployment_docs",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("board_id", sa.Integer, sa.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("category", sa.String(20), nullable=False, server_default="supporting"),
            sa.Column("content", sa.Text, nullable=False, server_default=""),
            sa.Column("url", sa.String(500)),
            sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_deployment_docs_board_id", "deployment_docs", ["board_id"])


def downgrade():
    op.drop_table("deployment_docs")
    op.drop_table("deployment_plans")
    op.drop_table("expenses")
