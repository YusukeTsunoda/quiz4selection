import os
import logging
import json
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Config:
    """アプリケーションの設定クラス"""
    # セッション設定
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    
    # 環境設定
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    VERCEL_ENV = os.environ.get('VERCEL_ENV')
    
    # データベース設定
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('LOCAL_DATABASE_URL')  # 開発環境用のデフォルト値

    # 環境に応じたデータベース接続オプション
    if FLASK_ENV == 'development' or VERCEL_ENV == 'development':
        SQLALCHEMY_ENGINE_OPTIONS = {}  # 開発環境ではSSLを無効化
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {  # 本番環境ではSSLを要求
            'connect_args': {
                'sslmode': 'require',
                'connect_timeout': 30
            }
        }

    
    def __init__(self):
        # 環境変数の状態をログ出力
        logger.info(json.dumps({
            'event': 'environment_check',
            'vercel_env': os.environ.get('VERCEL_ENV'),
            'database_url_set': bool(os.environ.get('DATABASE_URL')),
            'local_database_url_set': bool(os.environ.get('LOCAL_DATABASE_URL')),
            'supabase_url_set': bool(os.environ.get('SUPABASE_URL')),
            'supabase_key_set': bool(os.environ.get('SUPABASE_KEY')),
            'sqlalchemy_database_uri_set': bool(hasattr(self, 'SQLALCHEMY_DATABASE_URI'))
        }))
        
        # 開発環境の設定
        if self.FLASK_ENV == 'development' or self.VERCEL_ENV == 'development':
            logger.info("Using LOCAL_DATABASE_URL for development")
            self.SQLALCHEMY_DATABASE_URI = os.environ.get('LOCAL_DATABASE_URL')
            self.DEBUG = True
            self.DEVELOPMENT = True
        # 本番環境の設定
        else:
            logger.info("Using DATABASE_URL for production")
            self.SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
            if self.SQLALCHEMY_DATABASE_URI and self.SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
                self.SQLALCHEMY_DATABASE_URI = self.SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
            self.DEBUG = False
            self.DEVELOPMENT = False
        
        # データベース設定の状態をログ出力
        logger.info(json.dumps({
            'event': 'database_config',
            'is_production': not self.DEVELOPMENT,
            'database_url': bool(os.environ.get('DATABASE_URL')),
            'local_database_url': bool(os.environ.get('LOCAL_DATABASE_URL')),
            'sqlalchemy_database_uri': bool(self.SQLALCHEMY_DATABASE_URI)
        }))
        
        # SQLAlchemy設定の状態をログ出力
        logger.info(json.dumps({
            'event': 'sqlalchemy_config',
            'is_production': not self.DEVELOPMENT,
            'database_uri_set': bool(self.SQLALCHEMY_DATABASE_URI)
        }))

# Supabaseクライアントの初期化
try:
    logger.info("Initializing Supabase client...")
    if os.environ.get('SUPABASE_URL') and os.environ.get('SUPABASE_KEY'):
        from supabase import create_client
        supabase = create_client(
            os.environ.get('SUPABASE_URL'),
            os.environ.get('SUPABASE_KEY')
        )
    else:
        logger.error("Failed to initialize Supabase client: supabase_url is required")
        supabase = None
except Exception as e:
    logger.error(f"Error initializing Supabase client: {e}")
    supabase = None
