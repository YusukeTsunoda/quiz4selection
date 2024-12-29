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

class DatabaseConnection:
    """データベース接続を管理するクラス"""
    def __init__(self):
        self._client = None
        self._last_used = None
        self._connection_timeout = 300  # 5分

    @property
    def client(self):
        current_time = time.time()
        
        # コネクションの有効期限チェック
        if self._client is not None and self._last_used is not None:
            if current_time - self._last_used > self._connection_timeout:
                logger.info("Connection expired, recreating...")
                self._client = None
        
        if self._client is None:
            self._client = get_supabase_client()
            self._last_used = current_time
        else:
            self._last_used = current_time
        
        return self._client

class Config:
    # 環境変数の読み込みを先に行う
    IS_PRODUCTION = os.getenv('VERCEL_ENV') == 'production'
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'your-secret-key')
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    DATABASE_URL = os.getenv('DATABASE_URL')
    SUPAVISOR_URL = os.getenv('SUPAVISOR_URL')

    # クエリタイムアウトの設定
    QUERY_TIMEOUT = 5  # 秒
    STATEMENT_TIMEOUT = 5000  # ミリ秒

    # データベース接続設定
    if IS_PRODUCTION:
        if SUPAVISOR_URL:
            SQLALCHEMY_DATABASE_URI = SUPAVISOR_URL
            logger.info("Using Supavisor connection in production")
        else:
            SQLALCHEMY_DATABASE_URI = DATABASE_URL
            if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
                SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
            logger.info("Using direct database connection in production")
    else:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
            SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        logger.info("Using development database connection")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # データベース接続オプション最適化
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 1,
        "max_overflow": 0,
        "connect_args": {
            "sslmode": "require" if IS_PRODUCTION else "disable",
            "connect_timeout": 5,
            "application_name": "quiz_app",
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
            "options": f"-c statement_timeout={STATEMENT_TIMEOUT}"  # クエリタイムアウトの設定
        },
        "pool_pre_ping": True,
        "pool_recycle": 60,
        "pool_timeout": 5,
        "execution_options": {
            "timeout": QUERY_TIMEOUT  # SQLAlchemyのクエリタイムアウト
        }
    }

    # キャッシュ設定
    CACHE_TYPE = "simple"
    CACHE_DEFAULT_TIMEOUT = 300  # 5分
    CACHE_THRESHOLD = 500  # キャッシュするアイテムの最大数

# Supabaseクライアントの初期化（シングルトン）
_supabase_instance = None
_last_connection_time = None
_connection_timeout = 300  # 5分

def get_supabase_client():
    """
    Supabaseクライアントのシングルトンインスタンスを取得
    """
    global _supabase_instance, _last_connection_time
    current_time = time.time()

    # コネクションの有効期限チェック
    if _supabase_instance is not None and _last_connection_time is not None:
        if current_time - _last_connection_time > _connection_timeout:
            logger.info("Supabase connection expired, recreating...")
            _supabase_instance = None

    if _supabase_instance is None:
        start_time = time.time()
        try:
            logger.info("Initializing Supabase client...")
            _supabase_instance = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
            _last_connection_time = current_time
            end_time = time.time()
            logger.info(f"Supabase client initialized successfully in {end_time - start_time:.2f} seconds")
        except Exception as e:
            logger.error(f"Error initializing Supabase client: {e}", exc_info=True)
            return None

    return _supabase_instance

# 設定のログ出力（一度だけ）
logger.info(f"Environment: {'Production' if Config.IS_PRODUCTION else 'Development'}")
logger.info(f"SSL mode: {'enabled' if Config.IS_PRODUCTION else 'disabled'}")
logger.info(f"Database connection timeout: {Config.SQLALCHEMY_ENGINE_OPTIONS['connect_args']['connect_timeout']} seconds")
logger.info(f"Query timeout: {Config.QUERY_TIMEOUT} seconds")
logger.info(f"Statement timeout: {Config.STATEMENT_TIMEOUT} milliseconds")
logger.info(f"Pool settings - Size: {Config.SQLALCHEMY_ENGINE_OPTIONS['pool_size']}, "
           f"Timeout: {Config.SQLALCHEMY_ENGINE_OPTIONS['pool_timeout']}, "
           f"Recycle: {Config.SQLALCHEMY_ENGINE_OPTIONS['pool_recycle']}")

# データベース接続とSupabaseクライアントのインスタンスを作成
db_connection = DatabaseConnection()
supabase = get_supabase_client()

# エクスポートする変数を明示的に定義
__all__ = ['Config', 'db_connection', 'supabase']