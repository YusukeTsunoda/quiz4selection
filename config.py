import os
from dotenv import load_dotenv
import logging
from supabase import create_client, Client

# ロガーの設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'your-secret-key')

    # Supabase設定
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')

    # データベースURL (Supavisor)
    DATABASE_URL = os.getenv('DATABASE_URL')

    # データベース設定
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    
    # 開発環境の場合はローカルデータベースを使用
    if os.environ.get('FLASK_ENV') == 'development':
        SQLALCHEMY_DATABASE_URI = os.environ.get('LOCAL_DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/quiz_db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 1,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'pool_pre_ping': True,
        'connect_args': {
            'connect_timeout': 10,
            'application_name': 'quiz_app',
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
            'sslmode': 'prefer'
        }
    }

    logger.debug("--- 環境変数の設定 ---")
    logger.debug(f"FLASK_SECRET_KEY: {'設定されています' if SECRET_KEY else '設定されていません'}")
    logger.debug(f"SUPABASE_URL: {SUPABASE_URL}")
    logger.debug(f"SUPABASE_KEY: {'設定されています' if SUPABASE_KEY else '設定されていません (注意: 本番環境では安全な管理をしてください)'}")
    logger.debug(f"DATABASE_URL: {DATABASE_URL}")
    logger.debug("--- 環境変数の設定 完了 ---")


# Supabaseクライアントの初期化
try:
    logger.info("Initializing Supabase client...")
    supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Supabase client: {e}", exc_info=True)
    supabase = None