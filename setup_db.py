from app import app, db
import logging
import sqlalchemy as sa

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

with app.app_context():
    try:
        # PostgreSQLデータベースの初期化
        db.create_all()
        logger.info("PostgreSQLデータベーステーブルを作成しました")
        print("PostgreSQLデータベーステーブルが正常に作成されました")
        
        # テーブル名の確認
        inspector = sa.inspect(db.engine)
        table_names = inspector.get_table_names()
        logger.info(f"作成されたテーブル: {table_names}")
        print(f"作成されたテーブル: {table_names}")
        
        # シーケンスの確認
        sequences = []
        with db.engine.connect() as conn:
            result = conn.execute(sa.text("SELECT relname FROM pg_class WHERE relkind = 'S';"))
            sequences = [row[0] for row in result]
        
        logger.info(f"作成されたシーケンス: {sequences}")
        print(f"作成されたシーケンス: {sequences}")
    except Exception as e:
        logger.error(f"PostgreSQLデータベース初期化エラー: {e}")
        print(f"エラー: {e}") 