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
        self._retry_count = 0
        self._max_retries = 3

    @property
    def client(self):
        current_time = time.time()
        
        # コネクションの有効期限チェック
        if self._client is not None and self._last_used is not None:
            if current_time - self._last_used > self._connection_timeout:
                logger.info("Connection expired, recreating...")
                self._client = None
        
        if self._client is None:
            while self._retry_count < self._max_retries:
                try:
                    logger.info(f"Attempting to create Supabase client (attempt {self._retry_count + 1}/{self._max_retries})")
                    self._client = get_supabase_client()
                    if self._client:
                        self._last_used = current_time
                        self._retry_count = 0
                        break
                    else:
                        self._retry_count += 1
                        if self._retry_count < self._max_retries:
                            logger.warning(f"Failed to create client, retrying in 2 seconds...")
                            time.sleep(2)
                except Exception as e:
                    logger.error(f"Error creating Supabase client: {e}")
                    self._retry_count += 1
                    if self._retry_count < self._max_retries:
                        logger.warning(f"Failed to create client, retrying in 2 seconds...")
                        time.sleep(2)
            
            if self._client is None:
                logger.error("Failed to create Supabase client after all retries")
                raise Exception("Could not establish database connection")
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
    LOCAL_DATABASE_URL = os.getenv('LOCAL_DATABASE_URL', 'postgresql://localhost/quiz_app')

    # クエリタイムアウトの設定
    QUERY_TIMEOUT = 30  # 秒
    STATEMENT_TIMEOUT = 30000  # ミリ秒

    # データベース接続設定
    if IS_PRODUCTION:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
            SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        logger.info("Using Supabase direct connection in production")
        # 接続文字列のデバッグ（パスワードは隠す）
        debug_uri = SQLALCHEMY_DATABASE_URI
        if debug_uri:
            parts = debug_uri.split('@')
            if len(parts) > 1:
                masked_uri = f"{parts[0].split(':')[0]}:****@{parts[1]}"
                logger.info(f"Database URI format: {masked_uri}")
    else:
        SQLALCHEMY_DATABASE_URI = LOCAL_DATABASE_URL
        logger.info("Using local database connection")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # データベース接続オプション最適化
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 1 if IS_PRODUCTION else 5,
        "max_overflow": 0,
        "connect_args": {
            "sslmode": "require" if IS_PRODUCTION else "disable",
            "connect_timeout": 30,
            "application_name": "quiz_app_vercel",
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
            "options": f"-c statement_timeout={STATEMENT_TIMEOUT}",
            "client_encoding": 'utf8',
            "target_session_attrs": "read-write",
            "tcp_user_timeout": 30000, # ここを追加
        },
        "pool_pre_ping": True,
        "pool_recycle": 60,
        "pool_timeout": 30,
        "execution_options": {
            "timeout": 30
        }
    }

    # 本番環境での追加設定
    if IS_PRODUCTION:
        SQLALCHEMY_ENGINE_OPTIONS.update({
            "isolation_level": "READ COMMITTED",
            "echo": True,
            "echo_pool": True,
            "pool_reset_on_return": "rollback"
        })

    # SSL設定のログ出力
    if IS_PRODUCTION:
        logger.info(f"SSL Mode: {SQLALCHEMY_ENGINE_OPTIONS['connect_args']['sslmode']}")
        logger.info(f"TCP User Timeout: {SQLALCHEMY_ENGINE_OPTIONS['connect_args']['tcp_user_timeout']} milliseconds")
        logger.info(f"Client Encoding: {SQLALCHEMY_ENGINE_OPTIONS['connect_args']['client_encoding']}")
        logger.info(f"Target Session Attrs: {SQLALCHEMY_ENGINE_OPTIONS['connect_args']['target_session_attrs']}")

    # キャッシュ設定
    CACHE_TYPE = "simple"
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_THRESHOLD = 500

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
        retry_count = 0
        max_retries = 3
        retry_delay = 2  # 秒

        while retry_count < max_retries:
            try:
                logger.info(f"Initializing Supabase client (attempt {retry_count + 1}/{max_retries})...")
                
                # 新しい形式でのクライアント初期化
                _supabase_instance = create_client(
                    Config.SUPABASE_URL,
                    Config.SUPABASE_KEY,
                    {
                        'db': {
                            'schema': 'public'
                        },
                        'auth': {
                            'autoRefreshToken': True,
                            'persistSession': True
                        }
                    }
                )
                
                # 軽量な接続テスト
                try:
                    # データベース接続テスト
                    data = _supabase_instance.table('quiz_attempts').select("count").limit(1).execute()
                    logger.info("Database connection test successful")
                except Exception as e:
                    logger.warning(f"Database test failed: {e}")
                    # エラーを再度発生させて、リトライロジックを働かせる
                    raise
                
                _last_connection_time = current_time
                end_time = time.time()
                logger.info(f"Supabase client initialized successfully in {end_time - start_time:.2f} seconds")
                break
            except Exception as e:
                retry_count += 1
                logger.error(f"Error initializing Supabase client (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to initialize Supabase client after all retries")
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