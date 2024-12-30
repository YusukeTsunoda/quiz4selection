import os
import logging
import json
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def test_database_connection(app):
    """データベース接続をテストする関数"""
    try:
        engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("Database connection test successful")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database connection test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in database connection test: {e}")
        return False

class Config:
    """アプリケーションの設定クラス"""
    # セッション設定
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    
    # 環境設定
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    VERCEL_ENV = os.environ.get('VERCEL_ENV')
    
    # データベース設定
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQLAlchemy接続プール設定
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,  # 接続プールのサイズ
        'max_overflow': 10,  # 最大追加接続数
        'pool_timeout': 30,  # 接続タイムアウト（秒）
        'pool_recycle': 1800,  # 接続再利用時間（秒）
    }
    
    def __init__(self):
        # 環境変数の状態をログ出力
        logger.info(json.dumps({
            'event': 'environment_check',
            'vercel_env': os.environ.get('VERCEL_ENV'),
            'database_url_set': bool(os.environ.get('DATABASE_URL')),
            'local_database_url_set': bool(os.environ.get('LOCAL_DATABASE_URL'))
        }))
        
        # 開発環境の設定
        if self.FLASK_ENV == 'development' or self.VERCEL_ENV == 'development':
            logger.info("Using LOCAL_DATABASE_URL for development")
            database_url = os.environ.get('LOCAL_DATABASE_URL')
            if not database_url:
                raise ValueError("LOCAL_DATABASE_URL is not set in development environment")
            self.SQLALCHEMY_DATABASE_URI = database_url
            self.DEBUG = True
            self.DEVELOPMENT = True
        # 本番環境の設定
        else:
            logger.info("Using DATABASE_URL for production")
            database_url = os.environ.get('DATABASE_URL')
            if not database_url:
                raise ValueError("DATABASE_URL is not set in production environment")
            # PostgreSQL URLの修正
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            self.SQLALCHEMY_DATABASE_URI = database_url
            self.DEBUG = False
            self.DEVELOPMENT = False
            
            # 本番環境での追加の接続設定
            self.SQLALCHEMY_ENGINE_OPTIONS.update({
                'pool_pre_ping': True,  # 接続前の生存確認
                'pool_recycle': 300,    # より短い接続再利用時間
            })
        
        # データベース設定の状態をログ出力
        logger.info(json.dumps({
            'event': 'database_config',
            'is_production': not self.DEVELOPMENT,
            'database_url_set': bool(self.SQLALCHEMY_DATABASE_URI),
            'engine_options': self.SQLALCHEMY_ENGINE_OPTIONS
        }))

# Supabaseクライアントの初期化
try:
    logger.info("Initializing Supabase client...")
    if os.environ.get('NEXT_PUBLIC_SUPABASE_URL') and os.environ.get('NEXT_PUBLIC_SUPABASE_ANON_KEY'):
        from supabase import create_client
        supabase = create_client(
            os.environ.get('NEXT_PUBLIC_SUPABASE_URL'),
            os.environ.get('NEXT_PUBLIC_SUPABASE_ANON_KEY')
        )
    else:
        logger.error("Failed to initialize Supabase client: supabase_url is required")
        supabase = None
except Exception as e:
    logger.error(f"Error initializing Supabase client: {e}")
    supabase = None
