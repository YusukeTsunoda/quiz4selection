"""Convert existing quiz history data

Revision ID: data_migration_001
Revises: 806d3485a468
Create Date: 2024-01-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
import json

# revision identifiers, used by Alembic
revision = 'data_migration_001'
down_revision = '806d3485a468'
branch_labels = None
depends_on = None

def upgrade():
    # テーブルの定義
    quiz_attempts = table('quiz_attempts',
        column('id', sa.Integer),
        column('_quiz_history', sa.JSON)
    )

    # データベース接続
    connection = op.get_bind()

    # 全てのクイズ履歴を取得
    results = connection.execute(
        sa.select([quiz_attempts.c.id, quiz_attempts.c._quiz_history])
    ).fetchall()

    # データを更新
    for result in results:
        quiz_id = result[0]
        quiz_history = result[1]

        # quiz_historyがNoneでない場合のみ処理
        if quiz_history is not None:
            try:
                # 既にJSON形式の場合はスキップ
                if isinstance(quiz_history, dict) or isinstance(quiz_history, list):
                    continue

                # 文字列をJSONとしてパース
                parsed_history = json.loads(quiz_history) if isinstance(quiz_history, str) else quiz_history

                # データを更新
                connection.execute(
                    quiz_attempts.update().
                    where(quiz_attempts.c.id == quiz_id).
                    values(_quiz_history=json.dumps(parsed_history))
                )
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error processing quiz_id {quiz_id}: {e}")
                continue

def downgrade():
    pass 