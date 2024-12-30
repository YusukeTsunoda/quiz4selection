import os
from dotenv import load_dotenv
from supabase import create_client
import logging
import sys
import json

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger('config')

# 環境変数の読み込み
load_dotenv()

# 環境変数の状態をログ出力
logger.info(json.dumps({
    'event': 'environment_check',
    'environment': os.environ.get('ENVIRONMENT', 'development'),
    'database_url_set': bool(os.environ.get('DATABASE_URL')),
    'local_database_url_set': bool(os.environ.get('LOCAL_DATABASE_URL')),
    'supabase_url_set': bool(os.environ.get('SUPABASE_URL')),
    'supabase_key_set': bool(os.environ.get('SUPABASE_KEY'))
}))

class Config:
    # 基本設定
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'your-secret-key'
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
    
    # データベース接続設定
    DATABASE_URL = os.environ.get('DATABASE_URL')
    LOCAL_DATABASE_URL = os.environ.get('LOCAL_DATABASE_URL')
    
    # 環境変数の状態をログ出力
    logger.info(json.dumps({
        'event': 'database_config',
        'environment': ENVIRONMENT,
        'database_url': bool(DATABASE_URL),
        'local_database_url': bool(LOCAL_DATABASE_URL)
    }))
    
    # SQLAlchemy設定
    if ENVIRONMENT == 'production':
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
            SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
            logger.info('Converted postgres:// to postgresql:// in DATABASE_URL')
    else:
        SQLALCHEMY_DATABASE_URI = LOCAL_DATABASE_URL
        logger.info('Using LOCAL_DATABASE_URL for development')
    
    # データベースURIの状態をログ出力
    logger.info(json.dumps({
        'event': 'sqlalchemy_config',
        'environment': ENVIRONMENT,
        'database_uri_set': bool(SQLALCHEMY_DATABASE_URI)
    }))
    
    if not SQLALCHEMY_DATABASE_URI:
        error_msg = "Database URI is not set. Check your environment variables."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 1,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'pool_pre_ping': True,
        'connect_args': {
            'connect_timeout': 30,
            'application_name': 'quiz_app'
        }
    }
    
    # Supabase設定
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

    @staticmethod
    def init_app(app):
        pass

# Supabaseクライアントの初期化
def init_supabase():
    try:
        return create_client(
            supabase_url=Config.SUPABASE_URL,
            supabase_key=Config.SUPABASE_KEY
        )
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None

# グローバルインスタンスの作成
supabase = init_supabase()

# データベース接続文字列の取得
def get_db_connection():
    return Config.SQLALCHEMY_DATABASE_URI

db_connection = get_db_connection()