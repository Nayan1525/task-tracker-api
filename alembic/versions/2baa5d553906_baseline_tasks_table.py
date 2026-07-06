"""baseline tasks

Revision ID: 2baa5d553906
Revises: 
Create Date: 2026-07-06 16:43:10.845013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2baa5d553906'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Hand-trimmed from autogenerate output: autogenerate diffed against the
    # full model metadata (Task + Comment) and proposed `comments` too, but
    # that table is the next migration's job, not this "day zero" baseline
    # (Migration Requirements) — trimmed here rather than committed raw.
    op.create_table('tasks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('TODO', 'IN_PROGRESS', 'DONE', name='task_status', native_enum=False), nullable=False),
    sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='task_priority', native_enum=False), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tasks_status', 'tasks', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_tasks_status', table_name='tasks')
    op.drop_table('tasks')
