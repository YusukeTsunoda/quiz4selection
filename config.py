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