"""merge heads

Revision ID: merge_heads
Revises: data_migration_001, rename_quiz_history_column
Create Date: 2024-01-20 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads'
down_revision = ('data_migration_001', 'rename_quiz_history_column')
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass 