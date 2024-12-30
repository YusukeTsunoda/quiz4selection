import os
from dotenv import load_dotenv
from supabase import create_client
import logging
<<<<<<< HEAD
from supabase import create_client, Client
=======
import sys
>>>>>>> 681de6ad92a5180cf7f6948754ec9bd5293c7a94
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
    'vercel_env': os.environ.get('VERCEL_ENV', 'development'),
    'database_url_set': bool(os.environ.get('DATABASE_URL')),
    'local_database_url_set': bool(os.environ.get('LOCAL_DATABASE_URL')),
    'supabase_url_set': bool(os.environ.get('SUPABASE_URL')),
    'supabase_key_set': bool(os.environ.get('SUPABASE_KEY')),
    'sqlalchemy_database_uri_set': bool(os.environ.get('SQLALCHEMY_DATABASE_URI'))
}))

class Config:
<<<<<<< HEAD
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'your-secret-key')
    
    # 環境の確認
    VERCEL_ENV = os.getenv('VERCEL_ENV')
    FLASK_ENV = os.getenv('FLASK_ENV')
    IS_DEVELOPMENT = FLASK_ENV == 'development' or VERCEL_ENV == 'development'
    
    # 環境変数の状態をログ出力
    logger.info(json.dumps({
        "event": "environment_check",
        "vercel_env": VERCEL_ENV,
        "database_url_set": bool(os.getenv('DATABASE_URL')),
        "local_database_url_set": bool(os.getenv('LOCAL_DATABASE_URL')),
        "supabase_url_set": bool(os.getenv('SUPABASE_URL')),
        "supabase_key_set": bool(os.getenv('SUPABASE_KEY')),
        "sqlalchemy_database_uri_set": bool(os.getenv('SQLALCHEMY_DATABASE_URI'))
    }))

    # Supabase設定
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')

    # データベース接続設定
    if IS_DEVELOPMENT:
        # 開発環境ではローカルデータベースを使用
        SQLALCHEMY_DATABASE_URI = os.getenv('LOCAL_DATABASE_URL')
        logger.info("Using LOCAL_DATABASE_URL for development")
    else:
        # 本番環境ではDATABASE_URLを使用
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
        if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    
    # 環境設定のログ出力
    logger.info(json.dumps({
        "event": "database_config",
        "is_production": not IS_DEVELOPMENT,
        "database_url": bool(os.getenv('DATABASE_URL')),
        "local_database_url": bool(os.getenv('LOCAL_DATABASE_URL')),
        "sqlalchemy_database_uri": bool(SQLALCHEMY_DATABASE_URI)
    }))

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQLAlchemy設定のログ出力
    logger.info(json.dumps({
        "event": "sqlalchemy_config",
        "is_production": not IS_DEVELOPMENT,
        "database_uri_set": bool(SQLALCHEMY_DATABASE_URI)
    }))

    # データベース接続オプション
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 1,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
        "connect_args": {
            "connect_timeout": 30,
            "application_name": "quiz_app",
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
            "sslmode": "prefer"
=======
    # 基本設定
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'your-secret-key'
    IS_PRODUCTION = os.environ.get('VERCEL_ENV') == 'production'
    
    # データベース接続設定
    DATABASE_URL = os.environ.get('DATABASE_URL')
    LOCAL_DATABASE_URL = os.environ.get('LOCAL_DATABASE_URL')
    
    # SQLAlchemy設定
    if IS_PRODUCTION:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
            SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
            logger.info('Converted postgres:// to postgresql:// in DATABASE_URL')
    else:
        SQLALCHEMY_DATABASE_URI = LOCAL_DATABASE_URL
        logger.info('Using LOCAL_DATABASE_URL for development')
    
    # 環境変数の状態をログ出力
    logger.info(json.dumps({
        'event': 'database_config',
        'is_production': IS_PRODUCTION,
        'database_url': bool(DATABASE_URL),
        'local_database_url': bool(LOCAL_DATABASE_URL),
        'sqlalchemy_database_uri': bool(SQLALCHEMY_DATABASE_URI)
    }))
    
    # データベースURIの状態をログ出力
    logger.info(json.dumps({
        'event': 'sqlalchemy_config',
        'is_production': IS_PRODUCTION,
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
            'application_name': 'quiz_app',
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
            'sslmode': 'prefer'
>>>>>>> 681de6ad92a5180cf7f6948754ec9bd5293c7a94
        }
    }
    
    # Supabase設定
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

    @staticmethod
    def init_app(app):
        pass

<<<<<<< HEAD
# Supabaseクライアントの初期化（オプショナル）
try:
    logger.info("Initializing Supabase client...")
    if Config.SUPABASE_URL and Config.SUPABASE_KEY:
        supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
    else:
        logger.error("Failed to initialize Supabase client: supabase_url is required")
        supabase = None
except Exception as e:
    logger.error(f"Error initializing Supabase client: {e}")
    supabase = None
=======
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
>>>>>>> 681de6ad92a5180cf7f6948754ec9bd5293c7a94
