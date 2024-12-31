import os
import socket
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# 環境変数の読み込み
load_dotenv()

def test_db_connection(db_url):
    """データベース接続テスト"""
    try:
        logger.info("Testing database connection...")
        engine = create_engine(db_url, echo=True)
        
        # 接続情報の出力
        logger.info(f"Driver: {engine.driver}")
        logger.info(f"Dialect: {engine.dialect.name}")
        
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            logger.info(f"Database version: {result.scalar()}")
            return True
    except Exception as e:
        logger.error(f"Connection error: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        return False

def resolve_db_host(host, port=5432):
    """Supabaseホストの DNS 解決 - IPv6専用版"""
    try:
        from urllib.parse import urlparse
        parsed_url = urlparse(host)
        hostname = parsed_url.hostname or host
        logger.info(f"Attempting to resolve: {hostname}")

        addrinfo = socket.getaddrinfo(
            hostname,
            port,
            family=socket.AF_INET6,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
            flags=socket.AI_ADDRCONFIG
        )
        
        if not addrinfo:
            logger.error("No IPv6 addresses found")
            return hostname

        ip = addrinfo[0][4][0]
        logger.info(f"Resolved IPv6: {ip}")
        return f"[{ip}]"

    except socket.gaierror as e:
        logger.error(f"IPv6 DNS resolution error: {e}")
        return hostname
    except Exception as e:
        logger.error(f"Unexpected error in IPv6 resolution: {e}")
        return hostname

class Config:
    """アプリケーション設定クラス"""
    def __init__(self):
        logger.info("=== Config Initialization Start ===")
        
        self.FLASK_ENV = 'production' if os.getenv('VERCEL') else os.getenv('FLASK_ENV', 'development')
        logger.info(f"Current Environment: {self.FLASK_ENV}")
        
        if self.FLASK_ENV == 'development':
            db_url = os.getenv('LOCAL_DATABASE_URL')
            logger.info("Development mode detected")
        else:
            db_url = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')
            if not db_url:
                params = {
                    'user': os.getenv('POSTGRES_USER'),
                    'password': '***' if os.getenv('POSTGRES_PASSWORD') else None,
                    'host': os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
                    'port': os.getenv('POSTGRES_PORT', '5432'),
                    'database': os.getenv('POSTGRES_DATABASE')
                }
                logger.info(f"Database Parameters (masked): {params}")
                
                if all(v for k, v in params.items() if k != 'password'):
                    resolved_host = resolve_db_host(params['host'], int(params['port']))
                    db_url = f"postgresql://{params['user']}:{os.getenv('POSTGRES_PASSWORD')}@{resolved_host}:{params['port']}/{params['database']}"
                    logger.info("Database URL constructed from parameters")
                else:
                    logger.error("Missing required database parameters")
        
        self.SQLALCHEMY_DATABASE_URI = db_url
        if db_url:
            test_db_connection(db_url)
        else:
            logger.error("No database URL available")
        
        self.SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_recycle": 300,
        }
        if self.FLASK_ENV != 'development':
            self.SQLALCHEMY_ENGINE_OPTIONS["connect_args"] = {
                "sslmode": "require",
                "application_name": "quiz_app"
            }
        
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        logger.info("=== Config Initialization End ===")
