"""Added unknown_cards table

Revision ID: a49b0d49e3db
Revises: 26408bbc57d0
Create Date: 2024-01-28 15:46:02.731456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a49b0d49e3db"
down_revision: Union[str, None] = "26408bbc57d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "unknown_cards",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("card_UUID", sa.String(8), nullable=False),
        sa.Column("timestamp", sa.Float, nullable=False),
        sa.Column("machine_id", sa.Integer, sa.ForeignKey("machines.machine_id"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("unknown_cards")
