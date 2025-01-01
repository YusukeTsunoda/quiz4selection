"""Add user_id to QuizAttempt

Revision ID: c13a89d02f07
Revises: 
Create Date: 2024-01-01 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c13a89d02f07'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # デフォルトユーザーを作成
    op.execute("""
        INSERT INTO users (id, email, username, is_admin)
        VALUES ('default-user-id', 'default@example.com', 'default_user', false)
        ON CONFLICT (id) DO NOTHING
    """)
    
    # 既存のレコードにデフォルトのユーザーIDを設定
    op.execute("UPDATE quiz_attempts SET user_id = 'default-user-id' WHERE user_id IS NULL")
    
    # user_idカラムをNOT NULLに設定
    with op.batch_alter_table('quiz_attempts', schema=None) as batch_op:
        batch_op.alter_column('user_id',
                            existing_type=sa.String(length=36),
                            nullable=False)
        batch_op.alter_column('score',
                            existing_type=sa.INTEGER(),
                            nullable=False)
        batch_op.alter_column('total_questions',
                            existing_type=sa.INTEGER(),
                            nullable=False)


def downgrade():
    with op.batch_alter_table('quiz_attempts', schema=None) as batch_op:
        batch_op.alter_column('user_id',
                            existing_type=sa.String(length=36),
                            nullable=True)
        batch_op.alter_column('score',
                            existing_type=sa.INTEGER(),
                            nullable=True)
        batch_op.alter_column('total_questions',
                            existing_type=sa.INTEGER(),
                            nullable=True)
    
    # デフォルトユーザーを削除
    op.execute("DELETE FROM users WHERE id = 'default-user-id'")
