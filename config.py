import os
from dotenv import load_dotenv
import logging
import time
from supabase import create_client, Client

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Supabaseクライアントをグローバル変数として保持
_supabase_client = None

def get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        start_time = time.time()
        try:
            logger.info("Initializing Supabase client...")
            _supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
            end_time = time.time()
            logger.info(f"Supabase client initialized successfully in {end_time - start_time:.2f} seconds")
        except Exception as e:
            logger.error(f"Error initializing Supabase client: {e}", exc_info=True)
            return None
    return _supabase_client

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
        # 本番環境でSupavisorが設定されている場合はそちらを使用
        SQLALCHEMY_DATABASE_URI = SUPAVISOR_URL
        logger.info("Using Supavisor connection in production")
    else:
        # 開発環境または本番環境でもSupavisorが未設定の場合は通常のURLを使用
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
            SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        logger.info("Using development database connection")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # データベース接続オプション
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 5,
        "max_overflow": 0,
        "connect_args": {
            "sslmode": "require" if IS_PRODUCTION else "disable",
            "connect_timeout": 30,  # タイムアウトを10秒に設定
            "application_name": "quiz_app"
        },
        # コネクションプールの設定を追加
        "pool_pre_ping": True,  # コネクションの有効性をチェック
        "pool_recycle": 300,    # 5分でコネクションをリサイクル
        "pool_timeout": 10      # プールからの取得を10秒でタイムアウト
    }

    logger.info(f"SSL mode: {'enabled' if IS_PRODUCTION else 'disabled'}")
    logger.info(f"Database connection timeout: {SQLALCHEMY_ENGINE_OPTIONS['connect_args']['connect_timeout']} seconds")
    logger.info(f"Pool settings - Size: {SQLALCHEMY_ENGINE_OPTIONS['pool_size']}, "
               f"Timeout: {SQLALCHEMY_ENGINE_OPTIONS['pool_timeout']}, "
               f"Recycle: {SQLALCHEMY_ENGINE_OPTIONS['pool_recycle']}")

# Supabaseクライアントの初期化（シングルトンパターン）
supabase = get_supabase_client()