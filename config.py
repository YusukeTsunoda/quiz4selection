import os
from dotenv import load_dotenv
from supabase import create_client, Client
import re
import logging

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
    if DATABASE_URL:
        # 接続URLの解析と変換前の状態をログ
        logger.debug(f"Original DATABASE_URL: {DATABASE_URL}")
        
        # postgresからpostgresqlへの変換
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
            logger.debug(f"After protocol conversion: {DATABASE_URL}")
        
        # URLの各コンポーネントを解析してログ
        try:
            from urllib.parse import urlparse, urlunparse
            parsed_url = urlparse(DATABASE_URL)
            
            # ホスト名からIPv4アドレスを取得
            import socket
            try:
                host = parsed_url.hostname
                logger.debug(f"Resolving hostname: {host}")
                # IPv4アドレスのみを取得するように設定
                addr_info = socket.getaddrinfo(
                    host,
                    None,
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    0,
                    socket.AI_ADDRCONFIG
                )
                ipv4_addr = addr_info[0][4][0]
                logger.debug(f"Resolved IPv4 address: {ipv4_addr}")
                
                # URLを再構築（IPv4アドレスを使用）
                new_netloc = f"{parsed_url.username}:{parsed_url.password}@{ipv4_addr}:{parsed_url.port}"
                DATABASE_URL = urlunparse((
                    parsed_url.scheme,
                    new_netloc,
                    parsed_url.path,
                    parsed_url.params,
                    parsed_url.query,
                    parsed_url.fragment
                ))
                logger.debug(f"Updated DATABASE_URL with IPv4: {DATABASE_URL}")
            except Exception as e:
                logger.error(f"Error resolving IPv4 address: {e}", exc_info=True)
            
            logger.debug("Parsed URL components:")
            logger.debug(f"  scheme: {parsed_url.scheme}")
            logger.debug(f"  username: {'present' if parsed_url.username else 'missing'}")
            logger.debug(f"  password: {'present' if parsed_url.password else 'missing'}")
            logger.debug(f"  hostname: {parsed_url.hostname}")
            logger.debug(f"  port: {parsed_url.port}")
            logger.debug(f"  database: {parsed_url.path}")
        except Exception as e:
            logger.error(f"Error parsing DATABASE_URL: {e}", exc_info=True)
    else:
        logger.error("DATABASE_URL is not set")
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # データベース接続オプション
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 5,
        "max_overflow": 2,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
        "connect_args": {
            "sslmode": "require",
            "connect_timeout": 30,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
            "tcp_user_timeout": 30000,
            "options": "-c search_path=public -c statement_timeout=30000",
            "application_name": "quiz_app"
        }
    }
    
    logger.debug("SQLAlchemy engine options:")
    logger.debug(f"  Pool size: {SQLALCHEMY_ENGINE_OPTIONS['pool_size']}")
    logger.debug(f"  Max overflow: {SQLALCHEMY_ENGINE_OPTIONS['max_overflow']}")
    logger.debug(f"  Pool timeout: {SQLALCHEMY_ENGINE_OPTIONS['pool_timeout']}")
    logger.debug(f"  Pool recycle: {SQLALCHEMY_ENGINE_OPTIONS['pool_recycle']}")
    logger.debug(f"  Connect args: {SQLALCHEMY_ENGINE_OPTIONS['connect_args']}")

# Supabaseクライアントの初期化
try:
    logger.info("Initializing Supabase client...")
    supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Supabase client: {e}", exc_info=True)
    supabase = None