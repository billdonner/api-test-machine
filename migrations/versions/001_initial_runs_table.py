"""Initial runs table

Revision ID: 001
Revises:
Create Date: 2025-01-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False, index=True),
        sa.Column("url", sa.Text()),
        sa.Column("method", sa.String(10)),
        sa.Column("total_requests", sa.Integer()),
        sa.Column("concurrency", sa.Integer()),
        sa.Column("status", sa.String(20), nullable=False, index=True),
        sa.Column("started_at", sa.DateTime(), index=True),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), index=True),
        sa.Column("passed", sa.Boolean()),
        sa.Column("requests_completed", sa.Integer(), default=0),
        sa.Column("error_message", sa.Text()),
        sa.Column("spec_json", sa.JSON(), nullable=False),
        sa.Column("metrics_json", sa.JSON()),
        sa.Column("failure_reasons_json", sa.JSON()),
        sa.Column("endpoint_metrics_json", sa.JSON()),
        sa.Column("sampled_requests_json", sa.JSON()),
    )


def downgrade() -> None:
    op.drop_table("runs")
