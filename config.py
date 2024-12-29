import os
from dotenv import load_dotenv
import logging
import time
from supabase import create_client, Client
from functools import lru_cache

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Supabaseクライアントの初期化を最適化
@lru_cache(maxsize=1)
def get_supabase_client():
    """
    Supabaseクライアントのシングルトンインスタンスを取得
    lru_cacheを使用して1回だけ初期化されることを保証
    """
    start_time = time.time()
    try:
        logger.info("Initializing Supabase client...")
        client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        end_time = time.time()
        logger.info(f"Supabase client initialized successfully in {end_time - start_time:.2f} seconds")
        return client
    except Exception as e:
        logger.error(f"Error initializing Supabase client: {e}", exc_info=True)
        return None

class DatabaseConnection:
    """データベース接続を管理するクラス"""
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'your-secret-key')

    # Supabase設定
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')

    # データベースURL (Supavisor)
    DATABASE_URL = os.getenv('DATABASE_URL')
    SUPAVISOR_URL = os.getenv('SUPAVISOR_URL')

    # 本番環境（Vercel）かどうかを確認
    IS_PRODUCTION = os.getenv('VERCEL_ENV') == 'production'

    # データベース接続設定
    if IS_PRODUCTION and SUPAVISOR_URL:
        SQLALCHEMY_DATABASE_URI = SUPAVISOR_URL
        logger.info("Using Supavisor connection in production")
    else:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
            SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        logger.info("Using development database connection")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # データベース接続オプション最適化
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 1,  # Vercelの制限に合わせて最小化
        "max_overflow": 0,
        "connect_args": {
            "sslmode": "require" if IS_PRODUCTION else "disable",
            "connect_timeout": 5,  # タイムアウトを5秒に短縮
            "application_name": "quiz_app",
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5
        },
        "pool_pre_ping": True,
        "pool_recycle": 60,     # 1分でコネクションをリサイクル
        "pool_timeout": 5       # プールからの取得を5秒でタイムアウト
    }

    # 接続設定のログ出力
    logger.info(f"Environment: {'Production' if IS_PRODUCTION else 'Development'}")
    logger.info(f"SSL mode: {'enabled' if IS_PRODUCTION else 'disabled'}")
    logger.info(f"Database connection timeout: {SQLALCHEMY_ENGINE_OPTIONS['connect_args']['connect_timeout']} seconds")
    logger.info(f"Pool settings - Size: {SQLALCHEMY_ENGINE_OPTIONS['pool_size']}, "
               f"Timeout: {SQLALCHEMY_ENGINE_OPTIONS['pool_timeout']}, "
               f"Recycle: {SQLALCHEMY_ENGINE_OPTIONS['pool_recycle']}")

# データベース接続のシングルトンインスタンスを作成
db_connection = DatabaseConnection()