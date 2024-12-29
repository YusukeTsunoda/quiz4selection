import os
from dotenv import load_dotenv
import logging
import socket
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
    
    # データベースURL
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # DNS解決テストとログ出力
    if DATABASE_URL:
        logger.debug(f"Original DATABASE_URL: {DATABASE_URL}")
        
        # postgresからpostgresqlへの変換
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
            logger.debug(f"After protocol conversion: {DATABASE_URL}")
        
        try:
            from urllib.parse import urlparse
            import socket
            
            parsed_url = urlparse(DATABASE_URL)
            host = parsed_url.hostname
            logger.debug(f"Parsed hostname: {host}")
            
            # DNS解決テスト用ソケット作成
            
            try:
                logger.debug("Testing DNS resolution...")
                addr_info = socket.getaddrinfo(host, None)
                logger.debug(f"DNS resolution successful. Address info: {addr_info}")
                
                # IPv4アドレスの取得を試行
                ipv4_addrs = [addr[4][0] for addr in addr_info if addr[0] == socket.AF_INET]
                if ipv4_addrs:
                    logger.debug(f"Found IPv4 addresses: {ipv4_addrs}")
                else:
                    logger.warning("No IPv4 addresses found")
                    
            except socket.gaierror as e:
                logger.error(f"DNS resolution failed: {e}", exc_info=True)
                
        except Exception as e:
            logger.error(f"Error parsing DATABASE_URL: {e}", exc_info=True)
    else:
        logger.error("DATABASE_URL is not set")
    
    # 基本的な接続設定
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 最小限の接続オプション
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 1,  # 最小限のプールサイズ
        "max_overflow": 0,  # オーバーフローなし
        "connect_args": {
            "sslmode": "require",
            "connect_timeout": 30
        }
    }
    
    logger.debug("SQLAlchemy configuration:")
    logger.debug(f"  Database URI: {SQLALCHEMY_DATABASE_URI}")
    logger.debug(f"  Engine options: {SQLALCHEMY_ENGINE_OPTIONS}")

# Supabaseクライアントの初期化
try:
    logger.info("Initializing Supabase client...")
    supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Supabase client: {e}", exc_info=True)
    supabase = None