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
    SUPAVISOR_URL = os.getenv('SUPAVISOR_URL')  # Supavisorの接続URL

    logger.debug("--- 環境変数の設定 ---")
    logger.debug(f"FLASK_SECRET_KEY: {'設定されています' if SECRET_KEY else '設定されていません'}")
    logger.debug(f"SUPABASE_URL: {SUPABASE_URL}")
    logger.debug(f"SUPABASE_KEY: {'設定されています' if SUPABASE_KEY else '設定されていません (注意: 本番環境では安全な管理をしてください)'}")
    logger.debug(f"DATABASE_URL: {DATABASE_URL}")
    logger.debug(f"SUPAVISOR_URL: {'設定されています' if SUPAVISOR_URL else '設定されていません'}")
    logger.debug("--- 環境変数の設定 完了 ---")

    # 本番環境（Vercel）かどうかを確認
    IS_PRODUCTION = os.getenv('VERCEL_ENV') == 'production'
    
    if IS_PRODUCTION and SUPAVISOR_URL:
        # 本番環境でSupavisorが設定されている場合はそちらを使用
        SQLALCHEMY_DATABASE_URI = SUPAVISOR_URL
        logger.info("Using Supavisor connection in production")
    else:
        # 開発環境または本番環境でもSupavisorが未設定の場合は通常のURLを使用
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
            SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        logger.info(f"Using {'development' if not IS_PRODUCTION else 'production'} database connection")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # データベース接続オプション
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 1,
        "max_overflow": 0,
        "connect_args": {
            "sslmode": "require" if IS_PRODUCTION else "disable",  # 本番環境ではSSLを必須に
            "connect_timeout": 30,
            "application_name": "quiz_app"
        }
    }

    logger.debug("SQLAlchemy configuration:")
    # 機密情報をマスクしてログ出力
    masked_uri = SQLALCHEMY_DATABASE_URI.split('@')[1] if '@' in SQLALCHEMY_DATABASE_URI else SQLALCHEMY_DATABASE_URI
    logger.debug(f"  Database URI (masked): ...@{masked_uri}")
    logger.debug(f"  Engine options: {SQLALCHEMY_ENGINE_OPTIONS}")

# Supabaseクライアントの初期化
try:
    logger.info("Initializing Supabase client...")
    supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Supabase client: {e}", exc_info=True)
    supabase = None