import os
import socket
import logging
from dotenv import load_dotenv

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 環境変数の読み込み
load_dotenv()

def resolve_db_host(host, port=5432):
    """Supabaseホストの DNS 解決 - IPv6専用版"""
    try:
        from urllib.parse import urlparse
        parsed_url = urlparse(host)
        hostname = parsed_url.hostname or host
        logger.info(f"Attempting to resolve: {hostname}")

        # IPv6のみを使用するように設定
        addrinfo = socket.getaddrinfo(
            hostname,
            port,
            family=socket.AF_INET6,  # IPv6のみ
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
            flags=socket.AI_ADDRCONFIG  # IPv4マッピングを無効化
        )
        
        if not addrinfo:
            logger.error("No IPv6 addresses found")
            return hostname

        ip = addrinfo[0][4][0]
        logger.info(f"Resolved IPv6: {ip}")
        # IPv6アドレスは常に括弧で囲む
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
        # デバッグ情報の出力
        logger.info("=== Config Initialization Start ===")
        
        # 基本設定
        self.FLASK_ENV = 'production' if os.getenv('VERCEL') else os.getenv('FLASK_ENV', 'development')
        logger.info(f"Current Environment: {self.FLASK_ENV}")
        
        # データベース設定
        if self.FLASK_ENV == 'development':
            db_url = os.getenv('LOCAL_DATABASE_URL')
            logger.info(f"Development Database URL exists: {bool(db_url)}")
        else:
            db_url = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')
            logger.info(f"Production Database URL exists: {bool(db_url)}")
            
            if not db_url:
                # 個別パラメータの確認
                params = {
                    'user': os.getenv('POSTGRES_USER'),
                    'password': bool(os.getenv('POSTGRES_PASSWORD')),  # パスワードの有無のみログ
                    'host': os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
                    'port': os.getenv('POSTGRES_PORT', '5432'),
                    'database': os.getenv('POSTGRES_DATABASE')
                }
                logger.info(f"Database Parameters: {params}")
                
                if all(v for k, v in params.items() if k != 'password'):
                    resolved_host = resolve_db_host(params['host'], int(params['port']))
                    db_url = f"postgresql://{params['user']}:{os.getenv('POSTGRES_PASSWORD')}@{resolved_host}:{params['port']}/{params['database']}"
                    logger.info("Database URL constructed from parameters")
                else:
                    logger.error("Missing required database parameters")
                    
        self.SQLALCHEMY_DATABASE_URI = db_url
        logger.info(f"Final Database URI set: {bool(self.SQLALCHEMY_DATABASE_URI)}")
        
        # エンジンオプション
        self.SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_recycle": 300,
        }
        if self.FLASK_ENV != 'development':
            self.SQLALCHEMY_ENGINE_OPTIONS["connect_args"] = {"sslmode": "require"}
        
        # 共通設定
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        logger.info("=== Config Initialization End ===")
